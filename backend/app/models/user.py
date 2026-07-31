"""
User model + RoleEnum (RBAC 7 roles ตาม PLAN.md §21)
"""
import enum
import uuid
from datetime import datetime
from sqlalchemy import String, Boolean, DateTime, Enum as SAEnum, Integer, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class Role(str, enum.Enum):
    """RBAC role — ดู §21 ใน PLAN.md"""
    SUPER_ADMIN = "super_admin"  # manage user + ทุกอย่าง
    ADMIN = "admin"              # ทุกอย่างยกเว้น user mgmt
    EDITOR = "editor"            # upload content, สร้าง playlist/schedule (รอ approve)
    APPROVER = "approver"        # approve/reject content + schedule
    VIEWER = "viewer"            # ดูอย่างเดียว + export report
    OPERATOR = "operator"        # emergency broadcast + restart player
    DEVICE = "device"            # player token เฉพาะ — เรียก player API


class User(Base):
    """ผู้ใช้ระบบ admin (ไม่รวม player device)"""
    __tablename__ = "users"

    # ใช้ sa.Uuid (dialect-agnostic) — PG ใช้ UUID, SQLite ใช้ CHAR(32)
    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)

    # ข้อมูล login
    username: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)

    # ข้อมูลโปรไฟล์
    full_name: Mapped[str] = mapped_column(String(255), nullable=False, default="")
    role: Mapped[Role] = mapped_column(
        SAEnum(Role, name="user_role", native_enum=False, length=32),
        nullable=False,
        default=Role.VIEWER,
    )

    # สถานะ
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    # is_locked = admin สั่งล็อกด้วยมือ → บล็อกทุกอย่างจนกว่าคนจะมาปลด (รวม session ที่ล็อกอินค้างอยู่)
    is_locked: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)  # §26 account lockout
    failed_login_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    # locked_until = ระบบล็อกชั่วคราวเองเพราะกรอกรหัสผิดเกินกำหนด → ปลดเองเมื่อถึงเวลา
    # แยกจาก is_locked โดยตั้งใจ: ล็อกชั่วคราวบล็อกเฉพาะ "การล็อกอินใหม่" ไม่ตัด session ที่ทำงานอยู่
    # (ไม่งั้นคนร้ายกรอกรหัสผิดใส่ชื่อเราไม่กี่ครั้ง ก็เตะเราออกจากระบบกลางคันได้)
    locked_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    def __repr__(self) -> str:
        return f"<User {self.username} ({self.role.value})>"
