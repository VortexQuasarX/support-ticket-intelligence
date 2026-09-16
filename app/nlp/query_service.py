"""Query Orchestrator: NL -> SQL -> Validation -> Execution -> Self-Healing -> NL Answer."""

import logging
import time
from typing import Any, Dict, List, Optional

from app.database.db_manager import db_manager, DatabaseManager
from app.nlp.llm_client import llm_client, LLMClient
from app.nlp.sql_guard import SQLGuard

logger = logging.getLogger(__name__)


class QueryService:
    def __init__(self, db: Optional[DatabaseManager] = None, llm: Optional[LLMClient] = None):
        self.db = db or db_manager
        self.llm = llm or llm_client
        self.guard = SQLGuard()

    def process_query(self, question: str) -> Dict[str, Any]:
        """Process natural language query end-to-end with self-healing."""
        start_time = time.perf_counter()
        provider_name = self.llm.get_active_provider_name()

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

        for attempt in range(2):  # Max 1 retry
            try:
                data = self.db.execute_query(executed_sql, read_only=True)
                last_error = None
                break
            except Exception as exc:
                last_error = str(exc)
                logger.warning(f"SQL execution attempt {attempt+1} failed: {last_error}")
                # Attempt self-healing via LLM
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
