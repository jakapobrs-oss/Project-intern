"""Pydantic schemas — presentation"""
import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class PresentationZoneIn(BaseModel):
    zone_key: str = Field(..., min_length=1, max_length=64)
    content_id: uuid.UUID
    params_json: dict = {}
    order_index: int = 0


class PresentationZoneOut(PresentationZoneIn):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID


class PresentationBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: str = ""
    layout_json: dict = Field(default_factory=dict)
    duration_sec: int = Field(30, ge=1, le=86400)


class PresentationCreate(PresentationBase):
    zones: list[PresentationZoneIn] = []


class PresentationUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    layout_json: dict | None = None
    duration_sec: int | None = Field(None, ge=1, le=86400)
    zones: list[PresentationZoneIn] | None = None


class PresentationOut(PresentationBase):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    created_by: uuid.UUID
    created_at: datetime
    updated_at: datetime
    zones: list[PresentationZoneOut] = []
