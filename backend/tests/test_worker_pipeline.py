"""
Test worker pipeline (§22 + §28 + §35)
- needs_transcode: pure logic
- mark_stale_offline_in_session: device heartbeat aggregator (ใช้ DB)
- build_daily_summary_in_session: report (ใช้ DB)
"""
from datetime import datetime, timedelta, timezone

from app.workers.content_tasks import needs_transcode
from app.workers.device_tasks import mark_stale_offline_in_session
from app.workers.report_tasks import build_daily_summary_in_session
from app.models.device import Device, DeviceStatus
from app.models.content import Content, ContentType, ApprovalStatus


# ===== needs_transcode (pure) =====

def test_no_transcode_when_in_spec():
    assert needs_transcode("h264", "aac", 1080, 50 * 1024 * 1024) is False


def test_transcode_when_wrong_video_codec():
    assert needs_transcode("hevc", "aac", 1080, 1000) is True


def test_transcode_when_wrong_audio_codec():
    assert needs_transcode("h264", "mp3", 1080, 1000) is True


def test_transcode_when_too_tall():
    assert needs_transcode("h264", "aac", 2160, 1000) is True  # 4K → downscale


def test_transcode_when_too_large():
    assert needs_transcode("h264", "aac", 720, 300 * 1024 * 1024) is True


def test_no_transcode_when_unknown_codecs():
    # ถ้า probe ไม่ได้ (None) และไฟล์เล็ก → ไม่ต้อง transcode
    assert needs_transcode(None, None, None, 1000) is False


# ===== heartbeat aggregator (DB) =====

async def test_mark_stale_offline(db_session):
    now = datetime.now(timezone.utc)
    fresh = Device(name="fresh", status=DeviceStatus.ONLINE, last_heartbeat_at=now)
    stale = Device(name="stale", status=DeviceStatus.ONLINE,
                   last_heartbeat_at=now - timedelta(seconds=300))
    db_session.add_all([fresh, stale])
    await db_session.commit()

    count = await mark_stale_offline_in_session(db_session, threshold_sec=90)
    assert count == 1

    await db_session.refresh(stale)
    await db_session.refresh(fresh)
    assert stale.status == DeviceStatus.OFFLINE
    assert fresh.status == DeviceStatus.ONLINE


async def test_no_stale_devices(db_session):
    now = datetime.now(timezone.utc)
    db_session.add(Device(name="ok", status=DeviceStatus.ONLINE, last_heartbeat_at=now))
    await db_session.commit()
    assert await mark_stale_offline_in_session(db_session, threshold_sec=90) == 0


# ===== daily summary (DB) =====

async def test_daily_summary_counts(db_session, super_admin):
    now = datetime.now(timezone.utc)
    db_session.add_all([
        Device(name="d1", status=DeviceStatus.ONLINE, last_heartbeat_at=now),
        Device(name="d2", status=DeviceStatus.OFFLINE),
        Content(name="c1", type=ContentType.IMAGE,
                approval_status=ApprovalStatus.PENDING, created_by=super_admin.id),
    ])
    await db_session.commit()

    summary = await build_daily_summary_in_session(db_session)
    assert summary["devices_total"] == 2
    assert summary["devices_online"] == 1
    assert summary["devices_offline"] == 1
    assert summary["content_pending_approval"] == 1
