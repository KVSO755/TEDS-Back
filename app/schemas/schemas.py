from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional
from app.models.models import DistractionType


class DistractionEventIn(BaseModel):
    type: DistractionType
    timestamp: str = Field(
        ...,
        pattern=r"^\d{4}-\d{2}-\d{2}\|\d{2}:\d{2}:\d{2}$",
        description="Formato: 2026-04-12|14:35:22"
    )
    duration_seconds: float = Field(..., ge=0)


class DistractionEventOut(BaseModel):
    id: int
    session_id: str
    type: DistractionType
    timestamp: str
    duration_seconds: float

    model_config = {"from_attributes": True}


class SessionOut(BaseModel):
    id: str
    started_at: datetime
    ended_at: Optional[datetime] = None
    synced: bool
    event_count: int = 0

    model_config = {"from_attributes": True}


class WSMessage(BaseModel):
    action: str
    payload: dict = {}
