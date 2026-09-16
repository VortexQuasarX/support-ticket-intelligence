"""Comprehensive anomaly detection combining operational SLA rules and statistical modeling."""

from datetime import datetime
from typing import Any, Dict, List, Optional
import numpy as np
import pandas as pd

from app.config import (
    SLA_CRITICAL_HOURS,
    SLA_HIGH_HOURS,
    SLA_MEDIUM_HOURS,
    MAX_RESPONSE_TIME_THRESHOLD,
    IQR_MULTIPLIER,
    ZSCORE_THRESHOLD
)
from app.database.db_manager import db_manager, DatabaseManager


class AnomalyDetector:
    """Multi-tier engine for operational breaches and statistical anomalies."""

    def __init__(self, db: Optional[DatabaseManager] = None):
        self.db = db or db_manager

    def detect_all(self, min_severity: Optional[str] = None) -> List[Dict[str, Any]]:
        """Detect both rule-based and statistical anomalies, deduplicated and ranked."""
        # Fetch all tickets
        rows = self.db.execute_query("""
            SELECT 
                ticket_id, created_at, category, priority, status,
                response_time_hrs, resolution_time_hrs, agent_id,
                customer_rating, issue_summary
            FROM support_tickets
            ORDER BY created_at DESC;
        """)
        if not rows:
            return []

        df = pd.DataFrame(rows)
        df["created_at_dt"] = pd.to_datetime(df["created_at"])
        
        # Reference timestamp: maximum created_at in dataset (for deterministic evaluation of historic data)
        anchor_time = df["created_at_dt"].max()

        anomalies_by_ticket: Dict[str, Dict[str, Any]] = {}

        # -------------------------------------------------------------
        # 1. Operational SLA Rules
        # -------------------------------------------------------------
        for _, row in df.iterrows():
            t_id = row["ticket_id"]
            status = row["status"]
            priority = row["priority"]
            resp_time = row["response_time_hrs"]
            resol_time = row["resolution_time_hrs"]
            cat = row["category"]
            created = row["created_at_dt"]
            hours_open = (anchor_time - created).total_seconds() / 3600.0

            # Rule A: Unresolved Critical ticket > SLA_CRITICAL_HOURS (12 hrs)
            if status in ("Open", "Escalated") and priority == "Critical" and hours_open > SLA_CRITICAL_HOURS:
                self._record_anomaly(
                    anomalies_by_ticket,
                    ticket=row,
                    anomaly_type="SLA_BREACH_CRITICAL",
                    severity="CRITICAL",
                    score=95.0,
                    metric_name="unresolved_hours",
                    metric_value=round(hours_open, 1),
                    threshold=SLA_CRITICAL_HOURS,
                    description=f"Critical ticket unresolved after {hours_open:.1f} hours (SLA limit: {SLA_CRITICAL_HOURS}h).",
                    recommendation="Immediate executive escalation to on-call support team."
                )

            # Rule B: Unresolved High ticket > SLA_HIGH_HOURS (24 hrs)
            if status in ("Open", "Escalated") and priority == "High" and hours_open > SLA_HIGH_HOURS:
                self._record_anomaly(
                    anomalies_by_ticket,
                    ticket=row,
                    anomaly_type="SLA_BREACH_HIGH",
                    severity="CRITICAL",
                    score=85.0,
                    metric_name="unresolved_hours",
                    metric_value=round(hours_open, 1),
                    threshold=SLA_HIGH_HOURS,
                    description=f"High priority ticket unresolved after {hours_open:.1f} hours (SLA limit: {SLA_HIGH_HOURS}h).",
                    recommendation="Reassign or escalate to senior engineer."
                )

            # Rule C: Escalated ticket pending > 24 hours
            if status == "Escalated" and hours_open > 24.0:
                self._record_anomaly(
                    anomalies_by_ticket,
                    ticket=row,
                    anomaly_type="STALLED_ESCALATION",
                    severity="HIGH" if priority in ("Critical", "High") else "WARNING",
                    score=80.0,
                    metric_name="hours_since_creation",
                    metric_value=round(hours_open, 1),
                    threshold=24.0,
                    description=f"Ticket has been in Escalated state for {hours_open:.1f} hours.",
                    recommendation="Review escalation blocker with tier-2 lead."
                )

            # Rule D: Extreme response time on high/critical tickets
            if priority in ("Critical", "High") and resp_time > MAX_RESPONSE_TIME_THRESHOLD:
                self._record_anomaly(
                    anomalies_by_ticket,
                    ticket=row,
                    anomaly_type="FIRST_RESPONSE_DELAY",
                    severity="WARNING",
                    score=70.0,
                    metric_name="response_time_hrs",
                    metric_value=round(resp_time, 2),
                    threshold=MAX_RESPONSE_TIME_THRESHOLD,
                    description=f"First response delay of {resp_time:.1f} hrs exceeds threshold of {MAX_RESPONSE_TIME_THRESHOLD}h.",
                    recommendation="Review intake triage queue."
                )

        # -------------------------------------------------------------
        # 2. Statistical Outlier Detection (Tukey IQR & Z-score)
        # -------------------------------------------------------------
        resolved_df = df[df["status"] == "Resolved"].copy()
        if not resolved_df.empty:
            # Detect resolution time outliers overall and per category
            q1 = resolved_df["resolution_time_hrs"].quantile(0.25)
            q3 = resolved_df["resolution_time_hrs"].quantile(0.75)
            iqr = q3 - q1
            iqr_cutoff = q3 + (IQR_MULTIPLIER * iqr)

            mean_resol = resolved_df["resolution_time_hrs"].mean()
            std_resol = resolved_df["resolution_time_hrs"].std()

            for _, row in resolved_df.iterrows():
                resol_time = float(row["resolution_time_hrs"])
                z_score = (resol_time - mean_resol) / (std_resol if std_resol > 0 else 1.0)

                if resol_time > iqr_cutoff or z_score > ZSCORE_THRESHOLD:
                    sev = "CRITICAL" if resol_time > (q3 + 3.0 * iqr) else "WARNING"
                    score = min(99.0, 60.0 + (z_score * 10.0))
                    self._record_anomaly(
                        anomalies_by_ticket,
                        ticket=row,
                        anomaly_type="RESOLUTION_TIME_OUTLIER",
                        severity=sev,
                        score=round(score, 1),
                        metric_name="resolution_time_hrs",
                        metric_value=round(resol_time, 1),
                        threshold=round(iqr_cutoff, 1),
                        description=f"Abnormally long resolution time of {resol_time:.1f}h (IQR threshold: {iqr_cutoff:.1f}h, Z-score: {z_score:.2f}).",
                        recommendation="Audit ticket conversation log for process bottleneck or missing tooling."
                    )

            # CSAT Anomaly: Extremely low rating despite quick resolution
            for _, row in resolved_df.iterrows():
                rating = row["customer_rating"]
                resol_time = row["resolution_time_hrs"]
                if rating is not None and rating <= 2 and resol_time < 6.0:
                    self._record_anomaly(
                        anomalies_by_ticket,
                        ticket=row,
                        anomaly_type="LOW_CSAT_SURPRISE",
                        severity="WARNING",
                        score=65.0,
                        metric_name="customer_rating",
                        metric_value=int(rating),
                        threshold=3,
                        description=f"Customer rated {rating}/5 despite fast turnaround of {resol_time:.1f}h.",
                        recommendation="Reach out for feedback; review agent communication quality."
                    )

        # Convert to list and sort by score descending
        results = list(anomalies_by_ticket.values())
        results.sort(key=lambda x: x["score"], reverse=True)

        if min_severity:
            sev_levels = {"CRITICAL": 3, "HIGH": 2, "WARNING": 1, "INFO": 0}
            target_level = sev_levels.get(min_severity.upper(), 0)
            results = [a for a in results if sev_levels.get(a["severity"], 0) >= target_level]

        return results

    def _record_anomaly(
        self,
        registry: Dict[str, Dict[str, Any]],
        ticket: Any,
        anomaly_type: str,
        severity: str,
        score: float,
        metric_name: str,
        metric_value: Any,
        threshold: Any,
        description: str,
        recommendation: str
    ):
        t_id = ticket["ticket_id"]
        # If ticket already has an anomaly, retain the highest severity/score or aggregate
        if t_id in registry:
            if score > registry[t_id]["score"]:
                registry[t_id].update({
                    "anomaly_type": anomaly_type,
                    "severity": severity,
                    "score": score,
                    "metric_name": metric_name,
                    "metric_value": metric_value,
                    "threshold": threshold,
                    "description": description,
                    "recommendation": recommendation
                })
        else:
            registry[t_id] = {
                "ticket_id": t_id,
                "created_at": str(ticket["created_at"]),
                "category": ticket["category"],
                "priority": ticket["priority"],
                "status": ticket["status"],
                "agent_id": ticket["agent_id"],
                "issue_summary": ticket["issue_summary"],
                "anomaly_type": anomaly_type,
                "severity": severity,
                "score": score,
                "metric_name": metric_name,
                "metric_value": metric_value,
                "threshold": threshold,
                "description": description,
                "recommendation": recommendation
            }


anomaly_detector = AnomalyDetector()
