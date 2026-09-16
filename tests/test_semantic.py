import pytest
from app.analytics.semantic_engine import semantic_engine
from app.nlp.query_service import query_service


def test_semantic_search_similar_returns_matches():
    results = semantic_engine.search_similar("system login failure", top_k=5)
    assert isinstance(results, list)
    assert len(results) > 0
    # Top match should be login related
    assert any("login" in r["issue_summary"].lower() for r in results)


def test_topic_discovery_clusters():
    topics = semantic_engine.discover_topics(n_clusters=3)
    assert len(topics) == 3
    for t in topics:
        assert "keywords" in t
        assert len(t["keywords"]) > 0
        assert t["ticket_count"] > 0


def test_anomaly_diagnosis_engine():
    diag = semantic_engine.diagnose_anomaly("TKT-108")
    assert "ticket_id" in diag
    assert diag["ticket_id"] == "TKT-108"
    assert "diagnostic_summary" in diag
    assert "action_playbook" in diag
    assert len(diag["action_playbook"]) > 0


def test_hybrid_query_service_semantic_routing():
    res = query_service.process_query("Find tickets related to login failure")
    assert res["success"] is True
    assert res["row_count"] > 0
    assert "login" in res["answer"].lower() or "login" in str(res["data"]).lower()
