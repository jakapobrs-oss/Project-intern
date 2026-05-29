"""
Pydantic schema สำหรับ User
แยก Create / Update / Out เพื่อไม่ให้ password hash หลุดออกไปกับ response
"""
import uuid
from datetime import datetime
from pydantic import BaseModel, EmailStr, Field, ConfigDict

from app.models.user import Role


class UserBase(BaseModel):
    username: str = Field(..., min_length=3, max_length=64, pattern=r"^[a-zA-Z0-9_.-]+$")
    email: EmailStr
    full_name: str = Field("", max_length=255)
    role: Role = Role.VIEWER
    is_active: bool = True


class UserCreate(UserBase):
    """สร้าง user ใหม่ — ต้องมี password"""
    password: str = Field(..., min_length=8, max_length=128, description="ขั้นต่ำ 8 ตัวอักษร")


class UserUpdate(BaseModel):
    """แก้ user — ทุกฟิลด์ optional"""
    email: EmailStr | None = None
    full_name: str | None = Field(None, max_length=255)
    role: Role | None = None
    is_active: bool | None = None
    password: str | None = Field(None, min_length=8, max_length=128)


class UserOut(UserBase):
    """response — ไม่มี password"""
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    is_locked: bool
    created_at: datetime
    updated_at: datetime
    last_login_at: datetime | None = None
