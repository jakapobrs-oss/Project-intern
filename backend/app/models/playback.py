"""
PlaybackLog model (§28 reporting) — บันทึกว่า content ไหนถูกเล่นที่ device ไหน เมื่อไหร่
player POST batch มาเป็นระยะ → ใช้ทำ report play-count + schedule compliance

append-only (write-once) — ไม่มี update/delete จาก business logic
retention: raw 90 วัน (cron purge — §28), aggregate เก็บยาว
"""
import uuid
from datetime import datetime

from sqlalchemy import String, DateTime, ForeignKey, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class PlaybackLog(Base):
    __tablename__ = "playback_logs"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    device_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("devices.id", ondelete="CASCADE"), nullable=False, index=True)
    content_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, ForeignKey("contents.id", ondelete="SET NULL"), nullable=True, index=True)
    presentation_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, nullable=True)
    # เวลาที่ "เริ่มเล่น" จริงบน player (player ส่งมา — อาจต่างจากเวลา server รับ)
    played_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    duration_sec: Mapped[float | None] = mapped_column(nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
