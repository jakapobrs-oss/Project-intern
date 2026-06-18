"""
Test reporting service (§28) + export helpers
ใช้ db_session ตรงๆ (report_service เป็น query layer) + ทดสอบ export เป็น bytes
"""
from datetime import datetime, timedelta, timezone

from app.services import report_service
from app.services.report_export import rows_to_xlsx, report_to_pdf
from app.models.device import Device, DeviceStatus
from app.models.content import Content, ContentType, ApprovalStatus
from app.models.playback import PlaybackLog


async def test_device_status_report(db_session):
    db_session.add_all([
        Device(name="d1", status=DeviceStatus.ONLINE),
        Device(name="d2", status=DeviceStatus.OFFLINE),
        Device(name="d3", status=DeviceStatus.ONLINE),
    ])
    await db_session.commit()
    rep = await report_service.device_status_report(db_session)
    assert rep["total"] == 3
    assert rep["counts"]["online"] == 2
    assert rep["counts"]["offline"] == 1
    assert len(rep["devices"]) == 3


async def test_content_stats_report(db_session, super_admin):
    db_session.add_all([
        Content(name="a", type=ContentType.IMAGE, approval_status=ApprovalStatus.APPROVED, created_by=super_admin.id),
        Content(name="b", type=ContentType.VIDEO, approval_status=ApprovalStatus.PENDING, created_by=super_admin.id),
        Content(name="c", type=ContentType.IMAGE, approval_status=ApprovalStatus.APPROVED, created_by=super_admin.id),
    ])
    await db_session.commit()
    rep = await report_service.content_stats_report(db_session)
    assert rep["total"] == 3
    assert rep["by_type"]["image"] == 2
    assert rep["by_type"]["video"] == 1
    assert rep["by_approval_status"]["approved"] == 2


async def test_play_count_report(db_session, super_admin):
    dev = Device(name="player1", status=DeviceStatus.ONLINE)
    c1 = Content(name="hot", type=ContentType.IMAGE, created_by=super_admin.id)
    c2 = Content(name="cold", type=ContentType.IMAGE, created_by=super_admin.id)
    db_session.add_all([dev, c1, c2])
    await db_session.commit()

    now = datetime.now(timezone.utc)
    db_session.add_all([
        PlaybackLog(device_id=dev.id, content_id=c1.id, played_at=now, duration_sec=10),
        PlaybackLog(device_id=dev.id, content_id=c1.id, played_at=now, duration_sec=12),
        PlaybackLog(device_id=dev.id, content_id=c2.id, played_at=now, duration_sec=5),
        # นอกช่วง 30 วัน → ไม่นับ
        PlaybackLog(device_id=dev.id, content_id=c1.id, played_at=now - timedelta(days=40), duration_sec=99),
    ])
    await db_session.commit()

    rep = await report_service.play_count_report(db_session, days=30)
    assert rep["total_plays"] == 3
    # อันดับแรกต้องเป็น 'hot' (เล่น 2 ครั้ง)
    assert rep["items"][0]["name"] == "hot"
    assert rep["items"][0]["plays"] == 2


# ===== export helpers =====

def test_xlsx_export_produces_bytes():
    blob = rows_to_xlsx("Test", ["a", "b"], [[1, 2], [3, 4]])
    assert isinstance(blob, bytes)
    # XLSX = zip → magic bytes 'PK'
    assert blob[:2] == b"PK"


def test_pdf_export_produces_bytes():
    blob = report_to_pdf("Title", [("Section", ["h1", "h2"], [["x", "y"]])])
    assert isinstance(blob, bytes)
    assert blob[:4] == b"%PDF"
