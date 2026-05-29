"""
Presentation model — layout/template + content ที่ใส่ในแต่ละช่อง
ดู PLAN §35.1 — เป็นชั้นที่ "ของเดิมมี แต่ PLAN เดิมขาด"

1 Presentation = 1 หน้าจอที่ถูก compose ไว้ (เช่น แบ่ง 70/30 + ticker + clock)
"""
import uuid
from datetime import datetime
from sqlalchemy import String, DateTime, Integer, Text, ForeignKey, JSON, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base


class Presentation(Base):
    """Layout + composition ของ content"""
    __tablename__ = "presentations"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    description: Mapped[str] = mapped_column(Text, default="", nullable=False)

    # layout_json — schema คร่าวๆ:
    # { "template": "split_70_30", "zones": [{"key": "main", "x": 0, "y": 0, "w": 70, "h": 100}, ...] }
    layout_json: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)

    # default duration ถ้า plan_item ไม่ override
    duration_sec: Mapped[int] = mapped_column(Integer, default=30, nullable=False)

    created_by: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("users.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    zones: Mapped[list["PresentationZone"]] = relationship(
        back_populates="presentation",
        cascade="all, delete-orphan",
        lazy="selectin",
    )


class PresentationZone(Base):
    """1 zone = 1 ช่องใน layout → ผูกกับ content"""
    __tablename__ = "presentation_zones"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    presentation_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("presentations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    zone_key: Mapped[str] = mapped_column(String(64), nullable=False)  # match กับ layout_json
    content_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("contents.id"), nullable=False)

    # params เฉพาะ zone เช่น volume, mute, fit_mode
    params_json: Mapped[dict] = mapped_column(JSON, default=dict, nullable=False)
    order_index: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    presentation: Mapped[Presentation] = relationship(back_populates="zones")
