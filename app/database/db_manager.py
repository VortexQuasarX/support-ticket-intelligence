"""Thread-safe SQLite database manager with read-only query guardrails."""

import sqlite3
from pathlib import Path
from typing import Any, Dict, List, Optional
from contextlib import contextmanager

from app.config import DB_FILE_PATH
from app.database.schema import CREATE_TABLE_SQL, CREATE_INDEXES_SQL, CREATE_VIEWS_SQL


class DatabaseManager:
    def __init__(self, db_path: Optional[Path] = None):
        self.db_path = str(db_path or DB_FILE_PATH)
        self._ensure_db_dir()

    def _ensure_db_dir(self):
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)

    @contextmanager
    def get_connection(self, read_only: bool = False):
        conn = sqlite3.connect(self.db_path, timeout=15.0)
        conn.row_factory = sqlite3.Row
        try:
            if read_only:
                conn.execute("PRAGMA query_only = ON;")
            yield conn
            if not read_only:
                conn.commit()
        except Exception:
            if not read_only:
                conn.rollback()
            raise
        finally:
            conn.close()

    def init_database(self) -> None:
        """Initialize tables, indexes, and views."""
        with self.get_connection(read_only=False) as conn:
            conn.execute("PRAGMA journal_mode = WAL;")
            conn.execute("PRAGMA synchronous = NORMAL;")
            conn.execute(CREATE_TABLE_SQL)
            for idx_sql in CREATE_INDEXES_SQL:
                conn.execute(idx_sql)
            for view_sql in CREATE_VIEWS_SQL:
                conn.execute(view_sql)

    def execute_query(self, sql: str, params: tuple = (), read_only: bool = True) -> List[Dict[str, Any]]:
        """Execute a query and return rows as list of dictionaries."""
        with self.get_connection(read_only=read_only) as conn:
            cursor = conn.cursor()
            cursor.execute(sql, params)
            rows = cursor.fetchall()
            return [dict(row) for row in rows]

    def execute_scalar(self, sql: str, params: tuple = ()) -> Any:
        """Execute query and return the first column of the first row."""
        with self.get_connection(read_only=True) as conn:
            cursor = conn.cursor()
            cursor.execute(sql, params)
            row = cursor.fetchone()
            if row:
                return row[0]
            return None

    def execute_non_query(self, sql: str, params: tuple = ()) -> int:
        """Execute INSERT/UPDATE/DELETE and return affected rows count."""
        with self.get_connection(read_only=False) as conn:
            cursor = conn.cursor()
            cursor.execute(sql, params)
            return cursor.rowcount

    def get_ticket_count(self) -> int:
        """Get total count of tickets in database."""
        try:
            count = self.execute_scalar("SELECT COUNT(*) FROM support_tickets;")
            return int(count) if count is not None else 0
        except Exception:
            return 0


# Global instance
db_manager = DatabaseManager()
