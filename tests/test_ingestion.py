import pytest
from app.database.db_manager import db_manager
from app.ingestion.pipeline import ingestion_pipeline


def test_database_initialization():
    db_manager.init_database()
    assert db_manager.get_ticket_count() >= 0


def test_csv_ingestion_success():
    summary = ingestion_pipeline.run(force_reload=True)
    assert summary["status"] == "success"
    assert summary["records_inserted"] == 500
    assert summary["validation_errors_count"] == 0

    count = db_manager.get_ticket_count()
    assert count == 500


def test_data_integrity_and_null_semantics():
    # Verify unresolved tickets have null resolution time
    rows = db_manager.execute_query("""
        SELECT COUNT(*) as count FROM support_tickets 
        WHERE status IN ('Open', 'Escalated') AND resolution_time_hrs IS NOT NULL;
    """)
    assert rows[0]["count"] == 0

    # Verify resolved tickets have resolution time
    rows = db_manager.execute_query("""
        SELECT COUNT(*) as count FROM support_tickets 
        WHERE status = 'Resolved' AND resolution_time_hrs IS NULL;
    """)
    assert rows[0]["count"] == 0
