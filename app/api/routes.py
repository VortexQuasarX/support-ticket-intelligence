"""REST API endpoints: /health, /api/query, /api/anomalies, /api/kpis, /api/tickets."""

from typing import Optional
from fastapi import APIRouter, HTTPException, Query

from app.analytics.anomaly_engine import anomaly_detector
from app.analytics.kpi_engine import kpi_engine
from app.api.schemas import (
    QueryRequest,
    QueryResponse,
    AnomalyResponse,
    HealthResponse
)
from app.database.db_manager import db_manager
from app.nlp.llm_client import llm_client
from app.nlp.query_service import query_service

router = APIRouter()


@router.get("/health", response_model=HealthResponse, tags=["System"])
def health_check():
    """System health check, DB status, ticket count, and active LLM provider."""
    count = db_manager.get_ticket_count()
    return HealthResponse(
        status="healthy",
        database_connected=True,
        total_tickets=count,
        llm_provider=llm_client.get_active_provider_name()
    )


@router.post("/api/query", response_model=QueryResponse, tags=["Natural Language AI"])
def query_tickets(req: QueryRequest):
    """Ask questions in natural language about tickets; generates and executes SQL."""
    try:
        result = query_service.process_query(req.query)
        return QueryResponse(**result)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/api/anomalies", response_model=AnomalyResponse, tags=["Anomaly Detection"])
def get_anomalies(
    min_severity: Optional[str] = Query(None, description="Filter by minimum severity: CRITICAL, HIGH, WARNING"),
    limit: int = Query(50, ge=1, le=500, description="Max anomalies to return")
):
    """Detect and flag operational SLA breaches and statistical outliers."""
    all_anomalies = anomaly_detector.detect_all(min_severity=min_severity)
    critical_count = sum(1 for a in all_anomalies if a["severity"] == "CRITICAL")
    warning_count = sum(1 for a in all_anomalies if a["severity"] in ("WARNING", "HIGH"))

    return AnomalyResponse(
        total_anomalies=len(all_anomalies),
        critical_count=critical_count,
        warning_count=warning_count,
        anomalies=all_anomalies[:limit]
    )


@router.get("/api/kpis", tags=["Analytics"])
def get_kpis():
    """Retrieve executive KPIs, SLA compliance rates, and agent metrics."""
    return kpi_engine.get_executive_summary()


@router.get("/api/tickets", tags=["Tickets"])
def get_tickets(
    status: Optional[str] = Query(None, description="Filter by status: Open, Resolved, Escalated"),
    priority: Optional[str] = Query(None, description="Filter by priority: Low, Medium, High, Critical"),
    category: Optional[str] = Query(None, description="Filter by category: Billing, Technical, General"),
    agent_id: Optional[str] = Query(None, description="Filter by agent ID: e.g. AGT-04"),
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0)
):
    """Query raw tickets with optional filtering and pagination."""
    clauses = []
    params = []

    if status:
        clauses.append("status = ?")
        params.append(status)
    if priority:
        clauses.append("priority = ?")
        params.append(priority)
    if category:
        clauses.append("category = ?")
        params.append(category)
    if agent_id:
        clauses.append("agent_id = ?")
        params.append(agent_id)

    where_sql = f"WHERE {' AND '.join(clauses)}" if clauses else ""
    sql = f"""
        SELECT ticket_id, created_at, category, priority, status,
               response_time_hrs, resolution_time_hrs, agent_id,
               customer_rating, issue_summary
        FROM support_tickets
        {where_sql}
        ORDER BY created_at DESC
        LIMIT ? OFFSET ?;
    """
    params.extend([limit, offset])
    rows = db_manager.execute_query(sql, tuple(params))
    return {"total": len(rows), "tickets": rows}
