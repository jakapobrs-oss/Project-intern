"""
Reporting tasks (§28) — แทน DailyAgent เดิม

- daily_report() — cron ตี 1: คำนวณสรุปรายวัน (device online/offline, content รออนุมัติ,
  schedule active) แล้ว log ไว้ — ฐานสำหรับต่อยอดส่ง email/บันทึก snapshot ภายหลัง

logic จริงของ report (uptime/play-count/compliance) อยู่ที่ app/services/report_service.py
"""
from __future__ import annotations

from loguru import logger
from sqlalchemy import func, select

from app.models.content import Content, ApprovalStatus
from app.models.device import Device, DeviceStatus
from app.models.schedule import Schedule, ScheduleStatus
from app.workers.session import get_sessionmaker


async def build_daily_summary_in_session(db) -> dict:
    """สรุปตัวเลขรายวัน — แยกเป็นฟังก์ชันเพื่อ test ได้"""
    async def _count(stmt) -> int:
        return int((await db.execute(stmt)).scalar() or 0)

    online = await _count(select(func.count()).select_from(Device).where(Device.status == DeviceStatus.ONLINE))
    offline = await _count(select(func.count()).select_from(Device).where(Device.status == DeviceStatus.OFFLINE))
    total_devices = await _count(select(func.count()).select_from(Device))
    pending_content = await _count(
        select(func.count()).select_from(Content).where(Content.approval_status == ApprovalStatus.PENDING)
    )
    active_schedules = await _count(
        select(func.count()).select_from(Schedule).where(Schedule.status == ScheduleStatus.ACTIVE)
    )
    return {
        "devices_total": total_devices,
        "devices_online": online,
        "devices_offline": offline,
        "content_pending_approval": pending_content,
        "schedules_active": active_schedules,
    }


async def daily_report(ctx) -> dict:
    """Arq entry — สร้างสรุปรายวันแล้ว log"""
    async with get_sessionmaker()() as db:
        summary = await build_daily_summary_in_session(db)
    logger.info(f"daily_report: {summary}")
    return summary
