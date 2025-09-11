from datetime import datetime
from pydantic import BaseModel


class StrategyPayload(BaseModel):
    strategy: str
    symbol: str
    timeframe: str
    date: datetime
    notes: str | None = None


class DocRecord(BaseModel):
    id: int
    content: str
