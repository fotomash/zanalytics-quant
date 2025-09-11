"""Pydantic models for MCP2 payloads."""
from __future__ import annotations

from datetime import datetime
from pydantic import BaseModel


class BasePayload(BaseModel):
    """Base payload model shared across MCP2 endpoints."""

    strategy: str
    symbol: str
    timeframe: str
    date: datetime
    volume_profile: dict | None = None
    price_context: dict | None = None
    entry_idea: str | None = None
    llm_analysis: str | None = None
    vector_id: str | None = None
