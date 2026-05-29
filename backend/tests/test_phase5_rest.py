"""
Phase 5 rest — tests สำหรับ:
1. manifest emergency integration (override + targeting + version bump)
2. worker auto-expire emergency
3. audit on more events (content.approve, schedule.activate/pause, device.pair, tv.command_sent)
"""
from datetime import datetime, timedelta, timezone
import uuid
import pytest
import pytest_asyncio
from sqlalchemy import select

from app.models.audit import AuditLog, AuditOutcome
from app.models.content import Content, ContentType, ApprovalStatus
from app.models.device import Device, DevicePlatform, DeviceStatus, PlayerGroup
from app.models.emergency import EmergencyBroadcast, EmergencyKind, EmergencyStatus
from app.models.schedule import Schedule, ScheduleStatus
from app.models.plan import Plan
from app.workers.emergency_tasks import expire_emergencies_in_session
from app.services.manifest_service import build_manifest, _active_emergencies_for


async def _login(client, username: str, password: str = "testpass123") -> str:
    res = await client.post(
        "/api/v1/auth/login",
        data={"username": username, "password": password},
    )
    assert res.status_code == 200, res.text
    return res.json()["access_token"]


# ============================================================================
# 1) Manifest emergency integration
# ============================================================================

@pytest_asyncio.fixture
async def paired_device(db_session, super_admin) -> Device:
    """device ที่ pair แล้ว — รวมเป็น fixture ใช้ซ้ำ"""
    device = Device(
        name="TV Lobby",
        location="ชั้น 1",
        platform=DevicePlatform.ANDROID_TV,
        status=DeviceStatus.ONLINE,
        device_token_hash="fake_hash_for_test",
    )
    db_session.add(device)
    await db_session.commit()
    await db_session.refresh(device)
    return device


@pytest.mark.asyncio
async def test_manifest_includes_active_emergency_with_target_all(db_session, paired_device, super_admin):
    """emergency targeting {all: true} → ต้องอยู่ใน manifest ของ device ใดก็ตาม"""
    emer = EmergencyBroadcast(
        title="ไฟไหม้",
        kind=EmergencyKind.TEXT,
        payload={"message": "อพยพ", "bg_color": "#c00"},
        target={"all": True},
        status=EmergencyStatus.ACTIVE,
        priority=2000,
        created_by=super_admin.id,
    )
    db_session.add(emer)
    await db_session.commit()

    manifest = await build_manifest(db_session, paired_device)
    assert len(manifest.emergencies) == 1
    assert manifest.emergencies[0].title == "ไฟไหม้"
    assert manifest.emergencies[0].priority == 2000


@pytest.mark.asyncio
async def test_manifest_excludes_emergency_not_targeting_device(db_session, paired_device, super_admin):
    """emergency target device_ids อื่น → ต้องไม่อยู่ใน manifest"""
    other_id = uuid.uuid4()
    emer = EmergencyBroadcast(
        title="อื่น",
        kind=EmergencyKind.TEXT,
        payload={"message": "x"},
        target={"device_ids": [str(other_id)]},
        status=EmergencyStatus.ACTIVE,
        created_by=super_admin.id,
    )
    db_session.add(emer)
    await db_session.commit()

    manifest = await build_manifest(db_session, paired_device)
    assert manifest.emergencies == []


@pytest.mark.asyncio
async def test_manifest_excludes_emergency_outside_time_window(db_session, paired_device, super_admin):
    """emergency ที่ end_at < now → ไม่ใส่ใน manifest (ถึงจะยัง status=ACTIVE)"""
    past = datetime.now(timezone.utc) - timedelta(hours=1)
    emer = EmergencyBroadcast(
        title="หมดอายุแล้ว",
        kind=EmergencyKind.TEXT,
        payload={"message": "x"},
        target={"all": True},
        status=EmergencyStatus.ACTIVE,
        starts_at=past - timedelta(hours=2),
        ends_at=past,
        created_by=super_admin.id,
    )
    db_session.add(emer)
    await db_session.commit()

    manifest = await build_manifest(db_session, paired_device)
    assert manifest.emergencies == []


