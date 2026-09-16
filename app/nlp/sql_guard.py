"""SQL security sanitization and guardrails."""

import re
from typing import Tuple

FORBIDDEN_KEYWORDS = [
    r"\bINSERT\b", r"\bUPDATE\b", r"\bDELETE\b", r"\bDROP\b",
    r"\bALTER\b", r"\bCREATE\b", r"\bREPLACE\b", r"\bTRUNCATE\b",
    r"\bATTACH\b", r"\bDETACH\b", r"\bPRAGMA\b", r"\bVACUUM\b",
    r"\bEXEC\b", r"\bEXECUTE\b", r"\bUNION\s+ALL\s+SELECT\s+.*\bFROM\s+sqlite_master\b"
]

ALLOWED_TABLES = [
    "support_tickets",
    "v_agent_performance",
    "v_category_summary"
]


class SQLGuard:
    @staticmethod
    def clean_markdown(sql_candidate: str) -> str:
        """Strip markdown code fences and extraneous whitespace."""
        text = sql_candidate.strip()
        # Strip ```sql or ```
        text = re.sub(r"^```(?:sql)?\s*", "", text, flags=re.IGNORECASE)
        text = re.sub(r"\s*```$", "", text)
        return text.strip().rstrip(";")

    @classmethod
    def validate_and_sanitize(cls, raw_sql: str) -> Tuple[bool, str, str]:
        """
        Validate SQL for security and correctness.
        Returns: (is_valid: bool, sanitized_sql: str, reason: str)
        """
        sql = cls.clean_markdown(raw_sql)

        if not sql:
            return False, "", "Empty SQL query provided."

        # Check for multiple statements separated by semicolon
        if ";" in sql:
            return False, "", "Multiple SQL statements are not permitted for security."

        # Verify query starts with SELECT or WITH
        upper_sql = sql.upper().strip()
        if not (upper_sql.startswith("SELECT") or upper_sql.startswith("WITH")):
            return False, "", "Only read-only SELECT queries are allowed."

        # Check for forbidden DDL / DML operations
        for pattern in FORBIDDEN_KEYWORDS:
            if re.search(pattern, sql, re.IGNORECASE):
                return False, "", f"Forbidden operation detected: {pattern}"

        # Prevent access to sqlite system tables
        if re.search(r"\bsqlite_\w+", sql, re.IGNORECASE):
            return False, "", "Access to internal SQLite metadata tables is forbidden."

        # Append LIMIT if query selects raw rows without aggregation or limit
        if not re.search(r"\bLIMIT\s+\d+\b", sql, re.IGNORECASE):
            sql = f"{sql} LIMIT 100"

        return True, sql, "OK"
