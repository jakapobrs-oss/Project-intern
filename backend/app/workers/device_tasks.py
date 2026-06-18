"""
Device monitoring tasks (§35 — แทน CentralPlayerInfoHeartbeat เดิม)

- heartbeat_aggregator() — cron: หา device ที่ ONLINE แต่ไม่ส่ง heartbeat
                           เกิน threshold → เปลี่ยนเป็น OFFLINE
  (player heartbeat ทุก 30s → ถ้าหาย > 90s ถือว่า offline)
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from loguru import logger
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.device import Device, DeviceStatus
from app.workers.session import get_sessionmaker


# heartbeat ทุก 30s → ให้ miss 3 ครั้งก่อนตัดเป็น offline
OFFLINE_THRESHOLD_SEC = 90


async def mark_stale_offline_in_session(db: AsyncSession, threshold_sec: int = OFFLINE_THRESHOLD_SEC) -> int:
    """
    logic ที่ test ได้ — เปลี่ยน device ONLINE ที่ heartbeat เก่าเกิน threshold → OFFLINE
    คืนจำนวน device ที่ถูกตัด
    """
    now = datetime.now(timezone.utc)
    cutoff = now - timedelta(seconds=threshold_sec)
    stmt = select(Device.id, Device.name).where(
        Device.status == DeviceStatus.ONLINE,
        Device.last_heartbeat_at.is_not(None),
        Device.last_heartbeat_at < cutoff,
    )
    rows = (await db.execute(stmt)).all()
    if not rows:
        return 0
    ids = [r.id for r in rows]
    await db.execute(
        update(Device).where(Device.id.in_(ids)).values(status=DeviceStatus.OFFLINE)
    )
    await db.commit()
    for r in rows:
        logger.info(f"device_tasks: marked OFFLINE device_id={r.id} name={r.name!r}")
    return len(rows)


async def heartbeat_aggregator(ctx) -> int:
    """Arq entry — เปิด session เอง"""
    async with get_sessionmaker()() as db:
        return await mark_stale_offline_in_session(db)
