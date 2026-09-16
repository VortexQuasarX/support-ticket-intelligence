"""Pydantic request and response models for REST API."""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class QueryRequest(BaseModel):
    query: str = Field(..., min_length=2, json_schema_extra={"example": "How many tickets are currently open?"})


class QueryResponse(BaseModel):
    question: str
    sql: str
    answer: str
    data: List[Dict[str, Any]]
    row_count: int
    execution_time_ms: float
    chart_type: str
    provider: str
    success: bool
    error: Optional[str] = None


class AnomalyItem(BaseModel):
    ticket_id: str
    created_at: str
    category: str
    priority: str
    status: str
    agent_id: str
    issue_summary: str
    anomaly_type: str
    severity: str
    score: float
    metric_name: str
    metric_value: Any
    threshold: Any
    description: str
    recommendation: str


class AnomalyResponse(BaseModel):
    total_anomalies: int
    critical_count: int
    warning_count: int
    anomalies: List[AnomalyItem]


class HealthResponse(BaseModel):
    status: str
    database_connected: bool
    total_tickets: int
    llm_provider: str
    version: str = "1.0.0"
