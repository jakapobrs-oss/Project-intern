"""
Auth service — business logic ของ login / refresh / account lockout
แยกออกจาก endpoint เพื่อ test ง่าย + reuse ได้
"""
import math
import uuid
from datetime import datetime, timedelta, timezone
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.core.security import (
    hash_password,
    verify_password,
    create_access_token,
    create_refresh_token,
    decode_token,
    TokenType,
    JWTError,
)
from app.models.user import User


# §26: กรอกรหัสผิดครบ N ครั้ง → ล็อก "ชั่วคราว" แล้วปลดเองเมื่อครบเวลา (ปรับได้ที่ config)
# ห้ามกลับไปล็อกถาวร: ล็อกถาวรทำให้ใครก็ตามที่รู้แค่ชื่อผู้ใช้ ปิดบัญชีคนอื่นได้ตลอดกาล
# และ super_admin บัญชีเดียวที่ล็อกตัวเองจะไม่มีใครปลดให้ (ดู alembic 0006)
MAX_FAILED_LOGIN = settings.max_failed_login  # เก็บชื่อเดิมไว้ให้โค้ด/เทสเก่าที่ import ยังใช้ได้


class AuthError(Exception):
    """ใช้แทน HTTPException ที่ service layer — endpoint ค่อยแปลง"""
    def __init__(self, code: str, message: str):
        self.code = code
        self.message = message
        super().__init__(message)


def _as_utc(dt: datetime | None) -> datetime | None:
    """
    ทำให้ datetime มีโซนเวลาเสมอก่อนนำไปเทียบ

    SQLite (ที่ pytest ใช้) ไม่เก็บโซนเวลา — อ่านกลับมาได้ datetime แบบไม่มี tzinfo
    ถ้าเอาไปเทียบกับเวลาที่มี tzinfo ตรง ๆ Python จะโยน TypeError
    ค่าที่เราเขียนลงไปเป็น UTC เสมอ จึงเติม UTC ให้ตัวที่ไม่มีได้อย่างปลอดภัย
    """
    if dt is None:
        return None
    return dt if dt.tzinfo is not None else dt.replace(tzinfo=timezone.utc)


def lockout_seconds_left(user: User, now: datetime | None = None) -> int:
    """เหลือกี่วินาทีกว่าจะปลดล็อกชั่วคราว — 0 = ไม่ได้ถูกล็อก/หมดเวลาแล้ว"""
    until = _as_utc(user.locked_until)
    if until is None:
        return 0
    now = now or datetime.now(timezone.utc)
    return max(0, math.ceil((until - now).total_seconds()))


def _lockout_message(seconds_left: int) -> str:
    minutes_left = max(1, math.ceil(seconds_left / 60))
    return f"กรอกรหัสผ่านผิดเกินกำหนด บัญชีถูกล็อกชั่วคราว ลองใหม่ในอีก {minutes_left} นาที"


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
    นับครั้งที่ผิด และล็อกบัญชี "ชั่วคราว" เมื่อผิดครบกำหนด
    """
    user = await _find_user(db, username)
    if user is None:
        # ไม่บอก client ว่า user ไม่มี (ป้องกัน enumeration)
        raise AuthError("INVALID_CREDENTIALS", "username หรือ password ไม่ถูกต้อง")

    if not user.is_active:
        raise AuthError("ACCOUNT_DISABLED", "บัญชีถูกปิดใช้งาน")

    # ล็อกด้วยมือโดย admin — ต้องให้คนมาปลดเท่านั้น
    if user.is_locked:
        raise AuthError("ACCOUNT_LOCKED", "บัญชีถูกล็อกโดยผู้ดูแลระบบ ติดต่อ admin")

    # ล็อกชั่วคราวจากการเดารหัส — ยังไม่ถึงเวลาปลด
    seconds_left = lockout_seconds_left(user)
    if seconds_left > 0:
        raise AuthError("ACCOUNT_LOCKED_TEMP", _lockout_message(seconds_left))

    # ถึงเวลาปลดแล้ว → ล้างสถานะทิ้ง เริ่มนับใหม่ (ค่าจะถูก commit ไปกับผลลัพธ์ด้านล่าง)
    if user.locked_until is not None:
        user.locked_until = None
        user.failed_login_count = 0

    if not verify_password(password, user.password_hash):
        user.failed_login_count += 1
        if user.failed_login_count >= settings.max_failed_login:
            # ล็อกชั่วคราว + รีเซ็ตตัวนับ เพื่อให้รอบถัดไปหลังปลดเริ่มนับจากศูนย์
            user.locked_until = datetime.now(timezone.utc) + timedelta(
                minutes=settings.lockout_minutes
            )
            user.failed_login_count = 0
            await db.commit()
            raise AuthError(
                "ACCOUNT_LOCKED_TEMP",
                _lockout_message(settings.lockout_minutes * 60),
            )
        await db.commit()
        raise AuthError("INVALID_CREDENTIALS", "username หรือ password ไม่ถูกต้อง")

    # success → reset counter + ล้างล็อกชั่วคราว + บันทึก last_login
    user.failed_login_count = 0
    user.locked_until = None
    user.last_login_at = datetime.now(timezone.utc)
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

    # JWT sub เป็น string — แปลงเป็น UUID ก่อน query (SQLAlchemy Uuid type ต้องการ UUID object)
    # ให้สอดคล้องกับ get_current_user (deps.py) ที่แปลงเหมือนกัน
    try:
        user_pk = uuid.UUID(str(user_id))
    except (ValueError, TypeError) as e:
        raise AuthError("INVALID_TOKEN", "refresh token subject ไม่ถูกต้อง") from e

    # เช็คแค่ is_locked (ล็อกโดย admin) — ไม่เช็ค locked_until โดยตั้งใจ
    # ล็อกชั่วคราวเกิดจากคน "อื่น" เดารหัสเราผิดก็ได้ ถ้าให้มันตัด session ที่ใช้งานอยู่
    # ใครก็เตะเราออกจากระบบกลางคันได้ด้วยการกรอกรหัสผิดใส่ชื่อเราไม่กี่ครั้ง
    user = await db.get(User, user_pk)
    if user is None or not user.is_active or user.is_locked:
        raise AuthError("INVALID_TOKEN", "user ไม่พร้อมใช้งาน")

    access, new_refresh = issue_token_pair(user)
    return user, access, new_refresh
