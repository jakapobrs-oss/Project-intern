"""Pydantic schemas — plan + schedule"""
import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.schedule import ScheduleStatus

# ===== Plan =====

class PlanItemIn(BaseModel):
    presentation_id: uuid.UUID
    order_index: int = 0
    duration_sec_override: int | None = None


class PlanItemOut(PlanItemIn):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID


class PlanBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: str = ""


class PlanCreate(PlanBase):
    items: list[PlanItemIn] = []


class PlanUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    items: list[PlanItemIn] | None = None


class PlanOut(PlanBase):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    created_by: uuid.UUID
    created_at: datetime
    updated_at: datetime
    items: list[PlanItemOut] = []


# ===== Schedule =====

class ScheduleBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: str = ""
    plan_id: uuid.UUID
    player_group_id: uuid.UUID
    start_at: datetime
    end_at: datetime | None = None
    repeat_rule: str | None = None
    daily_window_start: str | None = Field(None, pattern=r"^\d{2}:\d{2}$")
    daily_window_end: str | None = Field(None, pattern=r"^\d{2}:\d{2}$")
    priority: int = Field(100, ge=0, le=1000)


class ScheduleCreate(ScheduleBase):
    pass


class ScheduleUpdate(BaseModel):
    name: str | None = None
    description: str | None = None
    start_at: datetime | None = None
    end_at: datetime | None = None
    repeat_rule: str | None = None
    daily_window_start: str | None = None
    daily_window_end: str | None = None
    priority: int | None = None
    status: ScheduleStatus | None = None


class ScheduleOut(ScheduleBase):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    status: ScheduleStatus
    created_by: uuid.UUID
    approved_by: uuid.UUID | None
    approved_at: datetime | None
    is_active: bool
    created_at: datetime
    updated_at: datetime