@pytest.mark.asyncio
async def test_manifest_version_changes_when_emergency_added(db_session, paired_device, super_admin):
    """version ต้องเปลี่ยนเมื่อ emergency activate → player heartbeat เห็น outdated"""
    m1 = await build_manifest(db_session, paired_device)
    v1 = m1.version

    db_session.add(EmergencyBroadcast(
        title="ใหม่",
        kind=EmergencyKind.TEXT,
        payload={"message": "x"},
        target={"all": True},
        status=EmergencyStatus.ACTIVE,
        created_by=super_admin.id,
    ))
    await db_session.commit()

    m2 = await build_manifest(db_session, paired_device)
    assert m2.version != v1, "manifest version ต้องเปลี่ยนเมื่อ emergency activate"


# ============================================================================
# 2) Worker auto-expire
# ============================================================================

@pytest.mark.asyncio
async def test_expire_emergencies_marks_past_ends_at_as_expired(db_session, super_admin):
    """auto-expire: ACTIVE + ends_at < now → EXPIRED"""
    past = datetime.now(timezone.utc) - timedelta(minutes=10)
    future = datetime.now(timezone.utc) + timedelta(hours=1)

    e_expired = EmergencyBroadcast(
        title="ควรหมดอายุ", kind=EmergencyKind.TEXT,
        payload={"message": "x"}, target={"all": True},
        status=EmergencyStatus.ACTIVE,
        ends_at=past, created_by=super_admin.id,
    )
    e_still_active = EmergencyBroadcast(
        title="ยังไม่หมด", kind=EmergencyKind.TEXT,
        payload={"message": "x"}, target={"all": True},
        status=EmergencyStatus.ACTIVE,
        ends_at=future, created_by=super_admin.id,
    )
    e_no_end = EmergencyBroadcast(
        title="ไม่มีหมดอายุ", kind=EmergencyKind.TEXT,
        payload={"message": "x"}, target={"all": True},
        status=EmergencyStatus.ACTIVE,
        ends_at=None, created_by=super_admin.id,
    )
    db_session.add_all([e_expired, e_still_active, e_no_end])
    await db_session.commit()

    count = await expire_emergencies_in_session(db_session)
    assert count == 1

    await db_session.refresh(e_expired)
    await db_session.refresh(e_still_active)
    await db_session.refresh(e_no_end)
    assert e_expired.status == EmergencyStatus.EXPIRED
    assert e_still_active.status == EmergencyStatus.ACTIVE
    assert e_no_end.status == EmergencyStatus.ACTIVE


@pytest.mark.asyncio
async def test_expire_emergencies_is_idempotent(db_session, super_admin):
    """รัน expire ซ้ำ → count=0 ครั้งที่สอง"""
    db_session.add(EmergencyBroadcast(
        title="หมด", kind=EmergencyKind.TEXT,
        payload={"message": "x"}, target={"all": True},
        status=EmergencyStatus.ACTIVE,
        ends_at=datetime.now(timezone.utc) - timedelta(seconds=1),
        created_by=super_admin.id,
    ))
    await db_session.commit()

    first = await expire_emergencies_in_session(db_session)
    second = await expire_emergencies_in_session(db_session)
    assert first == 1
    assert second == 0


# ============================================================================
# 3) Audit-on-more-events
# ============================================================================

@pytest.mark.asyncio
async def test_audit_logged_when_content_approved(client, db_session, super_admin):
    """approve content → audit row action=content.approve"""
    content = Content(
        name="ภาพประชาสัมพันธ์", type=ContentType.IMAGE,
        approval_status=ApprovalStatus.PENDING,
        created_by=super_admin.id,
    )
    db_session.add(content)
    await db_session.commit()
    await db_session.refresh(content)

    token = await _login(client, "superadmin")
    res = await client.post(
        f"/api/v1/contents/{content.id}/approve",
        headers={"Authorization": f"Bearer {token}"},
        json={"approve": True},
    )
    assert res.status_code == 200, res.text

    rows = (await db_session.execute(
        select(AuditLog).where(AuditLog.action == "content.approve")
    )).scalars().all()
    assert any(str(r.target_id) == str(content.id) for r in rows)


