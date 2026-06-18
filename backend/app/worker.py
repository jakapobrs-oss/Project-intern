"""
Arq worker entry point
รัน background task (§37 worker decomposition)

รันด้วย: arq app.worker.WorkerSettings

Task ที่ implement จริงแล้ว:
- generate_thumbnail / transcode_video  → app/workers/content_tasks.py (§22)
- heartbeat_aggregator                  → app/workers/device_tasks.py (§35)
- expire_emergencies                    → app/workers/emergency_tasks.py (Phase 5)
- daily_report                          → app/workers/report_tasks.py (§28)
"""
from arq.connections import RedisSettings
from arq import cron
from loguru import logger

from app.config import settings
from app.workers.emergency_tasks import expire_emergencies
from app.workers.content_tasks import generate_thumbnail, transcode_video
from app.workers.device_tasks import heartbeat_aggregator
from app.workers.report_tasks import daily_report


async def push_manifest(ctx, player_id: str):
    """
    (ไม่ใช้ใน pull-based architecture) — player ดึง manifest เองผ่าน GET /player/manifest
    เก็บ stub ไว้เผื่ออนาคตเปลี่ยนเป็น push (WebSocket/MQTT) §35.2
    """
    logger.info(f"push_manifest (no-op, pull-based): player={player_id}")


# ===== Worker settings =====

def _redis_settings() -> RedisSettings:
    """แปลง REDIS_URL → RedisSettings"""
    return RedisSettings.from_dsn(settings.redis_url)


class WorkerSettings:
    """Config ของ Arq worker"""
    functions = [
        generate_thumbnail,
        transcode_video,
        heartbeat_aggregator,
        push_manifest,
        daily_report,
        expire_emergencies,
    ]
    redis_settings = _redis_settings()

    cron_jobs = [
        # expire emergency ที่ ends_at < now ทุก 30 วินาที
        cron(expire_emergencies, second={0, 30}, run_at_startup=True),
        # ตัด device ที่ heartbeat หาย > 90s เป็น offline ทุก 1 นาที
        cron(heartbeat_aggregator, minute=set(range(0, 60)), run_at_startup=True),
        # report รายวัน ตี 1
        cron(daily_report, hour={1}, minute={0}),
    ]
