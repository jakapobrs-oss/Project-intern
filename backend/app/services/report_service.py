"""
Report service (§28) — คำนวณ report จากข้อมูลที่มีในระบบ

Report ที่รองรับ:
- device_status_report  : นับ online/offline/error + รายตัว (uptime, last heartbeat)
- content_stats_report  : นับ content แยกตาม approval status + type
- play_count_report     : content ไหนถูกเล่นกี่ครั้ง (จาก playback_logs §28)
- audit_summary_report  : นับ event แยก action ในช่วงเวลา

ทุกฟังก์ชันคืน dict/list ของ primitive → endpoint ส่งเป็น JSON หรือส่งต่อให้ export
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.audit import AuditLog
from app.models.content import Content, ContentType, ApprovalStatus
from app.models.device import Device, DeviceStatus
from app.models.playback import PlaybackLog


async def device_status_report(db: AsyncSession) -> dict:
    """สรุปสถานะ device — counts + รายตัว"""
    counts: dict[str, int] = {s.value: 0 for s in DeviceStatus}
    rows = (await db.execute(
        select(Device.status, func.count()).group_by(Device.status)
    )).all()
    for status, n in rows:
        key = status.value if hasattr(status, "value") else str(status)
        counts[key] = int(n)

    devices = (await db.execute(
        select(Device).order_by(Device.name)
    )).scalars().all()
    items = [
        {
            "id": str(d.id),
            "name": d.name,
            "location": d.location,
            "status": d.status.value,
            "last_heartbeat_at": d.last_heartbeat_at.isoformat() if d.last_heartbeat_at else None,
            "uptime_sec": d.uptime_sec,
            "app_version": d.app_version,
        }
        for d in devices
    ]
    return {"counts": counts, "total": len(items), "devices": items}


async def content_stats_report(db: AsyncSession) -> dict:
    """นับ content แยกตาม approval status + type"""
    by_status: dict[str, int] = {s.value: 0 for s in ApprovalStatus}
    for status, n in (await db.execute(
        select(Content.approval_status, func.count()).group_by(Content.approval_status)
    )).all():
        by_status[status.value if hasattr(status, "value") else str(status)] = int(n)

    by_type: dict[str, int] = {t.value: 0 for t in ContentType}
    for ctype, n in (await db.execute(
        select(Content.type, func.count()).group_by(Content.type)
    )).all():
        by_type[ctype.value if hasattr(ctype, "value") else str(ctype)] = int(n)

    total = int((await db.execute(select(func.count()).select_from(Content))).scalar() or 0)
    return {"total": total, "by_approval_status": by_status, "by_type": by_type}


async def play_count_report(db: AsyncSession, days: int = 30, limit: int = 50) -> dict:
    """content ไหนถูกเล่นกี่ครั้งในช่วง N วัน (จาก playback_logs)"""
    since = datetime.now(timezone.utc) - timedelta(days=days)
    stmt = (
        select(
            PlaybackLog.content_id,
            Content.name,
            func.count().label("plays"),
            func.coalesce(func.sum(PlaybackLog.duration_sec), 0).label("total_sec"),
        )
        .join(Content, Content.id == PlaybackLog.content_id, isouter=True)
        .where(PlaybackLog.played_at >= since)
        .group_by(PlaybackLog.content_id, Content.name)
        .order_by(func.count().desc())
        .limit(limit)
    )
    rows = (await db.execute(stmt)).all()
    items = [
        {
            "content_id": str(cid) if cid else None,
            "name": name or "(deleted)",
            "plays": int(plays),
            "total_seconds": float(total_sec or 0),
        }
        for cid, name, plays, total_sec in rows
    ]
    total_plays = sum(i["plays"] for i in items)
    return {"period_days": days, "total_plays": total_plays, "items": items}


async def audit_summary_report(db: AsyncSession, days: int = 30) -> dict:
    """นับ audit event แยก action ในช่วง N วัน"""
    since = datetime.now(timezone.utc) - timedelta(days=days)
    rows = (await db.execute(
        select(AuditLog.action, AuditLog.outcome, func.count())
        .where(AuditLog.created_at >= since)
        .group_by(AuditLog.action, AuditLog.outcome)
        .order_by(func.count().desc())
    )).all()
    items = [
        {
            "action": action,
            "outcome": outcome.value if hasattr(outcome, "value") else str(outcome),
            "count": int(n),
        }
        for action, outcome, n in rows
    ]
    return {"period_days": days, "items": items}
