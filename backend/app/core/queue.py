"""
Arq job enqueue helper — best-effort

ใช้จาก request scope (เช่น content upload) เพื่อโยนงานหนัก (thumbnail/transcode)
ไปให้ worker ทำ background

ออกแบบ best-effort: ถ้า Redis ล่ม/ติดต่อไม่ได้ → log แล้วข้าม
ไม่ทำให้ request หลัก (upload) พังเพราะ background queue มีปัญหา
"""
from __future__ import annotations

from loguru import logger

from app.config import settings

_pool = None


async def _get_pool():
    """lazy create arq redis pool (1 ครั้งต่อ process)"""
    global _pool
    if _pool is None:
        # import ในฟังก์ชันเพื่อไม่ให้ import error ตอน test เก็บ arq ไม่ครบ
        from arq import create_pool
        from arq.connections import RedisSettings

        _pool = await create_pool(RedisSettings.from_dsn(settings.redis_url))
    return _pool


async def enqueue(func_name: str, *args, **kwargs) -> bool:
    """
    โยนงานเข้า arq queue — คืน True ถ้า enqueue สำเร็จ, False ถ้าล้มเหลว (best-effort)
    """
    try:
        pool = await _get_pool()
        await pool.enqueue_job(func_name, *args, **kwargs)
        logger.info(f"enqueue: {func_name} args={args}")
        return True
    except Exception as e:  # noqa: BLE001 — best-effort ตั้งใจ swallow
        logger.warning(f"enqueue failed (ข้ามไป, ไม่กระทบ request): {func_name}: {e}")
        return False
