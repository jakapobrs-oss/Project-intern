"""
Content model — สื่อ raw (image, video, web, stream)
ดู PLAN §22 (Content Pipeline)
"""
import enum
import uuid
from datetime import datetime

from sqlalchemy import BigInteger, Boolean, DateTime, ForeignKey, Integer, String, Text, Uuid, func
from sqlalchemy import Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class ContentType(str, enum.Enum):
    IMAGE = "image"
    VIDEO = "video"
    WEB = "web"          # iframe URL (whitelist)
    STREAM = "stream"    # RTSP/HLS/RTMP
    TEXT = "text"        # simple HTML sanitized


class ApprovalStatus(str, enum.Enum):
    DRAFT = "draft"           # editor บันทึก
    PENDING = "pending"       # ส่งให้ approver
    APPROVED = "approved"
    REJECTED = "rejected"


class Content(Base):
    """1 record = 1 ไฟล์/URL สื่อ"""
    __tablename__ = "contents"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    description: Mapped[str] = mapped_column(Text, default="", nullable=False)

    type: Mapped[ContentType] = mapped_column(
        SAEnum(ContentType, name="content_type", native_enum=False, length=16),
        nullable=False,
    )

    # ===== ข้อมูลไฟล์ (กรณี image/video) =====
    storage_key: Mapped[str | None] = mapped_column(String(512), nullable=True)  # path บน S3/MinIO
    mime_type: Mapped[str | None] = mapped_column(String(128), nullable=True)
    file_size: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    sha256: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)  # ใช้ dedupe §22
    width: Mapped[int | None] = mapped_column(Integer, nullable=True)
    height: Mapped[int | None] = mapped_column(Integer, nullable=True)
    duration_sec: Mapped[float | None] = mapped_column(nullable=True)  # video เท่านั้น
    thumbnail_key: Mapped[str | None] = mapped_column(String(512), nullable=True)

    # ===== ข้อมูล URL (กรณี web/stream) =====
    url: Mapped[str | None] = mapped_column(String(2048), nullable=True)

    # ===== Approval workflow §22 / §21 =====
    approval_status: Mapped[ApprovalStatus] = mapped_column(
        SAEnum(ApprovalStatus, name="approval_status", native_enum=False, length=16),
        default=ApprovalStatus.DRAFT,
        nullable=False,
    )
    approved_by: Mapped[uuid.UUID | None] = mapped_column(Uuid, ForeignKey("users.id"), nullable=True)
    approved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    rejection_reason: Mapped[str | None] = mapped_column(Text, nullable=True)

    # ===== Lifecycle =====
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)  # auto-archive

    # ===== Audit =====
    created_by: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("users.id"), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )
