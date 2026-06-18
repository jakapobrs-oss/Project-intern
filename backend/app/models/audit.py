"""
AuditLog model — บันทึก action สำคัญทั้งหมดใน system (§Tier-1 §26 §31 PDPA)

แนวคิด:
- write-only / append-only (ไม่ลบ ไม่แก้)
- เก็บ actor (user หรือ device), action (verb), target (entity:id), metadata JSON
- ใช้กับ login attempt, content approve/reject, schedule activate, device pair,
  emergency broadcast, RBAC denied, ฯลฯ
- retention policy ค่อยลบทีเดียวต่อปี (Phase 7)
"""
import enum
import uuid
from datetime import datetime

from sqlalchemy import JSON, DateTime, String, Text, Uuid, func
from sqlalchemy import Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class AuditOutcome(str, enum.Enum):
    """ผลของ action — success / fail / denied"""
    SUCCESS = "success"
    FAIL = "fail"
    DENIED = "denied"


class AuditLog(Base):
    """
    Append-only audit log สำหรับ compliance + forensic
    ห้าม update/delete row เด็ดขาด (จัด trigger หรือ RBAC ใน DB ภายหลัง)
    """
    __tablename__ = "audit_logs"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)

    # ใครทำ — เก็บเป็น string (เพราะอาจเป็น user_id, device_id, "system", "anonymous")
    actor_type: Mapped[str] = mapped_column(String(32), nullable=False, default="user")
    actor_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)
    actor_label: Mapped[str | None] = mapped_column(String(255), nullable=True)  # username/device_name snapshot

    # ทำอะไร — verb เช่น "auth.login", "content.approve", "schedule.activate"
    action: Mapped[str] = mapped_column(String(64), nullable=False, index=True)

    # ทำกับอะไร — entity:id เช่น "device:abc-123", "content:xyz"
    target_type: Mapped[str | None] = mapped_column(String(32), nullable=True)
    target_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)

    outcome: Mapped[AuditOutcome] = mapped_column(
        SAEnum(AuditOutcome, name="audit_outcome", native_enum=False, length=16),
        nullable=False,
        default=AuditOutcome.SUCCESS,
    )

    # context เพิ่ม
    ip_address: Mapped[str | None] = mapped_column(String(45), nullable=True)  # IPv6 max 45
    user_agent: Mapped[str | None] = mapped_column(String(512), nullable=True)
    message: Mapped[str | None] = mapped_column(Text, nullable=True)  # human-readable
    extra: Mapped[dict | None] = mapped_column(JSON, nullable=True)   # structured metadata

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False, index=True
    )

    def __repr__(self) -> str:
        return f"<AuditLog {self.action} by {self.actor_label or self.actor_id} → {self.outcome.value}>"
