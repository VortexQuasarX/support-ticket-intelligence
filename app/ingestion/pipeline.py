"""Data ingestion pipeline: loads, validates, and stores tickets into SQLite."""

import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional
import pandas as pd
from pydantic import ValidationError

from app.config import CSV_FILE_PATH
from app.database.db_manager import db_manager, DatabaseManager
from app.ingestion.validator import TicketRecord

logger = logging.getLogger(__name__)


class IngestionPipeline:
    def __init__(self, db: Optional[DatabaseManager] = None):
        self.db = db or db_manager

    def run(self, csv_path: Optional[Path] = None, force_reload: bool = False) -> Dict[str, Any]:
        """Run the ingestion pipeline on the specified CSV file."""
        csv_file = Path(csv_path or CSV_FILE_PATH)
        if not csv_file.exists():
            raise FileNotFoundError(f"CSV file not found at: {csv_file}")

        self.db.init_database()
        existing_count = self.db.get_ticket_count()

        if existing_count > 0 and not force_reload:
            logger.info(f"Database already contains {existing_count} records. Skipping re-ingestion.")
            return {
                "status": "skipped",
                "message": f"Database already contains {existing_count} records.",
                "total_records": existing_count
            }

        df = pd.read_csv(csv_file)
        logger.info(f"Loaded {len(df)} rows from {csv_file.name}")

        valid_records: List[TicketRecord] = []
        validation_errors: List[Dict[str, Any]] = []

        for idx, row in df.iterrows():
            try:
                record_dict = row.to_dict()
                validated = TicketRecord(**record_dict)
                valid_records.append(validated)
            except ValidationError as e:
                validation_errors.append({"row": idx + 1, "errors": e.errors()})

        # Clear table if reload requested
        if force_reload:
            with self.db.get_connection(read_only=False) as conn:
                conn.execute("DELETE FROM support_tickets;")

        # Bulk insert
        insert_sql = """
        INSERT OR REPLACE INTO support_tickets (
            ticket_id, created_at, category, priority, status,
            response_time_hrs, resolution_time_hrs, agent_id,
            customer_rating, issue_summary
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
        """

        tuples = [
            (
                r.ticket_id,
                r.created_at.strftime("%Y-%m-%d %H:%M:%S"),
                r.category,
                r.priority,
                r.status,
                r.response_time_hrs,
                r.resolution_time_hrs,
                r.agent_id,
                r.customer_rating,
                r.issue_summary
            )
            for r in valid_records
        ]

        with self.db.get_connection(read_only=False) as conn:
            conn.executemany(insert_sql, tuples)

        summary = {
            "status": "success",
            "source_file": str(csv_file),
            "rows_read": len(df),
            "records_inserted": len(valid_records),
            "validation_errors_count": len(validation_errors),
            "categories": df["category"].value_counts().to_dict(),
            "statuses": df["status"].value_counts().to_dict(),
            "earliest_ticket": str(df["created_at"].min()),
            "latest_ticket": str(df["created_at"].max())
        }

        logger.info(f"Successfully ingested {len(valid_records)} tickets into database.")
        return summary


ingestion_pipeline = IngestionPipeline()
