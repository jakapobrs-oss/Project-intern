"""
FastAPI dependencies — auth + RBAC

Auth modes (Phase 7 — dual support):
  1. Bearer header — `Authorization: Bearer <jwt>` — สำหรับ player + backward compat
  2. httpOnly cookie — `access_token=<jwt>`         — สำหรับ admin UI (production)

ทั้ง 2 อ่านได้ทั้งคู่ — รูปแบบไหนมาก่อนใช้ตัวนั้น
"""
import uuid
from collections.abc import Iterable

from fastapi import Cookie, Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import TokenType, decode_token
from app.db import get_db
from app.models.user import Role, User

# OAuth2 scheme — เผยใน /api/docs ให้กด Authorize ทดสอบ login ได้
# auto_error=False เพราะเราจะ fallback ไปอ่าน cookie ถ้า header ไม่มา
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login", auto_error=False)


# ชื่อ cookie ต้อง sync กับ endpoint /auth/login (ที่ set cookie)
ACCESS_COOKIE_NAME = "signage_access_token"
REFRESH_COOKIE_NAME = "signage_refresh_token"


def _extract_token(
    header_token: str | None,
    cookie_token: str | None,
) -> str | None:
    """ลอง header ก่อน → fallback cookie"""
    return header_token or cookie_token


async def get_current_user(
    request: Request,
    header_token: str | None = Depends(oauth2_scheme),
    cookie_token: str | None = Cookie(default=None, alias=ACCESS_COOKIE_NAME),
    db: AsyncSession = Depends(get_db),
) -> User:
    """
    ดึง user จาก JWT access token + ตรวจสถานะ
    รองรับทั้ง Bearer header (player/Swagger) และ httpOnly cookie (admin UI)
    """
    token = _extract_token(header_token, cookie_token)
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="ต้องระบุ Authorization header หรือ access cookie",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        payload = decode_token(token)
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="token ไม่ถูกต้องหรือหมดอายุ",
            headers={"WWW-Authenticate": "Bearer"},
        ) from None

    if payload.get("type") != TokenType.ACCESS:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="ต้องใช้ access token (ไม่ใช่ refresh)",
        )

    user_id_str = payload.get("sub")
    user = None
    if user_id_str:
        try:
            # JWT sub เป็น string — แปลงเป็น UUID object ก่อนค่อยส่งให้ db.get
            # (SQLAlchemy Uuid type ต้องการ UUID, ไม่ใช่ str — bug บน SQLite)
            user = await db.get(User, uuid.UUID(user_id_str))
        except (ValueError, TypeError):
            user = None
    if user is None:
        raise HTTPException(status_code=401, detail="user ไม่พบ")
    if not user.is_active:
        raise HTTPException(status_code=403, detail="บัญชีถูกปิดใช้งาน")
    if user.is_locked:
        raise HTTPException(status_code=403, detail="บัญชีถูกล็อก")

    return user


def require_role(*allowed: Role):
    """
    Factory → dependency ที่จะอนุญาตเฉพาะ role ที่ระบุ
    ใช้: Depends(require_role(Role.ADMIN, Role.SUPER_ADMIN))
    """
    allowed_set = set(allowed)

    async def _checker(user: User = Depends(get_current_user)) -> User:
        if user.role not in allowed_set:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"role '{user.role.value}' ไม่มีสิทธิ์ (ต้องเป็น {[r.value for r in allowed_set]})",
            )
        return user

    return _checker


def require_any_role(roles: Iterable[Role]):
    """alias ใช้ list มาแทน"""
    return require_role(*roles)
