"""Hybrid Query Orchestrator: Combines Text-to-SQL with Semantic Search."""

import logging
import re
import time
from typing import Any, Dict, List, Optional

from app.analytics.semantic_engine import semantic_engine
from app.database.db_manager import db_manager, DatabaseManager
from app.nlp.llm_client import llm_client, LLMClient
from app.nlp.sql_guard import SQLGuard

logger = logging.getLogger(__name__)


class QueryService:
    def __init__(self, db: Optional[DatabaseManager] = None, llm: Optional[LLMClient] = None):
        self.db = db or db_manager
        self.llm = llm or llm_client
        self.guard = SQLGuard()
        self.semantic = semantic_engine

    def is_semantic_intent(self, q: str) -> bool:
        """Detect if the query is asking for qualitative/semantic discovery rather than aggregation."""
        text = q.lower()
        semantic_triggers = [
            r"\bfind\s+tickets?\s+(about|related|similar|mentioning)\b",
            r"\bsearch\s+for\b",
            r"\bcommon\s+(complaints|issues|problems)\b",
            r"\btopics?\b",
            r"\bclustering\b",
            r"\btickets?\s+mentioning\b",
            r"\bwhat\s+are\s+customers?\s+complaining\s+about\b"
        ]
        return any(re.search(pattern, text) for pattern in semantic_triggers)

    def process_query(self, question: str) -> Dict[str, Any]:
        """Process natural language query end-to-end with self-healing and hybrid routing."""
        start_time = time.perf_counter()
        provider_name = self.llm.get_active_provider_name()

        # Semantic Hybrid Branch
        if self.is_semantic_intent(question):
            return self._handle_semantic_query(question, start_time, provider_name)

        # Quantitative SQL Branch
        return self._handle_sql_query(question, start_time, provider_name)

    def _handle_semantic_query(self, question: str, start_time: float, provider: str) -> Dict[str, Any]:
        """Handle semantic search and topic discovery queries."""
        text = question.lower()
        
        # Topic discovery
        if "common" in text or "topics" in text or "clusters" in text:
            topics = self.semantic.discover_topics(n_clusters=4)
            duration = (time.perf_counter() - start_time) * 1000
            answer = (
                f"Discovered **{len(topics)} core issue themes** across support tickets: "
                + "; ".join([f"**Topic {t['topic_id']}** ({', '.join(t['keywords'][:3])})" for t in topics])
                + "."
            )
            return {
                "question": question,
                "sql": "-- Semantic Clustering via TF-IDF & K-Means over issue_summary",
                "sanitized_sql": "",
                "answer": answer,
                "data": topics,
                "row_count": len(topics),
                "execution_time_ms": round(duration, 2),
                "chart_type": "table",
                "provider": f"{provider} + Scikit-Learn TF-IDF",
                "success": True,
                "error": None
            }

        # Semantic search for symptoms
        cleaned_query = re.sub(r"^(find|search for|show me|tickets about|tickets related to)\s*", "", question, flags=re.IGNORECASE)
        results = self.semantic.search_similar(cleaned_query, top_k=10)
        duration = (time.perf_counter() - start_time) * 1000

        if not results:
            answer = f"No tickets found semantically matching '{cleaned_query}'."
        else:
            top_ids = ", ".join([r["ticket_id"] for r in results[:3]])
            answer = f"Found **{len(results)} tickets** semantically related to '{cleaned_query}'. Top matches: {top_ids}."

        return {
            "question": question,
            "sql": f"-- Semantic Vector Similarity Query for: '{cleaned_query}'",
            "sanitized_sql": "",
            "answer": answer,
            "data": results,
            "row_count": len(results),
            "execution_time_ms": round(duration, 2),
            "chart_type": "table",
            "provider": f"{provider} + Cosine Similarity",
            "success": True,
            "error": None
        }

    def _handle_sql_query(self, question: str, start_time: float, provider_name: str) -> Dict[str, Any]:
        """Generate, validate, and execute SQL query with self-healing retry."""
        # Step 1: Generate initial SQL
        raw_sql = self.llm.generate_sql(question)

        # Step 2: Validate & Sanitize SQL
        is_valid, sanitized_sql, reason = self.guard.validate_and_sanitize(raw_sql)
        if not is_valid:
            return {
                "question": question,
                "sql": raw_sql,
                "sanitized_sql": "",
                "answer": f"I cannot execute that query due to security rules: {reason}",
                "data": [],
                "row_count": 0,
                "execution_time_ms": round((time.perf_counter() - start_time) * 1000, 2),
                "chart_type": "none",
                "provider": provider_name,
                "success": False,
                "error": reason
            }

        # Step 3: Execute SQL with Self-Healing Retry
        data: List[Dict[str, Any]] = []
        last_error = None
        executed_sql = sanitized_sql

        for attempt in range(2):
            try:
                data = self.db.execute_query(executed_sql, read_only=True)
                last_error = None
                break
            except Exception as exc:
                last_error = str(exc)
                logger.warning(f"SQL execution attempt {attempt+1} failed: {last_error}")
                fixed_sql = self.llm.fix_sql(question, executed_sql, last_error)
                is_valid, safe_fixed, _ = self.guard.validate_and_sanitize(fixed_sql)
                if is_valid:
                    executed_sql = safe_fixed
                else:
                    break

        execution_duration = (time.perf_counter() - start_time) * 1000

        if last_error:
            return {
                "question": question,
                "sql": executed_sql,
                "sanitized_sql": executed_sql,
                "answer": f"Failed to execute query after self-healing attempt: {last_error}",
                "data": [],
                "row_count": 0,
                "execution_time_ms": round(execution_duration, 2),
                "chart_type": "none",
                "provider": provider_name,
                "success": False,
                "error": last_error
            }

        # Step 4: Synthesize human-readable answer
        answer = self.llm.synthesize_answer(question, executed_sql, data)

        # Step 5: Recommend chart type
        chart_type = self._recommend_chart(data)

        return {
            "question": question,
            "sql": executed_sql,
            "sanitized_sql": executed_sql,
            "answer": answer,
            "data": data,
            "row_count": len(data),
            "execution_time_ms": round(execution_duration, 2),
            "chart_type": chart_type,
            "provider": provider_name,
            "success": True,
            "error": None
        }

    def _recommend_chart(self, data: List[Dict[str, Any]]) -> str:
        """Suggest optimal visualization layout for UI rendering."""
        if not data:
            return "none"
        if len(data) == 1 and len(data[0]) == 1:
            return "metric_card"
        if len(data) > 1 and len(data[0]) == 2:
            keys = list(data[0].keys())
            if any("time" in k or "date" in k or "month" in k for k in keys):
                return "line_chart"
            return "bar_chart"
        if len(data) > 1 and len(data[0]) > 2:
            return "table"
        return "table"


query_service = QueryService()
