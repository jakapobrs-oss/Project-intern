"""
Security & rate-limit middleware (Phase 7 hardening)

ใส่ตอน startup ใน main.py — ทำงานก่อน CORS:
  - SecurityHeadersMiddleware: เพิ่ม headers ป้องกัน XSS/clickjacking/mime-sniff
  - RateLimitMiddleware: token bucket per-IP (in-memory) — ป้องกัน brute force
  - CsrfMiddleware: double-submit cookie pattern — defense-in-depth สำหรับ cookie auth

หมายเหตุ:
  - rate limit แบบ in-memory ใช้กับ single-instance; multi-instance ต้องย้ายไป Redis
  - HSTS เปิดเฉพาะตอน production (settings.app_env != development) — กัน lock-out dev
  - CSRF middleware ปิดโดย default (JWT-in-localStorage ตอนนี้ภูมิคุ้มกัน CSRF อยู่แล้ว)
    เปิดเมื่อ migrate ไป httpOnly cookie ผ่าน settings.csrf_enabled
"""
from __future__ import annotations

import hmac
import secrets
import time
from collections import defaultdict, deque
from collections.abc import Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse


# ============================================================================
# Security headers
# ============================================================================
class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """
    เพิ่ม HTTP security headers ทุก response

    Headers:
      - X-Content-Type-Options: nosniff      ← กัน MIME sniffing
      - X-Frame-Options: DENY                ← กัน clickjacking
      - Referrer-Policy: no-referrer         ← กัน leak referer ไป 3rd party
      - Permissions-Policy: ปิด feature ที่ไม่ใช้
      - Strict-Transport-Security (HSTS)     ← เฉพาะ production
      - Content-Security-Policy              ← จำกัด resource sources

    CSP: ไม่ใส่กับ /api/docs (ต้องการ CDN ของ Swagger)
    """

    def __init__(self, app, *, is_production: bool = False):
        super().__init__(app)
        self.is_production = is_production

    async def dispatch(self, request: Request, call_next: Callable):
        response: Response = await call_next(request)

        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("X-Frame-Options", "DENY")
        response.headers.setdefault("Referrer-Policy", "no-referrer")
        response.headers.setdefault(
            "Permissions-Policy",
            "geolocation=(), microphone=(), camera=(), payment=(), usb=()",
        )

        # HSTS เฉพาะ production (HTTP dev จะถูก browser memory ไว้แล้ว force HTTPS)
        if self.is_production:
            response.headers.setdefault(
                "Strict-Transport-Security",
                "max-age=31536000; includeSubDomains",
            )

        # CSP — ไม่ใส่กับ docs endpoint (ต้องการ CDN)
        path = request.url.path
        if not path.startswith("/api/docs") and not path.startswith("/api/redoc"):
            response.headers.setdefault(
                "Content-Security-Policy",
                "default-src 'self'; img-src 'self' data: blob:; "
                "script-src 'self'; style-src 'self' 'unsafe-inline'; "
                "connect-src 'self'; frame-ancestors 'none'",
            )

        return response


# ============================================================================
# Rate limit — token bucket per-IP
#
# Backends:
#   - memory (default): in-memory deque per process — ใช้กับ single instance
#   - redis: INCR + EXPIRE per-IP-per-window — multi-instance support
#
# เลือกผ่าน RateLimitMiddleware(backend="memory"|"redis", redis_client=...)
# ถ้า backend=redis แต่ redis_client=None → fallback memory + log warning
# ============================================================================

class _MemoryBucket:
    """Sliding window bucket — in-memory deque per IP"""

    def __init__(self, max_requests: int, window_sec: int):
        self.max_requests = max_requests
        self.window_sec = window_sec
        self._buckets: dict[str, deque[float]] = defaultdict(deque)

    def check_and_record(self, key: str) -> tuple[bool, int]:
        """
        Return (allowed, retry_after_sec)
        - allowed=True → record + ผ่าน
        - allowed=False → 429, retry_after_sec มีค่า
        """
        bucket = self._buckets[key]
        now = time.monotonic()
        cutoff = now - self.window_sec
        while bucket and bucket[0] < cutoff:
            bucket.popleft()

        if len(bucket) >= self.max_requests:
            retry_after = max(1, int(self.window_sec - (now - bucket[0])))
            return False, retry_after

        bucket.append(now)
        return True, 0


