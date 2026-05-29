"""
Plan model (= "Playlist" ในคำเดิม) — ลำดับของ Presentation
ดู §35.1
"""
import uuid
from datetime import datetime
from sqlalchemy import String, DateTime, Integer, Text, ForeignKey, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base


class Plan(Base):
    """1 Plan = sequence ของ presentation พร้อมระยะเวลา"""
    __tablename__ = "plans"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(255), nullable=False, unique=True, index=True)
    description: Mapped[str] = mapped_column(Text, default="", nullable=False)

    created_by: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("users.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    items: Mapped[list["PlanItem"]] = relationship(
        back_populates="plan",
        cascade="all, delete-orphan",
        order_by="PlanItem.order_index",
        lazy="selectin",
    )


class PlanItem(Base):
    """1 item ใน plan — ผูก presentation + override duration"""
    __tablename__ = "plan_items"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    plan_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("plans.id", ondelete="CASCADE"), nullable=False, index=True
    )
    presentation_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("presentations.id"), nullable=False)
    order_index: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    # ถ้า null ใช้ duration_sec ของ presentation
    duration_sec_override: Mapped[int | None] = mapped_column(Integer, nullable=True)

    plan: Mapped[Plan] = relationship(back_populates="items")
