"""
Auth endpoints — login / refresh / me / logout / csrf

Phase 7 — dual auth:
  - Bearer: JWT in JSON response → frontend stores ใน localStorage (default + backward compat)
  - Cookie: JWT in httpOnly cookie → frontend ส่ง `credentials: include` (production hardening)

ทั้ง 2 mode รันพร้อมกันได้ — backend ทำทั้งคู่ลูกค้าเลือกใช้แบบไหน
"""
import secrets

from fastapi import APIRouter, Cookie, Depends, HTTPException, Request, Response, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.deps import (
    ACCESS_COOKIE_NAME,
    REFRESH_COOKIE_NAME,
    get_current_user,
)
from app.config import settings
from app.db import get_db
from app.models.audit import AuditOutcome
from app.models.user import User
from app.schemas.auth import TokenPair, RefreshRequest
from app.schemas.user import UserOut
from app.services import auth_service, audit_service
from app.services.auth_service import AuthError


router = APIRouter()


# ===== Cookie helpers (Phase 7) =====

def _is_production() -> bool:
    return settings.app_env != "development"


def _set_auth_cookies(response: Response, access: str, refresh: str) -> None:
    """
    Set httpOnly cookies — access + refresh
    samesite=lax: ส่ง cookie กับ same-site navigation (รวมถึง form submit)
                  strict ก็ได้แต่ลด UX เวลา redirect จาก email link
    secure: True ใน production (HTTPS only) — dev = False เพราะ localhost HTTP
    """
    common = {
        "httponly": True,
        "samesite": "lax",
        "secure": _is_production(),
        "path": "/",
    }
    response.set_cookie(
        ACCESS_COOKIE_NAME,
        access,
        max_age=settings.jwt_access_expire_minutes * 60,
        **common,
    )
    response.set_cookie(
        REFRESH_COOKIE_NAME,
        refresh,
        max_age=settings.jwt_refresh_expire_days * 86400,
        **common,
    )


def _clear_auth_cookies(response: Response) -> None:
    """Clear ทั้ง access + refresh — ใช้ตอน logout"""
    common = {
        "httponly": True,
        "samesite": "lax",
        "secure": _is_production(),
        "path": "/",
    }
    response.delete_cookie(ACCESS_COOKIE_NAME, **common)
    response.delete_cookie(REFRESH_COOKIE_NAME, **common)


# ===== Error mapping =====

def _auth_error_to_http(e: AuthError) -> HTTPException:
    """แปลง AuthError → HTTPException ตาม code"""
    code_to_status = {
        "INVALID_CREDENTIALS": status.HTTP_401_UNAUTHORIZED,
        "ACCOUNT_DISABLED": status.HTTP_403_FORBIDDEN,
        "ACCOUNT_LOCKED": status.HTTP_403_FORBIDDEN,
        "INVALID_TOKEN": status.HTTP_401_UNAUTHORIZED,
    }
    return HTTPException(
        status_code=code_to_status.get(e.code, status.HTTP_400_BAD_REQUEST),
        detail={"code": e.code, "message": e.message},
    )


# ===== Endpoints =====

@router.post("/login", response_model=TokenPair)
async def login(
    request: Request,
    response: Response,
    form: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_db),
):
    """
    Login ด้วย username/email + password

    คืน TokenPair (JSON) + set httpOnly cookies:
      - frontend Bearer mode → ใช้ค่าใน JSON response
      - frontend cookie mode → cookie ถูก set แล้ว ใช้ได้เลย (credentials: include)
    """
    ctx = audit_service.extract_request_context(request)
    try:
        user = await auth_service.authenticate(db, form.username, form.password)
    except AuthError as e:
        await audit_service.log_event(
            db,
            action="auth.login",
            actor_type="user",
            actor_label=form.username,
            outcome=AuditOutcome.FAIL,
            message=e.code,
            **ctx,
        )
        raise _auth_error_to_http(e)

    access, refresh = auth_service.issue_token_pair(user)
    await audit_service.log_event(
        db,
        action="auth.login",
        actor_type="user",
        actor_id=str(user.id),
        actor_label=user.username,
        outcome=AuditOutcome.SUCCESS,
        **ctx,
    )

    # set httpOnly cookies (Phase 7 — production cookie mode)
    _set_auth_cookies(response, access, refresh)

    return TokenPair(
        access_token=access,
        refresh_token=refresh,
        expires_in=settings.jwt_access_expire_minutes * 60,
    )


@router.post("/refresh", response_model=TokenPair)
async def refresh(
    response: Response,
    body: RefreshRequest | None = None,
    cookie_refresh: str | None = Cookie(default=None, alias=REFRESH_COOKIE_NAME),
    db: AsyncSession = Depends(get_db),
):
    """
    Rotate refresh token — ออก access + refresh ใหม่ (§26)

    อ่าน refresh token จาก:
      1. JSON body (Bearer mode)
      2. Cookie (cookie mode) — ถ้า body ไม่มา
    """
    # Bearer mode: body ต้องมา + มี refresh_token
    # Cookie mode: body=None → fallback อ่านจาก cookie
    refresh_token = None
    if body is not None and body.refresh_token:
        refresh_token = body.refresh_token
    elif cookie_refresh:
        refresh_token = cookie_refresh

    if not refresh_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="ต้องระบุ refresh_token (JSON หรือ cookie)",
        )

    try:
        _, access, new_refresh = await auth_service.refresh_tokens(db, refresh_token)
    except AuthError as e:
        raise _auth_error_to_http(e)

    # rotate cookies ด้วย (cookie mode)
    _set_auth_cookies(response, access, new_refresh)

    return TokenPair(
        access_token=access,
        refresh_token=new_refresh,
        expires_in=settings.jwt_access_expire_minutes * 60,
    )


@router.get("/me", response_model=UserOut)
async def me(user: User = Depends(get_current_user)):
    """ดึงข้อมูล user ปัจจุบันจาก token (header หรือ cookie)"""
    return user


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(
    response: Response,
    _: User = Depends(get_current_user),
):
    """
    Logout — clear httpOnly cookies
    Bearer mode: client ต้องลบ token ฝั่งตัวเองอยู่ดี (stateless JWT)
    Cookie mode: backend ลบ cookie ที่ set ไว้ผ่าน Set-Cookie expire=0
    Phase ถัดไปจะเพิ่ม jti blacklist ใน Redis
    """
    _clear_auth_cookies(response)
    return None


@router.get("/csrf")
async def get_csrf_token(
    response: Response,
    csrf_cookie: str | None = Cookie(default=None, alias="csrf_token"),
):
    """
    ออก CSRF token + set cookie (สำหรับ frontend cookie mode)

    Flow:
      1. Frontend เรียก GET /auth/csrf หลัง login
      2. Response มี cookie `csrf_token` + JSON body `{"csrf_token": "..."}`
      3. Frontend ใส่ค่า X-CSRF-Token header ในทุก mutation request
      4. CsrfMiddleware เปรียบเทียบ cookie กับ header → match ผ่าน

    หมายเหตุ: ถ้า CsrfMiddleware ปิดอยู่ endpoint นี้ยังคืน token ได้ — frontend
    ใช้ในอนาคตเมื่อ flip flag CSRF_ENABLED
    """
    token = csrf_cookie or secrets.token_urlsafe(32)
    response.set_cookie(
        "csrf_token",
        token,
        httponly=False,           # ต้องอ่านจาก JS เพื่อใส่ใน header
        samesite="strict",
        secure=_is_production(),
        max_age=86400,
        path="/",
    )
    return {"csrf_token": token}
