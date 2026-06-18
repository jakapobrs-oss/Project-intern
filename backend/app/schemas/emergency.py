"""
Schemas สำหรับ Emergency Broadcast endpoint
"""
from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.models.emergency import EmergencyKind, EmergencyStatus


class EmergencyTarget(BaseModel):
    """target ของ broadcast — ว่างหมด = all devices"""
    all: bool = False
    device_ids: list[UUID] = Field(default_factory=list)
    group_ids: list[UUID] = Field(default_factory=list)


class EmergencyCreate(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    kind: EmergencyKind
    payload: dict[str, Any] = Field(default_factory=dict)
    target: EmergencyTarget = Field(default_factory=EmergencyTarget)
    priority: int = 1000
    starts_at: datetime | None = None
    ends_at: datetime | None = None
    requires_ack: bool = False
    notes: str | None = None


class EmergencyUpdate(BaseModel):
    title: str | None = None
    payload: dict[str, Any] | None = None
    target: EmergencyTarget | None = None
    priority: int | None = None
    starts_at: datetime | None = None
    ends_at: datetime | None = None
    notes: str | None = None


class EmergencyOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    title: str
    kind: EmergencyKind
    payload: dict[str, Any]
    target: dict[str, Any]
    status: EmergencyStatus
    priority: int
    starts_at: datetime | None
    ends_at: datetime | None
    requires_ack: bool
    acknowledged_at: datetime | None
    created_by: UUID
    created_at: datetime
    updated_at: datetime
