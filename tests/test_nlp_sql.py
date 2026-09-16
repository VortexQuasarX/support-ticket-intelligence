import pytest
from app.nlp.sql_guard import SQLGuard
from app.nlp.query_service import query_service


def test_sql_guard_blocks_destructive_commands():
    guard = SQLGuard()
    dangerous_queries = [
        "DROP TABLE support_tickets;",
        "DELETE FROM support_tickets WHERE 1=1;",
        "UPDATE support_tickets SET status = 'Resolved';",
        "INSERT INTO support_tickets VALUES ('x');",
        "SELECT * FROM support_tickets; DROP TABLE users;"
    ]
    for q in dangerous_queries:
        is_valid, _, reason = guard.validate_and_sanitize(q)
        assert not is_valid, f"Failed to block: {q} (reason: {reason})"


def test_sql_guard_allows_safe_selects():
    guard = SQLGuard()
    safe_queries = [
        "SELECT COUNT(*) FROM support_tickets WHERE status = 'Open'",
        "SELECT agent_id, AVG(customer_rating) FROM support_tickets GROUP BY agent_id"
    ]
    for q in safe_queries:
        is_valid, sanitized, _ = guard.validate_and_sanitize(q)
        assert is_valid
        assert "LIMIT" in sanitized


def test_sample_assessment_queries():
    test_cases = [
        ("How many tickets are currently open?", 111),
        ("Which agent resolved the most tickets this month?", "AGT-01"),
        ("What is the average customer rating for Technical category tickets?", 3.74)
    ]
    for prompt, expected_val in test_cases:
        res = query_service.process_query(prompt)
        assert res["success"] is True
        assert res["row_count"] >= 1
        assert str(expected_val) in str(res["data"]) or str(expected_val) in res["answer"]
