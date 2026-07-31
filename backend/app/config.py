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
    # s3_endpoint = ที่อยู่ "ฝั่งใน" ที่ backend/worker ใช้คุยกับ MinIO (ชื่อ service ใน docker network)
    s3_endpoint: str = "http://minio:9000"
    s3_access_key: str = "minioadmin"
    s3_secret_key: str = "minioadmin"
    s3_bucket: str = "signage-media"
    s3_region: str = "us-east-1"
    # s3_public_endpoint = ที่อยู่ที่ "เครื่องเล่นข้างนอก" เข้าถึงได้ (LAN IP / โดเมน / CDN)
    #   เว้นว่าง (default) = ไม่ให้ player ยิงหา MinIO ตรงๆ แต่ให้ดึงไฟล์ผ่าน backend
    #   ที่ /api/v1/media (ดู core/media_link.py) — เครื่องเล่นคุยกับ backend ได้อยู่แล้วเสมอ
    #   จึงไม่มีทางเจอปัญหา "แปลชื่อ host ไม่ออก" เหมือนตอน sign ด้วย http://minio:9000
    #   ตั้งค่านี้เมื่ออยากลดภาระ backend แล้วให้ player โหลดจาก MinIO/CDN ตรงๆ
    s3_public_endpoint: str = ""
    # อายุลิงก์สื่อ (วินาที) — player poll manifest ทุก 60s จึงได้ลิงก์ใหม่ก่อนหมดอายุเสมอ
    media_url_ttl_sec: int = 3600

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

    # ===== Trusted proxy (§31 audit) =====
    # รายการ IP/ช่วง IP ของ reverse proxy ที่เชื่อถือได้ คั่นด้วยจุลภาค เช่น "172.16.0.0/12"
    # มีผลกับ IP ที่บันทึกลง audit เท่านั้น: เชื่อ header X-Forwarded-For เฉพาะเมื่อผู้ที่
    # ต่อเข้ามาโดยตรงอยู่ในรายการนี้ — ว่างไว้ = ไม่เชื่อ header เลย ใช้ IP ที่ต่อเข้ามาตรง ๆ
    # (ถ้าเชื่อทุกคน ใครก็แนบ X-Forwarded-For ปลอมให้ audit บันทึก IP ผิดคนได้)
    trusted_proxies: str = ""

    # ===== Account lockout (§26) — ชั้นที่ 2 ถัดจาก rate limit =====
    # กรอกรหัสผิดครบ max_failed_login ครั้ง → ล็อกชั่วคราว lockout_minutes นาที แล้วปลดเอง
    # ตั้งใจให้ "ชั่วคราว" ไม่ใช่ถาวร เพราะล็อกถาวรเปิดช่องให้ใครก็ได้ที่รู้ชื่อผู้ใช้
    # จงใจกรอกผิดเพื่อปิดบัญชีคนอื่น (account-lockout DoS) และทำให้ super_admin
    # บัญชีเดียวล็อกตัวเองแล้วไม่มีใครปลดได้
    max_failed_login: int = 5
    lockout_minutes: int = 15

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
