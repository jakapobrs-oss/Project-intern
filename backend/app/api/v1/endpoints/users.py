"""
User CRUD endpoints — เฉพาะ SUPER_ADMIN (ดู §21)
"""
import uuid
from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.deps import require_role
from app.core.security import hash_password
from app.db import get_db
from app.models.user import User, Role
from app.schemas.user import UserCreate, UserUpdate, UserOut
from app.services import audit_service


router = APIRouter()


# dependency กลาง — ทุก endpoint ในไฟล์นี้ต้องเป็น super_admin
_admin_only = require_role(Role.SUPER_ADMIN)


@router.get("", response_model=list[UserOut])
async def list_users(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(_admin_only),
):
    """ลิสต์ user ทั้งหมด"""
    res = await db.execute(select(User).order_by(User.created_at.desc()))
    return res.scalars().all()


@router.post("", response_model=UserOut, status_code=status.HTTP_201_CREATED)
async def create_user(
    payload: UserCreate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    actor: User = Depends(_admin_only),
):
    """สร้าง user ใหม่ — username + email ต้อง unique"""
    user = User(
        username=payload.username,
        email=payload.email,
        full_name=payload.full_name,
        role=payload.role,
        is_active=payload.is_active,
        password_hash=hash_password(payload.password),
    )
    db.add(user)
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(status_code=409, detail="username หรือ email ซ้ำ")
    await db.refresh(user)
    await audit_service.log_action(
        db, request, actor, "user.create",
        target_type="user", target_id=user.id,
        message=f"สร้างผู้ใช้ {user.username} สิทธิ์ {user.role.value}",
    )
    return user


@router.get("/{user_id}", response_model=UserOut)
async def get_user(
    user_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(_admin_only),
):
    user = await db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="ไม่พบ user")
    return user


@router.patch("/{user_id}", response_model=UserOut)
async def update_user(
    user_id: uuid.UUID,
    payload: UserUpdate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    actor: User = Depends(_admin_only),
):
    user = await db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="ไม่พบ user")

    data = payload.model_dump(exclude_unset=True)
    # เก็บรายชื่อฟิลด์ไว้ลง audit — ห้ามเก็บค่ารหัสผ่านลง log เด็ดขาด เอาแค่ชื่อฟิลด์
    changed_fields = sorted(data.keys())
    if "password" in data and data["password"]:
        user.password_hash = hash_password(data.pop("password"))
        # password เปลี่ยน → ปลดล็อกทุกชนิด + reset counter
        user.is_locked = False
        user.locked_until = None
        user.failed_login_count = 0
    # admin กดปลดล็อก → ต้องล้างล็อกชั่วคราวด้วย ไม่งั้นปลดแล้วยังเข้าไม่ได้จนกว่าจะครบเวลา
    if data.get("is_locked") is False:
        user.locked_until = None
        user.failed_login_count = 0
    for k, v in data.items():
        setattr(user, k, v)

    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(status_code=409, detail="email ซ้ำกับ user อื่น")
    await db.refresh(user)
    await audit_service.log_action(
        db, request, actor, "user.update",
        target_type="user", target_id=user.id,
        message=f"แก้ไขผู้ใช้ {user.username} ฟิลด์ {', '.join(changed_fields)}",
        extra={"fields": changed_fields},
    )
    return user


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(
    user_id: uuid.UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current: User = Depends(_admin_only),
):
    """ลบ user — ห้ามลบตัวเอง"""
    if current.id == user_id:
        raise HTTPException(status_code=400, detail="ห้ามลบบัญชีของตัวเอง")
    user = await db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="ไม่พบ user")
    # อ่านค่าไว้ก่อนลบ — หลัง delete แล้ว object จะอ่านไม่ได้
    deleted_label = f"{user.username} สิทธิ์ {user.role.value}"
    await db.delete(user)
    await db.commit()
    await audit_service.log_action(
        db, request, current, "user.delete",
        target_type="user", target_id=user_id,
        message=f"ลบผู้ใช้ {deleted_label}",
    )
    return None
