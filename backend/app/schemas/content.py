"""Pydantic schemas — content"""
import uuid
from datetime import datetime
from pydantic import BaseModel, Field, ConfigDict, HttpUrl

from app.models.content import ContentType, ApprovalStatus


class ContentBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: str = ""
    type: ContentType


class ContentCreateUrl(ContentBase):
    """สร้าง content แบบ web/stream — ไม่ upload ไฟล์"""
    url: HttpUrl

    def to_dict(self) -> dict:
        d = self.model_dump()
        d["url"] = str(self.url)
        return d


class ContentUpdate(BaseModel):
    name: str | None = Field(None, max_length=255)
    description: str | None = None
    expires_at: datetime | None = None
    is_active: bool | None = None


class ContentOut(ContentBase):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    storage_key: str | None
    mime_type: str | None
    file_size: int | None
    sha256: str | None
    width: int | None
    height: int | None
    duration_sec: float | None
    thumbnail_key: str | None
    url: str | None
    approval_status: ApprovalStatus
    approved_by: uuid.UUID | None
    approved_at: datetime | None
    rejection_reason: str | None
    expires_at: datetime | None
    created_by: uuid.UUID
    is_active: bool
    created_at: datetime
    updated_at: datetime


class ContentUploadOut(ContentOut):
    """
    ผลของการอัปโหลดไฟล์ — เหมือน ContentOut แต่มีธงบอกว่าไฟล์ซ้ำของเดิมหรือเปล่า

    deduplicated=True แปลว่าระบบเจอไฟล์เนื้อเดียวกัน (SHA-256 ตรงกัน) อยู่แล้ว จึงคืน
    รายการเดิมกลับไปแทนการสร้างใหม่ — หน้าจอต้องบอกผู้ใช้ว่าชื่อที่เพิ่งตั้งไม่ถูกใช้
    """
    deduplicated: bool = False


class ApprovalAction(BaseModel):
    """approve/reject content"""
    approve: bool = True
    rejection_reason: str | None = None
