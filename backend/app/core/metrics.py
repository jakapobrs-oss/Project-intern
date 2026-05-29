"""
Prometheus-compatible metrics — Phase 5 monitoring

เริ่มจาก plain-text exposition (ไม่ผูก prometheus-client lib เพื่อลด dep)
ภายหลัง upgrade เป็น prometheus_client ได้ถ้าต้องการ histogram/quantile

Output format:
    # HELP <metric_name> <description>
    # TYPE <metric_name> <counter|gauge|histogram>
    <metric_name>{<label>="<value>"} <number>
"""
from __future__ import annotations
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.device import Device, DeviceStatus
from app.models.content import Content, ApprovalStatus
from app.models.emergency import EmergencyBroadcast, EmergencyStatus


async def build_metrics(db: AsyncSession) -> str:
    """build Prometheus exposition text"""
    lines: list[str] = []

    # --- device by status ---
    device_counts = await _group_count(db, Device.status, DeviceStatus)
    lines += [
        "# HELP signage_devices_total Number of devices by status",
        "# TYPE signage_devices_total gauge",
    ]
    for status_value, count in device_counts.items():
        lines.append(f'signage_devices_total{{status="{status_value}"}} {count}')

    # --- content by approval status ---
    content_counts = await _group_count(db, Content.approval_status, ApprovalStatus)
    lines += [
        "# HELP signage_contents_total Number of contents by approval status",
        "# TYPE signage_contents_total gauge",
    ]
    for status_value, count in content_counts.items():
        lines.append(f'signage_contents_total{{approval="{status_value}"}} {count}')

    # --- emergency active count ---
    active_emergencies = await db.scalar(
        select(func.count(EmergencyBroadcast.id)).where(
            EmergencyBroadcast.status == EmergencyStatus.ACTIVE
        )
    )
    lines += [
        "# HELP signage_emergency_active Active emergency broadcasts",
        "# TYPE signage_emergency_active gauge",
        f"signage_emergency_active {active_emergencies or 0}",
    ]

    # ปิดด้วย \n เพื่อให้ Prometheus parse ได้
    return "\n".join(lines) + "\n"


async def _group_count(db: AsyncSession, column, enum_cls) -> dict[str, int]:
    """count rows group-by column, รวม enum ที่ count=0 ด้วย"""
    stmt = select(column, func.count()).group_by(column)
    rows = (await db.execute(stmt)).all()
    base = {e.value: 0 for e in enum_cls}
    for col_val, n in rows:
        key = col_val.value if hasattr(col_val, "value") else str(col_val)
        base[key] = n
    return base
