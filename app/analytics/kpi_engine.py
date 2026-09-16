"""High-level KPI and metrics computation engine."""

from typing import Any, Dict, Optional
from app.database.db_manager import db_manager, DatabaseManager


class KPIEngine:
    def __init__(self, db: Optional[DatabaseManager] = None):
        self.db = db or db_manager

    def get_executive_summary(self) -> Dict[str, Any]:
        """Compute comprehensive operational metrics."""
        stats_sql = """
        SELECT 
            COUNT(*) AS total_tickets,
            SUM(CASE WHEN status = 'Open' THEN 1 ELSE 0 END) AS open_tickets,
            SUM(CASE WHEN status = 'Escalated' THEN 1 ELSE 0 END) AS escalated_tickets,
            SUM(CASE WHEN status = 'Resolved' THEN 1 ELSE 0 END) AS resolved_tickets,
            ROUND(AVG(response_time_hrs), 2) AS avg_response_time_hrs,
            ROUND(AVG(CASE WHEN status = 'Resolved' THEN resolution_time_hrs END), 2) AS avg_resolution_time_hrs,
            ROUND(AVG(customer_rating), 2) AS avg_customer_rating
        FROM support_tickets;
        """
        summary_rows = self.db.execute_query(stats_sql)
        summary = summary_rows[0] if summary_rows else {}

        total = summary.get("total_tickets", 0) or 0
        resolved = summary.get("resolved_tickets", 0) or 0
        resolution_rate = round((resolved / total * 100.0), 1) if total > 0 else 0.0

        # Category breakdown
        cat_rows = self.db.execute_query("""
            SELECT category, COUNT(*) as count, 
                   ROUND(AVG(CASE WHEN status = 'Resolved' THEN resolution_time_hrs END), 2) as avg_resolution_hrs,
                   ROUND(AVG(customer_rating), 2) as avg_csat
            FROM support_tickets
            GROUP BY category
            ORDER BY count DESC;
        """)

        # Priority breakdown
        priority_rows = self.db.execute_query("""
            SELECT priority, COUNT(*) as count
            FROM support_tickets
            GROUP BY priority
            ORDER BY 
                CASE priority
                    WHEN 'Critical' THEN 1
                    WHEN 'High' THEN 2
                    WHEN 'Medium' THEN 3
                    WHEN 'Low' THEN 4
                    ELSE 5
                END;
        """)

        # Agent performance leaderboard
        agent_rows = self.db.execute_query("""
            SELECT agent_id, total_assigned, tickets_resolved, 
                   avg_resolution_time_hrs, avg_response_time_hrs, avg_customer_rating
            FROM v_agent_performance
            ORDER BY avg_customer_rating DESC;
        """)

        return {
            "total_tickets": total,
            "open_tickets": summary.get("open_tickets", 0) or 0,
            "escalated_tickets": summary.get("escalated_tickets", 0) or 0,
            "resolved_tickets": resolved,
            "resolution_rate_pct": resolution_rate,
            "avg_response_time_hrs": summary.get("avg_response_time_hrs", 0.0) or 0.0,
            "avg_resolution_time_hrs": summary.get("avg_resolution_time_hrs", 0.0) or 0.0,
            "avg_customer_rating": summary.get("avg_customer_rating", 0.0) or 0.0,
            "categories": cat_rows,
            "priorities": priority_rows,
            "agents": agent_rows
        }


kpi_engine = KPIEngine()
