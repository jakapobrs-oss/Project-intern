"""
อ่าน config จาก environment variable (Pydantic Settings)
ไฟล์เดียวเป็น single source of truth สำหรับ config ทั้ง backend
"""
from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Config ทั้งหมดที่ดึงจาก .env
    ค่า default ใส่ไว้สำหรับ dev เท่านั้น — production ต้อง override ผ่าน env
    """
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # ===== App =====
    app_env: str = "development"
    app_debug: bool = True
    app_timezone: str = "Asia/Bangkok"
    app_default_lang: str = "th"
    log_level: str = "INFO"

    # ===== Database =====
    database_url: str = "postgresql+asyncpg://signage:signage_dev@postgres:5432/signage"

    # ===== Redis =====
    redis_url: str = "redis://redis:6379/0"

    # ===== S3 / MinIO =====
    s3_endpoint: str = "http://minio:9000"
    s3_access_key: str = "minioadmin"
    s3_secret_key: str = "minioadmin"
    s3_bucket: str = "signage-media"
    s3_region: str = "us-east-1"

    # ===== JWT =====
    jwt_secret_key: str = "change_me"
    jwt_algorithm: str = "HS256"
    jwt_access_expire_minutes: int = 30
    jwt_refresh_expire_days: int = 7

    # ===== Device token (แยกจาก user JWT ตาม §26) =====
    device_token_secret: str = "change_me_too"
    device_token_expire_days: int = 365

    # ===== CORS =====
    cors_origins: str = "http://localhost:3000"

    # ===== Sentry (error tracking) — optional, ปิดถ้า DSN ว่าง =====
    sentry_dsn: str = ""
    sentry_traces_sample_rate: float = 0.0   # 0.0 = ไม่ส่ง performance trace
    sentry_environment: str = ""              # ใช้ app_env ถ้าไม่ระบุ

    # ===== Rate limit (Phase 7) — protect /auth/login จาก brute force =====
    rate_limit_max_requests: int = 10        # ต่อ window
    rate_limit_window_sec: int = 60          # 10 requests / 60s default
    # backend: "memory" (single instance) หรือ "redis" (multi instance)
    rate_limit_backend: str = "memory"

    # ===== CSRF (Phase 7) — เปิดเมื่อ migrate ไป httpOnly cookie auth =====
    # ตอนนี้ frontend ใช้ JWT-in-localStorage → CSRF ไม่ใช่ปัญหา (ปิดโดย default)
    csrf_enabled: bool = False

    # ===== ClamAV virus scan (§22) — env-gated, ปิดใน dev =====
    clamav_enabled: bool = False
    clamav_host: str = "clamav"
    clamav_port: int = 3310
    clamav_fail_closed: bool = True   # ต่อ clamd ไม่ได้ → ปฏิเสธ upload (ปลอดภัยกว่า)

    @property
    def cors_origins_list(self) -> list[str]:
        """แปลง CORS_ORIGINS จาก string คั่นด้วย comma เป็น list"""
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    """ดึง settings แบบ singleton (cache ไว้)"""
    return Settings()


settings = get_settings()
