"""
Security primitives: bcrypt password hashing + JWT encode/decode
ใช้ python-jose + passlib (สอดคล้อง §26)
"""
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

from jose import JWTError, jwt
from passlib.context import CryptContext

from app.config import settings

# bcrypt rounds=12 — default ของ passlib (~250ms per hash บน server ปกติ)
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


# ===== Password =====

def hash_password(plain: str) -> str:
    """แฮช password ด้วย bcrypt"""
    return pwd_context.hash(plain)


def verify_password(plain: str, hashed: str) -> bool:
    """ตรวจ password ปลอดภัย (constant-time compare ภายใน passlib)"""
    return pwd_context.verify(plain, hashed)


# ===== JWT =====

class TokenType:
    ACCESS = "access"
    REFRESH = "refresh"


def _create_token(
    subject: str | uuid.UUID,
    token_type: str,
    expires_delta: timedelta,
    extra_claims: dict[str, Any] | None = None,
) -> str:
    """สร้าง JWT ทั่วไป — ใช้ภายในไฟล์นี้เท่านั้น"""
    now = datetime.now(UTC)
    payload: dict[str, Any] = {
        "sub": str(subject),
        "type": token_type,
        "iat": int(now.timestamp()),
        "exp": int((now + expires_delta).timestamp()),
        "jti": uuid.uuid4().hex,  # สำหรับ token revocation ในอนาคต
    }
    if extra_claims:
        payload.update(extra_claims)
    return jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)


def create_access_token(subject: str | uuid.UUID, role: str) -> str:
    """JWT access token (อายุสั้น 30 นาที default)"""
    return _create_token(
        subject,
        TokenType.ACCESS,
        timedelta(minutes=settings.jwt_access_expire_minutes),
        extra_claims={"role": role},
    )


def create_refresh_token(subject: str | uuid.UUID) -> str:
    """JWT refresh token (อายุยาว 7 วัน default) — rotate ทุกครั้งที่ใช้"""
    return _create_token(
        subject,
        TokenType.REFRESH,
        timedelta(days=settings.jwt_refresh_expire_days),
    )


def decode_token(token: str) -> dict[str, Any]:
    """
    decode + verify signature + verify expiry
    raise JWTError ถ้าไม่ผ่าน (caller จัดการแปลงเป็น HTTPException)
    """
    return jwt.decode(token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])


__all__ = [
    "hash_password",
    "verify_password",
    "create_access_token",
    "create_refresh_token",
    "decode_token",
    "TokenType",
    "JWTError",
]
