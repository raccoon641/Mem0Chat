from __future__ import annotations

from datetime import datetime
from typing import Optional, Literal

from pydantic import BaseModel, Field


class UserCreate(BaseModel):
    whatsapp_user_id: str
    phone_number: Optional[str] = None
    timezone: str = Field(default="UTC")


class UserRead(BaseModel):
    id: int
    whatsapp_user_id: str
    phone_number: Optional[str]
    timezone: str
    created_at: datetime

    class Config:
        from_attributes = True


class InteractionRead(BaseModel):
    id: int
    user_id: int
    twilio_message_sid: Optional[str]
    message_direction: str
    message_type: str
    body_text: Optional[str]
    occurred_at: datetime
    created_at: datetime

    class Config:
        from_attributes = True


class MemoryCreate(BaseModel):
    memory_type: Literal["text", "image", "audio"]
    text: Optional[str] = None
    media_url: Optional[str] = None
    labels: Optional[list[str]] = None


class MemoryRead(BaseModel):
    id: int
    user_id: int
    interaction_id: Optional[int]
    mem0_id: Optional[str]
    memory_type: str
    title: Optional[str]
    text: Optional[str]
    labels_json: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True


class SearchResponseItem(BaseModel):
    memory: MemoryRead
    score: Optional[float] = None
    source_interaction: Optional[InteractionRead] = None


class AnalyticsSummary(BaseModel):
    total_users: int
    total_interactions: int
    total_memories: int
    memories_by_type: dict
    last_ingest_time: Optional[datetime] 