class _RedisBucket:
    """
    Fixed window per-IP — Redis INCR + EXPIRE pattern

    Key format: rl:{key}:{window_bucket}
    - window_bucket = floor(now / window_sec) → คีย์เปลี่ยนทุก window_sec วินาที
    - ทำให้ key หมดอายุเองไม่ต้อง cleanup

    ต่างจาก memory bucket (sliding window) → Redis backend เป็น fixed window
    ขอบเขต: ช่วงท้าย window + ต้น window ถัดไป อาจรับ 2× ของ limit
    ใน production-rate-limit นี้ยอมรับได้ (defense in depth, ไม่ใช่ DDoS protection)
    """

    KEY_PREFIX = "rl"

    def __init__(self, redis_client, max_requests: int, window_sec: int):
        self.redis = redis_client
        self.max_requests = max_requests
        self.window_sec = window_sec

    async def check_and_record(self, key: str) -> tuple[bool, int]:
        import math
        now = time.time()
        window_id = math.floor(now / self.window_sec)
        redis_key = f"{self.KEY_PREFIX}:{key}:{window_id}"

        try:
            # INCR + EXPIRE atomically via pipeline
            pipe = self.redis.pipeline()
            pipe.incr(redis_key)
            pipe.expire(redis_key, self.window_sec + 5)   # buffer 5s
            results = await pipe.execute()
            count = int(results[0])
        except Exception as e:
            from loguru import logger
            logger.warning(f"rate_limit Redis error: {e} — fail-open")
            return True, 0

        if count > self.max_requests:
            # next window starts at (window_id + 1) * window_sec
            retry_after = max(1, int((window_id + 1) * self.window_sec - now))
            return False, retry_after

        return True, 0


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Per-IP rate limit สำหรับ login (กัน brute force)

    Args:
        max_requests: ต่อ window
        window_sec: window size (วินาที)
        protected_prefixes: path prefixes ที่ check
        backend: "memory" หรือ "redis"
        redis_client: async Redis client (ต้องมีถ้า backend="redis")
    """

    def __init__(
        self,
        app,
        *,
        max_requests: int = 10,
        window_sec: int = 60,
        protected_prefixes: tuple[str, ...] = ("/api/v1/auth/login",),
        backend: str = "memory",
        redis_client=None,
    ):
        super().__init__(app)
        self.protected_prefixes = protected_prefixes

        if backend == "redis" and redis_client is not None:
            self.bucket = _RedisBucket(redis_client, max_requests, window_sec)
            self._is_async = True
        else:
            if backend == "redis":
                from loguru import logger
                logger.warning("rate_limit: backend=redis แต่ไม่มี redis_client — fallback memory")
            self.bucket = _MemoryBucket(max_requests, window_sec)
            self._is_async = False

    async def dispatch(self, request: Request, call_next: Callable):
        if not any(request.url.path.startswith(p) for p in self.protected_prefixes):
            return await call_next(request)

        ip = _client_ip(request)
        if self._is_async:
            allowed, retry_after = await self.bucket.check_and_record(ip)
        else:
            allowed, retry_after = self.bucket.check_and_record(ip)

        if not allowed:
            return JSONResponse(
                status_code=429,
                content={
                    "detail": {
                        "code": "RATE_LIMITED",
                        "message": f"พยายามมากเกินไป — ลองอีกครั้งใน {retry_after} วินาที",
                    }
                },
                headers={"Retry-After": str(retry_after)},
            )

        return await call_next(request)


def _client_ip(request: Request) -> str:
    """ดึง client IP — respect X-Forwarded-For (กรณีอยู่หลัง nginx/load-balancer)"""
    fwd = request.headers.get("x-forwarded-for")
    if fwd:
        return fwd.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


# ============================================================================
# CSRF — double-submit cookie pattern
# ============================================================================
#
# Flow (เปิดเมื่อย้ายไป httpOnly cookie auth):
#   1. GET ทุก route → response set cookie `csrf_token` (non-httpOnly, samesite=strict)
#   2. Frontend อ่าน cookie ส่งคืนใน header `X-CSRF-Token` ตอน mutate request
#   3. Middleware เปรียบเทียบ cookie vs header → match ผ่าน, ไม่ match → 403
#
# ทำไม double-submit (ไม่ใช่ synchronizer token)?
#   - ไม่ต้อง server-side state — scale ได้
#   - ใช้ได้กับ SPA (Next.js) ตรงๆ
#
# จำกัด:
#   - subdomain ที่ตั้ง cookie ได้ → bypass ได้ → ต้อง strict samesite + secure flag
# ============================================================================
class CsrfMiddleware(BaseHTTPMiddleware):
    """
    CSRF protection — double-submit cookie

    Args:
        cookie_name: ชื่อ cookie (default "csrf_token")
        header_name: ชื่อ header ที่ frontend ส่งกลับ (default "X-CSRF-Token")
        secure: เซ็ต Secure flag (production ต้อง True เพราะ HTTPS only)
        protected_methods: methods ที่ check CSRF (POST/PUT/PATCH/DELETE)
        exempt_paths: prefix ที่ยกเว้น (เช่น `/api/v1/player/` — player ใช้ Bearer token)
    """

    def __init__(
        self,
        app,
        *,
        cookie_name: str = "csrf_token",
        header_name: str = "X-CSRF-Token",
        secure: bool = False,
        protected_methods: tuple[str, ...] = ("POST", "PUT", "PATCH", "DELETE"),
        exempt_paths: tuple[str, ...] = ("/api/v1/player/", "/api/v1/auth/login", "/api/v1/auth/refresh"),
    ):
        super().__init__(app)
        self.cookie_name = cookie_name
        self.header_name = header_name
        self.secure = secure
        self.protected_methods = protected_methods
        self.exempt_paths = exempt_paths

    async def dispatch(self, request: Request, call_next: Callable):
        method = request.method.upper()
        path = request.url.path

        # state-changing request → check token
        if method in self.protected_methods and not any(path.startswith(p) for p in self.exempt_paths):
            cookie_token = request.cookies.get(self.cookie_name)
            header_token = request.headers.get(self.header_name)

            # constant-time compare (กัน timing attack)
            if not cookie_token or not header_token or not hmac.compare_digest(cookie_token, header_token):
                return JSONResponse(
                    status_code=403,
                    content={
                        "detail": {
                            "code": "CSRF_INVALID",
                            "message": "CSRF token ไม่ถูกต้องหรือหายไป",
                        }
                    },
                )

        response = await call_next(request)

        # set cookie ถ้ายังไม่มี — ทุก response (idempotent — ไม่ทับถ้ามี)
        if not request.cookies.get(self.cookie_name):
            token = secrets.token_urlsafe(32)
            response.set_cookie(
                key=self.cookie_name,
                value=token,
                httponly=False,         # ต้องอ่านได้จาก JS เพื่อใส่ใน header
                samesite="strict",
                secure=self.secure,
                max_age=86400,          # 1 วัน
            )

        return response
