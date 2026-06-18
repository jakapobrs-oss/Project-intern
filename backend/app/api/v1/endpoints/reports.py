"""
Reporting endpoints (§28)

JSON:
- GET /reports/devices         — device status report
- GET /reports/content         — content library stats
- GET /reports/play-count      — content play counts (N วัน)
- GET /reports/audit-summary   — audit event summary (N วัน)

Export:
- GET /reports/devices.xlsx    — Excel ของ device report
- GET /reports/summary.pdf     — PDF รวมหลาย section
"""
from fastapi import APIRouter, Depends, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.deps import require_role
from app.db import get_db
from app.models.user import User, Role
from app.services import report_service
from app.services.report_export import rows_to_xlsx, report_to_pdf, ExportUnavailable
from fastapi import HTTPException


router = APIRouter()

# admin/super/viewer/operator ดู report ได้ (editor/approver โฟกัสงาน content)
_can_view = require_role(Role.SUPER_ADMIN, Role.ADMIN, Role.VIEWER, Role.OPERATOR)


@router.get("/devices")
async def report_devices(db: AsyncSession = Depends(get_db), _: User = Depends(_can_view)):
    return await report_service.device_status_report(db)


@router.get("/content")
async def report_content(db: AsyncSession = Depends(get_db), _: User = Depends(_can_view)):
    return await report_service.content_stats_report(db)


@router.get("/play-count")
async def report_play_count(
    days: int = 30,
    limit: int = 50,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(_can_view),
):
    return await report_service.play_count_report(db, days=days, limit=limit)


@router.get("/audit-summary")
async def report_audit_summary(
    days: int = 30,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(_can_view),
):
    return await report_service.audit_summary_report(db, days=days)


@router.get("/devices.xlsx")
async def export_devices_xlsx(db: AsyncSession = Depends(get_db), _: User = Depends(_can_view)):
    """ดาวน์โหลด device report เป็น Excel"""
    data = await report_service.device_status_report(db)
    headers = ["ชื่อจอ", "ตำแหน่ง", "สถานะ", "heartbeat ล่าสุด", "uptime (วิ)", "เวอร์ชัน"]
    rows = [
        [d["name"], d["location"], d["status"], d["last_heartbeat_at"] or "-",
         d["uptime_sec"] if d["uptime_sec"] is not None else "-", d["app_version"] or "-"]
        for d in data["devices"]
    ]
    try:
        blob = rows_to_xlsx("Devices", headers, rows)
    except ExportUnavailable as e:
        raise HTTPException(503, str(e))
    return Response(
        content=blob,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": 'attachment; filename="device-report.xlsx"'},
    )


@router.get("/summary.pdf")
async def export_summary_pdf(db: AsyncSession = Depends(get_db), _: User = Depends(_can_view)):
    """ดาวน์โหลด PDF สรุป device + content + play-count (สำหรับผู้บริหาร)"""
    devices = await report_service.device_status_report(db)
    content = await report_service.content_stats_report(db)
    plays = await report_service.play_count_report(db, days=30, limit=20)

    sections = [
        (
            "สถานะจอ (Device Status)",
            ["ชื่อจอ", "ตำแหน่ง", "สถานะ", "heartbeat ล่าสุด"],
            [[d["name"], d["location"], d["status"], d["last_heartbeat_at"] or "-"] for d in devices["devices"]],
        ),
        (
            "สรุป Content",
            ["ประเภท/สถานะ", "จำนวน"],
            (
                [[f"type:{k}", v] for k, v in content["by_type"].items()]
                + [[f"approval:{k}", v] for k, v in content["by_approval_status"].items()]
            ),
        ),
        (
            "Content เล่นบ่อยสุด (30 วัน)",
            ["content", "จำนวนครั้ง", "รวมวินาที"],
            [[i["name"], i["plays"], i["total_seconds"]] for i in plays["items"]],
        ),
    ]
    try:
        blob = report_to_pdf("รายงานสรุประบบ Digital Signage", sections)
    except ExportUnavailable as e:
        raise HTTPException(503, str(e))
    return Response(
        content=blob,
        media_type="application/pdf",
        headers={"Content-Disposition": 'attachment; filename="signage-summary.pdf"'},
    )
