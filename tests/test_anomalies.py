import pytest
from app.analytics.anomaly_engine import anomaly_detector


def test_anomaly_detection_runs():
    anomalies = anomaly_detector.detect_all()
    assert isinstance(anomalies, list)
    assert len(anomalies) > 0


def test_critical_sla_anomaly_flagging():
    anomalies = anomaly_detector.detect_all(min_severity="CRITICAL")
    critical_items = [a for a in anomalies if a["severity"] == "CRITICAL"]
    assert len(critical_items) > 0

    for item in critical_items:
        assert "score" in item
        assert item["score"] >= 80.0
        assert "recommendation" in item
        assert len(item["recommendation"]) > 0


def test_statistical_outlier_detection():
    anomalies = anomaly_detector.detect_all()
    outliers = [a for a in anomalies if a["anomaly_type"] == "RESOLUTION_TIME_OUTLIER"]
    assert len(outliers) > 0
    # Longest resolution times should be flagged
    for o in outliers:
        assert float(o["metric_value"]) > 40.0
