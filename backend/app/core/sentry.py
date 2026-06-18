"""
Sentry SDK initialization — optional + idempotent + PII scrubbing

ติด sentry-sdk เป็น optional dependency:
- ถ้าไม่ได้ติดตั้ง → skip เงียบ ๆ (log debug)
- ถ้าติดตั้งแต่ SENTRY_DSN ว่าง → skip
- ถ้าครบ → init พร้อม FastAPI integration + before_send scrubber

PII scrubbing (PDPA §31 compliance):
- ลบ password / token / cookie จาก request data
- mask email + phone ใน user context
- strip Authorization header ออกจาก breadcrumbs
- กรอง sensitive query params

ใช้: เรียก `init_sentry()` ครั้งเดียวใน lifespan startup
"""
from __future__ import annotations

import re
from typing import Any

from loguru import logger

from app.config import settings

_initialized = False


# ===== PII scrubbing helpers =====

# field name ที่ต้องลบทิ้ง (case-insensitive substring match)
SENSITIVE_KEYS = frozenset([
    "password",
    "passwd",
    "secret",
    "token",
    "api_key",
    "apikey",
    "authorization",
    "cookie",
    "csrf",
    "device_token",
    "device_token_hash",
    "password_hash",
    "refresh_token",
    "access_token",
    "jwt",
    "pairing_code",
])

# header name ที่ต้อง strip ออกจาก breadcrumb
SENSITIVE_HEADERS = frozenset([
    "authorization",
    "cookie",
    "set-cookie",
    "x-csrf-token",
    "x-api-key",
])

REDACTED = "[Filtered]"

_EMAIL_RE = re.compile(r"([a-zA-Z0-9._%+-]+)@([a-zA-Z0-9.-]+\.[a-zA-Z]{2,})")
_PHONE_TH_RE = re.compile(r"\b0\d{8,9}\b")


def _is_sensitive_key(key: str) -> bool:
    """ตรวจว่า key ชื่อนี้น่าจะเป็น sensitive (case-insensitive substring)"""
    k = key.lower()
    return any(s in k for s in SENSITIVE_KEYS)


def _mask_email(s: str) -> str:
    """admin@example.com → a***@example.com"""
    def _replace(m: re.Match[str]) -> str:
        local, domain = m.group(1), m.group(2)
        masked = local[0] + "***" if local else "***"
        return f"{masked}@{domain}"
    return _EMAIL_RE.sub(_replace, s)


def _mask_phone(s: str) -> str:
    """0812345678 → 081****678"""
    def _replace(m: re.Match[str]) -> str:
        ph = m.group(0)
        if len(ph) < 7:
            return "***"
        return f"{ph[:3]}****{ph[-3:]}"
    return _PHONE_TH_RE.sub(_replace, s)


def _scrub_value(value: Any) -> Any:
    """recursive scrub — keep structure, redact values"""
    if isinstance(value, dict):
        return {k: (REDACTED if _is_sensitive_key(k) else _scrub_value(v)) for k, v in value.items()}
    if isinstance(value, list | tuple):
        return type(value)(_scrub_value(v) for v in value)
    if isinstance(value, str):
        # mask email + phone ใน message-level strings
        return _mask_phone(_mask_email(value))
    return value


def _scrub_headers(headers: dict[str, Any] | None) -> dict[str, Any] | None:
    """strip sensitive headers (Authorization, Cookie, etc.)"""
    if not headers:
        return headers
    return {
        k: (REDACTED if k.lower() in SENSITIVE_HEADERS else v)
        for k, v in headers.items()
    }


def _before_send(event: dict[str, Any], hint: dict[str, Any]) -> dict[str, Any] | None:
    """
    Sentry before_send hook — รันก่อนส่ง event ไป Sentry
    ทำหน้าที่ scrub PII

    return None = ทิ้ง event (ไม่ส่ง)
    return dict = ส่ง (modified)
    """
    try:
        # request body / form / json
        request = event.get("request")
        if isinstance(request, dict):
            if "data" in request:
                request["data"] = _scrub_value(request["data"])
            if "headers" in request:
                request["headers"] = _scrub_headers(request["headers"])
            if "cookies" in request:
                request["cookies"] = REDACTED
            # query string params
            if "query_string" in request and isinstance(request["query_string"], str):
                request["query_string"] = _scrub_query_string(request["query_string"])

        # user context — mask email
        user = event.get("user")
        if isinstance(user, dict) and "email" in user:
            user["email"] = _mask_email(user["email"])

        # breadcrumbs — strip Authorization จาก http breadcrumbs
        breadcrumbs = event.get("breadcrumbs", {}).get("values", [])
        for crumb in breadcrumbs:
            if not isinstance(crumb, dict):
                continue
            data = crumb.get("data", {})
            if isinstance(data, dict):
                crumb["data"] = _scrub_value(data)

        # extra context
        if "extra" in event:
            event["extra"] = _scrub_value(event["extra"])

        # message-level strings (exception messages, log messages)
        if "message" in event and isinstance(event["message"], str):
            event["message"] = _mask_phone(_mask_email(event["message"]))

    except Exception as e:  # noqa: BLE001
        # scrubber error ห้ามทำให้ event หาย — log + ส่งต่อตามเดิม
        logger.warning(f"sentry scrubber error: {e}")

    return event


def _scrub_query_string(qs: str) -> str:
    """scrub sensitive query params เช่น ?token=xxx → ?token=[Filtered]"""
    parts = []
    for kv in qs.split("&"):
        if "=" in kv:
            k, v = kv.split("=", 1)
            if _is_sensitive_key(k):
                parts.append(f"{k}={REDACTED}")
                continue
        parts.append(kv)
    return "&".join(parts)


# ===== init =====

def init_sentry() -> bool:
    """
    Init Sentry — return True ถ้า init สำเร็จ
    เรียกซ้ำได้ปลอดภัย (idempotent)
    """
    global _initialized
    if _initialized:
        return True
    if not settings.sentry_dsn:
        logger.debug("sentry: DSN ว่าง — ข้าม init")
        return False

    try:
        import sentry_sdk
        from sentry_sdk.integrations.fastapi import FastApiIntegration
        from sentry_sdk.integrations.sqlalchemy import SqlalchemyIntegration
        from sentry_sdk.integrations.starlette import StarletteIntegration
    except ImportError:
        logger.warning(
            "sentry: SENTRY_DSN ระบุไว้ แต่ไม่พบ package 'sentry-sdk' — "
            "ติดตั้ง: pip install 'sentry-sdk[fastapi]>=2.0' (optional)"
        )
        return False

    sentry_sdk.init(
        dsn=settings.sentry_dsn,
        environment=settings.sentry_environment or settings.app_env,
        traces_sample_rate=settings.sentry_traces_sample_rate,
        integrations=[
            StarletteIntegration(),
            FastApiIntegration(),
            SqlalchemyIntegration(),
        ],
        # PII off by default (PDPA §31) — ไม่ส่ง IP/user-agent ดิบ
        send_default_pii=False,
        # custom scrubber — กรอง PII ในทุก event (request data, breadcrumbs, etc.)
        before_send=_before_send,
        # request body capture: "small" = ≤4KB only (ลดโอกาส PII รั่ว)
        max_request_body_size="small",
    )
    _initialized = True
    logger.info(f"sentry: initialized (env={settings.sentry_environment or settings.app_env}) with PII scrubbing")
    return True


# ===== exposed สำหรับ testing =====
__all__ = ["init_sentry", "_before_send", "_scrub_value", "_mask_email", "_mask_phone"]
