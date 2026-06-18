"""
Arq worker entry point
รัน background task (§37 worker decomposition)

รันด้วย: arq app.worker.WorkerSettings
"""
from arq import cron
from arq.connections import RedisSettings
from loguru import logger

from app.config import settings
from app.workers.emergency_tasks import expire_emergencies

# ===== Task stubs (จะ implement ทีละ phase ตาม §37) =====

async def heartbeat_aggregator(ctx):
    """รวบรวม heartbeat จาก players (แทน CentralPlayerInfoHeartbeat เดิม)"""
    logger.info("heartbeat_aggregator: running...")
    # TODO: aggregate heartbeats from Redis → DB


async def push_manifest(ctx, player_id: str):
    """Generate + push manifest JSON ให้ player (แทน ScriptAgent เดิม, §35.2)"""
    logger.info(f"push_manifest: player={player_id}")
    # TODO: build manifest from schedule + contents


async def transcode_video(ctx, content_id: str):
    """Transcode video → MP4 H.264 1080p (§22 content pipeline)"""
    logger.info(f"transcode_video: content={content_id}")
    # TODO: ffmpeg pipeline


async def generate_thumbnail(ctx, content_id: str):
    """Generate thumbnail สำหรับ content (แทน ThumbnailGenerator เดิม)"""
    logger.info(f"generate_thumbnail: content={content_id}")
    # TODO: PIL / ffmpeg


async def daily_report(ctx):
    """รัน report รายวัน + ส่ง email (แทน DailyAgent เดิม)"""
    logger.info("daily_report: running...")
    # TODO


# ===== Worker settings =====

def _redis_settings() -> RedisSettings:
    """แปลง REDIS_URL → RedisSettings"""
    # ใช้ arq parser ของมันเอง
    return RedisSettings.from_dsn(settings.redis_url)


class WorkerSettings:
    """Config ของ Arq worker"""
    functions = [
        heartbeat_aggregator,
        push_manifest,
        transcode_video,
        generate_thumbnail,
        daily_report,
        expire_emergencies,
    ]
    redis_settings = _redis_settings()

    # Cron — ทุก 30 วินาที expire emergency ที่ ends_at < now (Phase 5 rest)
    # ระยะ 30s ดีพอ — manifest cache_seconds=60 อยู่แล้ว
    cron_jobs = [
        cron(expire_emergencies, second={0, 30}, run_at_startup=True),
    ]
