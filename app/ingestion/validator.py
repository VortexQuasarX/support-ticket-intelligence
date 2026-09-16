"""Pydantic schemas and validation for ingested ticket data."""

from datetime import datetime
from typing import Optional, Literal
from pydantic import BaseModel, Field, field_validator


class TicketRecord(BaseModel):
    ticket_id: str = Field(..., description="Unique ticket identifier")
    created_at: datetime = Field(..., description="Creation timestamp")
    category: Literal["Billing", "Technical", "General"] = Field(..., description="Ticket category")
    priority: Literal["Low", "Medium", "High", "Critical"] = Field(..., description="Urgency level")
    status: Literal["Open", "Resolved", "Escalated"] = Field(..., description="Current status")
    response_time_hrs: float = Field(..., ge=0.0, description="Response time in hours")
    resolution_time_hrs: Optional[float] = Field(None, ge=0.0, description="Resolution time in hours")
    agent_id: str = Field(..., description="Assigned agent ID")
    customer_rating: Optional[int] = Field(None, ge=1, le=5, description="CSAT score (1-5)")
    issue_summary: str = Field(..., min_length=1, description="Brief description of issue")

    @field_validator("created_at", mode="before")
    @classmethod
    def parse_created_at(cls, v):
        if isinstance(v, str):
            return datetime.strptime(v.strip(), "%Y-%m-%d %H:%M")
        return v

    @field_validator("resolution_time_hrs", mode="before")
    @classmethod
    def parse_resolution_time(cls, v):
        if v is None or v == "" or (isinstance(v, float) and v != v):
            return None
        return float(v)

    @field_validator("customer_rating", mode="before")
    @classmethod
    def parse_rating(cls, v):
        if v is None or v == "" or (isinstance(v, float) and v != v):
            return None
        return int(float(v))
