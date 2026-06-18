"""
Schedule model — ผูก plan ↔ player_group + ช่วงเวลา + priority
ดู §23 scheduler edge cases
"""
import enum
import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, Uuid, func
from sqlalchemy import Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class ScheduleStatus(str, enum.Enum):
    DRAFT = "draft"
    PENDING_APPROVAL = "pending_approval"
    ACTIVE = "active"
    PAUSED = "paused"
    EXPIRED = "expired"


class Schedule(Base):
    """Schedule = เมื่อไหร่ ใครเล่นอะไร — priority stack ตาม §23"""
    __tablename__ = "schedules"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    description: Mapped[str] = mapped_column(Text, default="", nullable=False)

    plan_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("plans.id"), nullable=False, index=True)
    player_group_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("player_groups.id"), nullable=False, index=True)

    # ช่วงเวลา
    start_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    end_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, index=True)

    # RRULE (iCal) สำหรับ recurrence — §23
    repeat_rule: Mapped[str | None] = mapped_column(String(512), nullable=True)

    # day-parting: เล่นเฉพาะช่วงเวลาในวัน (HH:MM-HH:MM)
    daily_window_start: Mapped[str | None] = mapped_column(String(8), nullable=True)
    daily_window_end: Mapped[str | None] = mapped_column(String(8), nullable=True)

    # priority — เลขมาก = สำคัญกว่า (ใช้แก้ conflict §23 priority stack)
    priority: Mapped[int] = mapped_column(Integer, default=100, nullable=False, index=True)

    # status workflow
    status: Mapped[ScheduleStatus] = mapped_column(
        SAEnum(ScheduleStatus, name="schedule_status", native_enum=False, length=32),
        default=ScheduleStatus.DRAFT,
        nullable=False,
        index=True,
    )

    # audit
    created_by: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("users.id"), nullable=False)
    approved_by: Mapped[uuid.UUID | None] = mapped_column(Uuid, ForeignKey("users.id"), nullable=True)
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )
