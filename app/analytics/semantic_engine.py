"""Semantic Search, Issue Topic Clustering, and AI Anomaly Root-Cause Diagnostician."""

import logging
from typing import Any, Dict, List, Optional
import numpy as np
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.cluster import MiniBatchKMeans

from app.database.db_manager import db_manager, DatabaseManager
from app.nlp.llm_client import llm_client

logger = logging.getLogger(__name__)


class SemanticEngine:
    """Enterprise semantic text analysis over support ticket issue summaries."""

    def __init__(self, db: Optional[DatabaseManager] = None):
        self.db = db or db_manager
        self.vectorizer: Optional[TfidfVectorizer] = None
        self.tfidf_matrix = None
        self.tickets_df: Optional[pd.DataFrame] = None
        self._is_indexed = False

    def ensure_index(self):
        """Build TF-IDF inverted index over all issue summaries in SQLite."""
        if self._is_indexed and self.tickets_df is not None:
            return

        rows = self.db.execute_query("""
            SELECT ticket_id, created_at, category, priority, status,
                   response_time_hrs, resolution_time_hrs, agent_id,
                   customer_rating, issue_summary
            FROM support_tickets
            ORDER BY created_at DESC;
        """)
        if not rows:
            return

        self.tickets_df = pd.DataFrame(rows)
        self.vectorizer = TfidfVectorizer(
            stop_words="english",
            ngram_range=(1, 2),
            max_features=1000
        )
        self.tfidf_matrix = self.vectorizer.fit_transform(self.tickets_df["issue_summary"].fillna(""))
        self._is_indexed = True
        logger.info(f"Indexed {len(self.tickets_df)} ticket summaries for semantic search.")

    def search_similar(
        self,
        query: str,
        top_k: int = 10,
        category: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Find tickets semantically related to a text description or symptom."""
        self.ensure_index()
        if not self._is_indexed or self.vectorizer is None or self.tickets_df is None:
            return []

        query_vec = self.vectorizer.transform([query])
        similarities = cosine_similarity(query_vec, self.tfidf_matrix).flatten()

        results = []
        # Get indices sorted by similarity score descending
        top_indices = np.argsort(similarities)[::-1]

        for idx in top_indices:
            score = float(similarities[idx])
            if score < 0.05 and len(results) >= 3:
                break
            row = self.tickets_df.iloc[idx].to_dict()
            if category and row["category"].lower() != category.lower():
                continue

            results.append({
                "ticket_id": row["ticket_id"],
                "similarity_score": round(score, 3),
                "category": row["category"],
                "priority": row["priority"],
                "status": row["status"],
                "agent_id": row["agent_id"],
                "resolution_time_hrs": row["resolution_time_hrs"],
                "customer_rating": row["customer_rating"],
                "issue_summary": row["issue_summary"]
            })
            if len(results) >= top_k:
                break

        return results

    def discover_topics(self, n_clusters: int = 4) -> List[Dict[str, Any]]:
        """Cluster tickets into emergent problem clusters with keyword summaries."""
        self.ensure_index()
        if not self._is_indexed or self.vectorizer is None or self.tickets_df is None:
            return []

        kmeans = MiniBatchKMeans(n_clusters=n_clusters, random_state=42, batch_size=100, n_init="auto")
        labels = kmeans.fit_predict(self.tfidf_matrix)

        terms = self.vectorizer.get_feature_names_out()
        order_centroids = kmeans.cluster_centers_.argsort()[:, ::-1]

        df_copy = self.tickets_df.copy()
        df_copy["cluster"] = labels

        topics = []
        for i in range(n_clusters):
            cluster_rows = df_copy[df_copy["cluster"] == i]
            top_terms = [terms[ind] for ind in order_centroids[i, :5]]
            
            # Dominant category in cluster
            top_cat = cluster_rows["category"].mode()[0] if not cluster_rows.empty else "General"
            avg_resol = round(cluster_rows["resolution_time_hrs"].mean(), 1) if not cluster_rows.empty else 0.0
            avg_csat = round(cluster_rows["customer_rating"].mean(), 2) if not cluster_rows.empty else 0.0

            sample_issues = cluster_rows["issue_summary"].head(3).tolist()

            topics.append({
                "topic_id": i + 1,
                "keywords": top_terms,
                "dominant_category": top_cat,
                "ticket_count": len(cluster_rows),
                "avg_resolution_hrs": avg_resol,
                "avg_csat": avg_csat,
                "sample_issues": sample_issues
            })

        topics.sort(key=lambda x: x["ticket_count"], reverse=True)
        return topics

    def diagnose_anomaly(self, ticket_id: str) -> Dict[str, Any]:
        """Deep AI Root-Cause Diagnostic for a flagged ticket."""
        rows = self.db.execute_query(
            "SELECT * FROM support_tickets WHERE ticket_id = ?;", (ticket_id,)
        )
        if not rows:
            return {"error": f"Ticket {ticket_id} not found"}

        t = rows[0]
        cat = t["category"]
        agent = t["agent_id"]
        resol_time = t.get("resolution_time_hrs")
        resp_time = t.get("response_time_hrs")
        status = t["status"]
        priority = t["priority"]

        # Benchmarks for context
        cat_stats = self.db.execute_query(
            "SELECT AVG(resolution_time_hrs) as avg_resol, AVG(response_time_hrs) as avg_resp FROM support_tickets WHERE category = ? AND status = 'Resolved';",
            (cat,)
        )[0]
        agent_stats = self.db.execute_query(
            "SELECT AVG(resolution_time_hrs) as avg_resol, COUNT(*) as resolved_cnt FROM support_tickets WHERE agent_id = ? AND status = 'Resolved';",
            (agent,)
        )[0]

        cat_avg_resol = round(cat_stats["avg_resol"] or 0.0, 1)
        agent_avg_resol = round(agent_stats["avg_resol"] or 0.0, 1)

        # Synthesize diagnostic root causes
        findings = []
        if resol_time and resol_time > cat_avg_resol * 2.0:
            findings.append(f"Resolution time ({resol_time:.1f}h) is {resol_time / max(cat_avg_resol, 1):.1f}x higher than the {cat} category benchmark ({cat_avg_resol}h).")
        if resp_time and resp_time > 3.5:
            findings.append(f"Initial agent response was delayed by {resp_time:.1f}h, indicating intake bottleneck.")
        if status in ("Open", "Escalated") and priority in ("Critical", "High"):
            findings.append(f"Ticket remains {status} despite {priority} urgency classification, constituting an active SLA breach.")

        # Find similar historical tickets
        similar = self.search_similar(t["issue_summary"], top_k=3)
        similar_ids = [s["ticket_id"] for s in similar if s["ticket_id"] != ticket_id]

        # Recommended Playbook
        actions = []
        if priority == "Critical":
            actions.append("Initiate immediate swarming session with on-call Tier 3 engineers.")
        actions.append(f"Review handoff logs between intake triage and agent {agent}.")
        actions.append("Correlate issue keywords against recent platform deployment notes.")

        diagnosis_summary = " ".join(findings) if findings else "Ticket metrics deviate from standard operational tolerances."

        return {
            "ticket_id": ticket_id,
            "category": cat,
            "priority": priority,
            "status": status,
            "agent_id": agent,
            "resolution_time_hrs": resol_time,
            "category_benchmark_resol_hrs": cat_avg_resol,
            "agent_benchmark_resol_hrs": agent_avg_resol,
            "issue_summary": t["issue_summary"],
            "diagnostic_summary": diagnosis_summary,
            "findings": findings,
            "similar_tickets": similar_ids,
            "action_playbook": actions
        }


semantic_engine = SemanticEngine()
