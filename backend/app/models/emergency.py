"""
Emergency Broadcast model — override schedule ปกติเพื่อแจ้งเตือนฉุกเฉิน
ดู Optional features Top-5 §8.5 ใน PLAN.md

Flow:
1. operator/super_admin สร้าง broadcast (text/image/url) + target (all / group / specific devices)
2. backend invalidate manifest ของ device target → next pull ได้ urgent payload
3. มี starts_at / ends_at (NULL = active ทันที / ไม่หมดอายุ)
4. priority สูงกว่าทุก schedule
"""
import enum
import uuid
from datetime import datetime

from sqlalchemy import JSON, Boolean, DateTime, Integer, String, Text, Uuid, func
from sqlalchemy import Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class EmergencyKind(str, enum.Enum):
    TEXT = "text"          # ข้อความล้วน (full-screen)
    IMAGE = "image"        # content_id อ้างถึง image content
    URL = "url"            # iframe / web page (เช่น live stream แจ้งเตือน)


class EmergencyStatus(str, enum.Enum):
    DRAFT = "draft"
    ACTIVE = "active"
    EXPIRED = "expired"
    CANCELLED = "cancelled"


class EmergencyBroadcast(Base):
    """
    Emergency broadcast — override ทุก schedule ปกติชั่วคราว
    priority สูงสุด (ใน manifest จะถูกใส่เป็น top entry)
    """
    __tablename__ = "emergency_broadcasts"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)

    title: Mapped[str] = mapped_column(String(255), nullable=False)
    kind: Mapped[EmergencyKind] = mapped_column(
        SAEnum(EmergencyKind, name="emergency_kind", native_enum=False, length=16),
        nullable=False,
    )

    # payload — แล้วแต่ kind
    # text: { "message": "...", "bg_color": "#c00", "text_color": "#fff", "font_size": 96 }
    # image: { "content_id": "..." }
    # url:   { "url": "https://...", "refresh_sec": 60 }
    payload: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)

    # target — null/empty = all devices
    # { "all": true } หรือ { "device_ids": [...] } หรือ { "group_ids": [...] }
    target: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)

    status: Mapped[EmergencyStatus] = mapped_column(
        SAEnum(EmergencyStatus, name="emergency_status", native_enum=False, length=16),
        nullable=False,
        default=EmergencyStatus.DRAFT,
    )

    # ใช้ตัวเลขสูงเพื่อให้ priority อยู่เหนือ schedule ปกติเสมอ
    priority: Mapped[int] = mapped_column(Integer, nullable=False, default=1000)

    starts_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    ends_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # acknowledgement — ให้ operator confirm ก่อนส่ง (กัน accidental broadcast)
    requires_ack: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    acknowledged_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    created_by: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    def __repr__(self) -> str:
        return f"<Emergency {self.title} [{self.status.value}]>"