@pytest.mark.asyncio
async def test_audit_logged_when_content_rejected(client, db_session, super_admin):
    """reject content → audit action=content.reject + เก็บเหตุผลใน message"""
    content = Content(
        name="ภาพที่ถูก reject", type=ContentType.IMAGE,
        approval_status=ApprovalStatus.PENDING,
        created_by=super_admin.id,
    )
    db_session.add(content)
    await db_session.commit()
    await db_session.refresh(content)

    token = await _login(client, "superadmin")
    res = await client.post(
        f"/api/v1/contents/{content.id}/approve",
        headers={"Authorization": f"Bearer {token}"},
        json={"approve": False, "rejection_reason": "ภาพไม่ชัด"},
    )
    assert res.status_code == 200, res.text

    rows = (await db_session.execute(
        select(AuditLog).where(AuditLog.action == "content.reject")
    )).scalars().all()
    assert len(rows) >= 1
    assert any("ภาพไม่ชัด" in (r.message or "") for r in rows)


@pytest.mark.asyncio
async def test_audit_logged_when_device_pair_fails(client, db_session):
    """pair ด้วย code ที่ไม่มี → audit outcome=FAIL"""
    res = await client.post(
        "/api/v1/player/pair",
        json={
            "pairing_code": "INVALID",
            "platform": "android_tv",
            "mac_address": None,
            "serial_number": None,
            "app_version": "0.1.0",
        },
    )
    assert res.status_code == 404

    rows = (await db_session.execute(
        select(AuditLog).where(AuditLog.action == "device.pair")
    )).scalars().all()
    assert any(r.outcome == AuditOutcome.FAIL for r in rows)


@pytest.mark.asyncio
async def test_audit_logged_when_device_pair_succeeds(client, db_session, super_admin):
    """pair สำเร็จ → audit outcome=SUCCESS + actor_type=device"""
    # admin สร้าง device ก่อน (เพื่อมี pairing_code)
    token = await _login(client, "superadmin")
    res = await client.post(
        "/api/v1/devices",
        headers={"Authorization": f"Bearer {token}"},
        json={"name": "Test TV", "location": "test", "platform": "android_tv"},
    )
    assert res.status_code == 201, res.text
    device_data = res.json()
    pairing_code = device_data["pairing_code"]

    # player claim
    res = await client.post(
        "/api/v1/player/pair",
        json={
            "pairing_code": pairing_code,
            "platform": "android_tv",
            "mac_address": "aa:bb:cc:dd:ee:ff",
            "serial_number": "SN001",
            "app_version": "0.1.0",
        },
    )
    assert res.status_code == 200, res.text

    rows = (await db_session.execute(
        select(AuditLog).where(AuditLog.action == "device.pair", AuditLog.outcome == AuditOutcome.SUCCESS)
    )).scalars().all()
    assert len(rows) >= 1
    assert rows[0].actor_type == "device"


@pytest.mark.asyncio
async def test_audit_logged_when_schedule_activated(client, db_session, super_admin):
    """schedule approve → audit action=schedule.activate"""
    # สร้าง plan + group + schedule แบบ minimal
    plan = Plan(name=f"Plan {uuid.uuid4().hex[:6]}", created_by=super_admin.id)
    group = PlayerGroup(name=f"Group {uuid.uuid4().hex[:6]}")
    db_session.add_all([plan, group])
    await db_session.commit()
    await db_session.refresh(plan)
    await db_session.refresh(group)

    sch = Schedule(
        name="ทดสอบ",
        plan_id=plan.id,
        player_group_id=group.id,
        start_at=datetime.now(timezone.utc),
        end_at=datetime.now(timezone.utc) + timedelta(days=1),
        status=ScheduleStatus.PENDING_APPROVAL,
        created_by=super_admin.id,
    )
    db_session.add(sch)
    await db_session.commit()
    await db_session.refresh(sch)

    token = await _login(client, "superadmin")
    res = await client.post(
        f"/api/v1/schedules/{sch.id}/approve",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 200, res.text

    rows = (await db_session.execute(
        select(AuditLog).where(AuditLog.action == "schedule.activate")
    )).scalars().all()
    assert any(str(r.target_id) == str(sch.id) for r in rows)
