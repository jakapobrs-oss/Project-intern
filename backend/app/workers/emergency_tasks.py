"""
Emergency-related background tasks (Phase 5 rest)

Tasks:
- expire_emergencies()  → cron ทุกๆ 30 วินาที — เปลี่ยน status ACTIVE → EXPIRED
                          เมื่อ ends_at < now (กัน manifest ยังเห็น emergency หมดอายุค้างไว้)

แยกออกจาก worker.py หลักเพื่อให้ test ได้อิสระ
"""
from __future__ import annotations

from datetime import UTC, datetime

from loguru import logger
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.config import settings
from app.models.emergency import EmergencyBroadcast, EmergencyStatus

# engine สำหรับ worker — ใช้แยกจาก request scope (FastAPI Depends)
# ใน worker ไม่มี request lifecycle เลยต้องสร้าง engine ที่ระดับ module
_worker_engine = None
_worker_sessionmaker: async_sessionmaker[AsyncSession] | None = None


def _get_sessionmaker() -> async_sessionmaker[AsyncSession]:
    """lazy init เพื่อ test mock ได้ + ไม่กิน resource ตอน import"""
    global _worker_engine, _worker_sessionmaker
    if _worker_sessionmaker is None:
        _worker_engine = create_async_engine(settings.database_url, pool_pre_ping=True, future=True)
        _worker_sessionmaker = async_sessionmaker(_worker_engine, expire_on_commit=False)
    return _worker_sessionmaker


async def expire_emergencies_in_session(db: AsyncSession) -> int:
    """
    ส่วน logic ที่ test ได้ — ทำใน session ที่ caller ส่งมา
    return จำนวน row ที่ expire
    """
    now = datetime.now(UTC)
    stmt = (
        select(EmergencyBroadcast.id, EmergencyBroadcast.title)
        .where(EmergencyBroadcast.status == EmergencyStatus.ACTIVE)
        .where(EmergencyBroadcast.ends_at.is_not(None))
        .where(EmergencyBroadcast.ends_at < now)
    )
    rows = (await db.execute(stmt)).all()
    if not rows:
        return 0

    ids = [r.id for r in rows]
    await db.execute(
        update(EmergencyBroadcast)
        .where(EmergencyBroadcast.id.in_(ids))
        .values(status=EmergencyStatus.EXPIRED)
    )
    await db.commit()

    for r in rows:
        logger.info(f"emergency_tasks: auto-expired emergency_id={r.id} title={r.title!r}")
    return len(rows)


async def expire_emergencies(ctx) -> int:
    """Arq entry — เปิด session เอง, return count เพื่อให้ Arq log"""
    sm = _get_sessionmaker()
    async with sm() as db:
        return await expire_emergencies_in_session(db)
