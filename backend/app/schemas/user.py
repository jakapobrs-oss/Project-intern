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
    # ต้องประกาศไว้ ไม่งั้น Pydantic ทิ้งฟิลด์นี้เงียบ ๆ แล้วปุ่มล็อก/ปลดล็อกในหน้า users
    # จะตอบ 200 โดยไม่มีอะไรเปลี่ยน (บั๊กเดิม: ปลดล็อกได้ทางเดียวคือแก้ DB ตรง ๆ)
    is_locked: bool | None = None
    password: str | None = Field(None, min_length=8, max_length=128)


class UserOut(UserBase):
    """response — ไม่มี password"""
    model_config = ConfigDict(from_attributes=True)

    # ทับ EmailStr ของ UserBase ด้วย str โดยตั้งใจ
    # ตรวจรูปแบบอีเมลตอน "รับเข้า" (UserCreate/UserUpdate) พอแล้ว — ถ้ามาตรวจซ้ำตอน
    # "ส่งออก" ข้อมูลที่อยู่ในฐานอยู่แล้วเพียงแถวเดียวผิดรูป จะทำให้ทั้ง endpoint
    # ตอบ 500 หน้าจัดการผู้ใช้งานเปิดไม่ได้เลย (เจอจริง: seed_demo.py สร้างผู้ใช้
    # อีเมล @demo.local ซึ่ง email-validator ถือเป็นโดเมนสงวน → ทั้งหน้าพัง)
    email: str
    id: uuid.UUID
    is_locked: bool
    # ว่าง = ไม่ได้ถูกล็อกชั่วคราว; มีค่า = ระบบล็อกจากการกรอกรหัสผิด จนถึงเวลานี้
    locked_until: datetime | None = None
    created_at: datetime
    updated_at: datetime
    last_login_at: datetime | None = None
