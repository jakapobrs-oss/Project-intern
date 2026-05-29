"""
Pydantic schema สำหรับ auth flow
"""
from pydantic import BaseModel, Field


class LoginRequest(BaseModel):
    """ขอ login — รับ username หรือ email ก็ได้"""
    username: str = Field(..., min_length=1, max_length=255, description="username หรือ email")
    password: str = Field(..., min_length=1, max_length=128)


class TokenPair(BaseModel):
    """คู่ access + refresh token"""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int = Field(..., description="access token อายุ (วินาที)")


class RefreshRequest(BaseModel):
    # optional — ถ้าไม่ระบุ จะอ่านจาก httpOnly cookie (Phase 7 cookie mode)
    refresh_token: str | None = None
