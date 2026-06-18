"""
FastAPI entry point
เริ่ม app + register routers + middleware + lifespan
"""
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger

from app.api.v1.router import api_router
from app.config import settings
from app.core.middleware import CsrfMiddleware, RateLimitMiddleware, SecurityHeadersMiddleware
from app.core.sentry import init_sentry


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifespan hook — รันตอน startup + shutdown
    สำหรับเปิด/ปิด resource เช่น DB pool, Redis, S3 client
    """
    logger.info(f"🚀 Starting Digital Signage API ({settings.app_env})")
    # Sentry (no-op ถ้า DSN ว่าง หรือไม่ได้ติดตั้ง package)
    init_sentry()
    # TODO: init DB pool, Redis, S3 client, ฯลฯ
    yield
    logger.info("👋 Shutting down")
    # TODO: close pools


app = FastAPI(
    title="Digital Signage Management API",
    description="ระบบจัดการจอประชาสัมพันธ์ — Backend API",
    version="0.1.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
    lifespan=lifespan,
)

# ── Middleware (order matters — ลำดับล่างสุด wrap inside, รันก่อน) ──
#
# 1) Security headers — ใส่ headers ก่อนคืน response (outermost)
# 2) Rate limit — บล็อก /auth/login brute force
# 3) CSRF — defense in depth (เปิดเมื่อย้ายไป cookie auth)
# 4) CORS — handle preflight + cross-origin (innermost — รันใกล้ app สุด)
#
# Phase 7 hardening
app.add_middleware(
    SecurityHeadersMiddleware,
    is_production=(settings.app_env != "development"),
)

# Rate limit — เลือก backend memory หรือ redis ผ่าน env
# Redis client lazy-create (กัน startup race condition กับ Redis service)
_redis_client = None
if settings.rate_limit_backend == "redis":
    try:
        import redis.asyncio as redis_async
        _redis_client = redis_async.from_url(settings.redis_url, decode_responses=True)
        logger.info("rate_limit: using Redis backend (multi-instance ready)")
    except ImportError:
        logger.warning("rate_limit: backend=redis แต่ไม่มี package 'redis' — fallback memory")

app.add_middleware(
    RateLimitMiddleware,
    max_requests=settings.rate_limit_max_requests,
    window_sec=settings.rate_limit_window_sec,
    backend=settings.rate_limit_backend,
    redis_client=_redis_client,
)
if settings.csrf_enabled:
    app.add_middleware(
        CsrfMiddleware,
        secure=(settings.app_env != "development"),
    )
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*", "X-CSRF-Token"],
)

# Register API routes (v1)
app.include_router(api_router, prefix="/api/v1")


@app.get("/", tags=["meta"])
async def root():
    """Health check / landing"""
    return {
        "name": "Digital Signage Management API",
        "version": "0.1.0",
        "env": settings.app_env,
        "docs": "/api/docs",
    }


@app.get("/healthz", tags=["meta"])
async def healthz():
    """Liveness probe — สำหรับ k8s / docker healthcheck"""
    return {"status": "ok"}
