"""
Auth service — business logic ของ login / refresh / account lockout
แยกออกจาก endpoint เพื่อ test ง่าย + reuse ได้
"""
from datetime import UTC, datetime

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import (
    JWTError,
    TokenType,
    create_access_token,
    create_refresh_token,
    decode_token,
    verify_password,
)
from app.models.user import User

# §26: lockout หลัง fail 5 ครั้ง (ปลดเอง = admin reset หรือรอ unlock policy ใน Phase ถัดไป)
MAX_FAILED_LOGIN = 5


class AuthError(Exception):
    """ใช้แทน HTTPException ที่ service layer — endpoint ค่อยแปลง"""
    def __init__(self, code: str, message: str):
        self.code = code
        self.message = message
        super().__init__(message)


async def _find_user(db: AsyncSession, username_or_email: str) -> User | None:
    """หา user ด้วย username หรือ email"""
    stmt = select(User).where(
        or_(User.username == username_or_email, User.email == username_or_email)
    )
    res = await db.execute(stmt)
    return res.scalar_one_or_none()


async def authenticate(db: AsyncSession, username: str, password: str) -> User:
    """
    ตรวจสอบ credential — ถ้าผ่านคืน User, ถ้าไม่ผ่าน raise AuthError
    เพิ่ม failed_login_count + lock account เมื่อเกิน
    """
    user = await _find_user(db, username)
    if user is None:
        # ไม่บอก client ว่า user ไม่มี (ป้องกัน enumeration)
        raise AuthError("INVALID_CREDENTIALS", "username หรือ password ไม่ถูกต้อง")

    if not user.is_active:
        raise AuthError("ACCOUNT_DISABLED", "บัญชีถูกปิดใช้งาน")

    if user.is_locked:
        raise AuthError("ACCOUNT_LOCKED", "บัญชีถูกล็อกจากการ login ผิดเกินกำหนด ติดต่อ admin")

    if not verify_password(password, user.password_hash):
        user.failed_login_count += 1
        if user.failed_login_count >= MAX_FAILED_LOGIN:
            user.is_locked = True
        await db.commit()
        raise AuthError("INVALID_CREDENTIALS", "username หรือ password ไม่ถูกต้อง")

    # success → reset counter + บันทึก last_login
    user.failed_login_count = 0
    user.last_login_at = datetime.now(UTC)
    await db.commit()
    await db.refresh(user)
    return user


def issue_token_pair(user: User) -> tuple[str, str]:
    """ออก access + refresh token"""
    access = create_access_token(subject=user.id, role=user.role.value)
    refresh = create_refresh_token(subject=user.id)
    return access, refresh


async def refresh_tokens(db: AsyncSession, refresh_token: str) -> tuple[User, str, str]:
    """
    Rotate refresh token (§26: refresh token rotation)
    คืน (user, new_access, new_refresh)
    """
    try:
        payload = decode_token(refresh_token)
    except JWTError as e:
        raise AuthError("INVALID_TOKEN", f"refresh token ไม่ถูกต้อง: {e}") from e

    if payload.get("type") != TokenType.REFRESH:
        raise AuthError("INVALID_TOKEN", "token ไม่ใช่ refresh token")

    user_id = payload.get("sub")
    if not user_id:
        raise AuthError("INVALID_TOKEN", "refresh token ไม่มี subject")

    user = await db.get(User, user_id)
    if user is None or not user.is_active or user.is_locked:
        raise AuthError("INVALID_TOKEN", "user ไม่พร้อมใช้งาน")

    access, new_refresh = issue_token_pair(user)
    return user, access, new_refresh
