"""
Regression tests — ลิงก์ไฟล์สื่อที่ส่งให้เครื่องเล่น (§22)

บั๊กที่ test ชุดนี้กันไม่ให้กลับมา (เจอจาก user-test 2026-07-31):
  manifest เคยส่ง pre-signed URL ที่ sign ด้วย S3_ENDPOINT = http://minio:9000
  ซึ่งเป็นชื่อ service ใน docker network → เครื่องเล่นจริงแปลชื่อไม่ออก → จอดำ
ผลข้างเคียงที่เจอด้วย: ลายเซ็นเปลี่ยนทุกครั้งที่สร้าง manifest → version เปลี่ยนทุก request
  → heartbeat ตอบ manifest_outdated=True ตลอด
"""
import time
from datetime import datetime, timedelta, timezone

import pytest
import pytest_asyncio

from app.config import settings
from app.core.media_link import _sign, build_media_url, verify_media_token
from app.models.content import ApprovalStatus, Content, ContentType
from app.models.device import Device, DevicePlatform, DeviceStatus, PlayerGroup
from app.models.plan import Plan, PlanItem
from app.models.presentation import Presentation, PresentationZone
from app.models.schedule import Schedule, ScheduleStatus
from app.services.manifest_service import build_manifest

STORAGE_KEY = "contents/ab/abcdef/poster.png"


@pytest_asyncio.fixture
async def device_with_image_schedule(db_session, super_admin) -> Device:
    """จอ 1 ตัวในกลุ่มที่มีตารางเล่น active ซึ่งเล่นรูปที่เก็บใน MinIO"""
    device = Device(
        name="TV Lobby",
        platform=DevicePlatform.ANDROID_TV,
        status=DeviceStatus.ONLINE,
        device_token_hash="fake_hash_for_test",
    )
    group = PlayerGroup(name="กลุ่มลอบบี้")
    group.devices.append(device)
    content = Content(
        name="โปสเตอร์ OPD",
        type=ContentType.IMAGE,
        storage_key=STORAGE_KEY,
        mime_type="image/png",
        approval_status=ApprovalStatus.APPROVED,
        created_by=super_admin.id,
    )
    db_session.add_all([device, group, content])
    await db_session.flush()

    presentation = Presentation(
        name="เต็มจอ",
        layout_json={"template": "fullscreen", "zones": [{"key": "main"}]},
        duration_sec=30,
        created_by=super_admin.id,
    )
    presentation.zones.append(
        PresentationZone(zone_key="main", content_id=content.id, order_index=0)
    )
    plan = Plan(name="playlist ลอบบี้", created_by=super_admin.id)
    db_session.add_all([presentation, plan])
    await db_session.flush()

    db_session.add(PlanItem(plan_id=plan.id, presentation_id=presentation.id, order_index=0))
    db_session.add(
        Schedule(
            name="ตารางลอบบี้",
            plan_id=plan.id,
            player_group_id=group.id,
            start_at=datetime.now(timezone.utc) - timedelta(hours=1),
            status=ScheduleStatus.ACTIVE,
            is_active=True,
            created_by=super_admin.id,
        )
    )
    await db_session.commit()
    await db_session.refresh(device)
    return device


def _first_content_url(manifest) -> str:
    assert manifest.items, "manifest ต้องมี item อย่างน้อย 1 (setup ผิดถ้าไม่มี)"
    return manifest.items[0].zones[0].content_url


# ===== ลายเซ็นของลิงก์ =====

def test_verify_accepts_valid_token():
    exp = int(time.time()) + 600
    assert verify_media_token(STORAGE_KEY, exp, _sign(STORAGE_KEY, exp)) is True


def test_verify_rejects_expired_token():
    exp = int(time.time()) - 1
    assert verify_media_token(STORAGE_KEY, exp, _sign(STORAGE_KEY, exp)) is False


def test_verify_rejects_tampered_key():
    """เปลี่ยน key ในลิงก์เพื่อดูดไฟล์อื่น → ต้องไม่ผ่าน"""
    exp = int(time.time()) + 600
    assert verify_media_token("contents/other/secret.png", exp, _sign(STORAGE_KEY, exp)) is False


def test_media_url_is_relative_without_base():
    """ไม่มี request (เช่นเรียกจาก worker) → คืน path relative ให้ client ต่อเอง"""
    url = build_media_url(STORAGE_KEY)
    assert url.startswith("/api/v1/media?")


def test_media_url_is_stable_within_ttl_window():
    """ลิงก์ต้องไม่เปลี่ยนทุกครั้งที่สร้าง ไม่งั้น manifest version เด้งตลอด"""
    assert build_media_url(STORAGE_KEY, "http://x/api/v1/media") == build_media_url(
        STORAGE_KEY, "http://x/api/v1/media"
    )


# ===== manifest ที่ส่งให้เครื่องเล่นจริง =====

@pytest.mark.asyncio
async def test_manifest_media_url_never_points_to_docker_host(device_with_image_schedule, db_session):
    """หัวใจของบั๊ก: URL ในmanifest ต้องไม่ใช่ host ภายใน docker (เครื่องเล่นเรียกไม่ถึง)"""
    manifest = await build_manifest(
        db_session, device_with_image_schedule, "http://192.168.1.10:8000/api/v1/media"
    )
    url = _first_content_url(manifest)
    assert "minio" not in url, f"URL ยังชี้ไป MinIO ภายใน docker: {url}"
    assert url.startswith("http://192.168.1.10:8000/api/v1/media?"), url
    assert "k=" in url and "e=" in url and "s=" in url


@pytest.mark.asyncio
async def test_manifest_version_stable_across_rebuilds(device_with_image_schedule, db_session):
    """สร้าง manifest ซ้ำโดยไม่มีอะไรเปลี่ยน → version ต้องเท่าเดิม (ไม่งั้น player โหลดใหม่ไม่จบ)"""
    base = "http://192.168.1.10:8000/api/v1/media"
    v1 = (await build_manifest(db_session, device_with_image_schedule, base)).version
    v2 = (await build_manifest(db_session, device_with_image_schedule, base)).version
    assert v1 == v2


@pytest.mark.asyncio
async def test_manifest_endpoint_builds_url_from_incoming_request(
    client, device_with_image_schedule, db_session, monkeypatch
):
    """
    ยิง GET /player/manifest จริง → URL สื่อต้องประกอบจาก host ที่ยิงเข้ามา
    (host ที่เครื่องเล่นเพิ่งเรียกสำเร็จ = เรียกซ้ำได้แน่นอน)
    """
    async def _fake_find(db, token):
        return device_with_image_schedule

    monkeypatch.setattr("app.services.device_service.find_device_by_token", _fake_find)

    res = await client.get(
        "/api/v1/player/manifest", headers={"Authorization": "Bearer dev-token"}
    )
    assert res.status_code == 200, res.text
    url = res.json()["items"][0]["zones"][0]["content_url"]
    assert url.startswith("http://test/api/v1/media?"), url


@pytest.mark.asyncio
async def test_media_endpoint_rejects_bad_signature(client):
    """ลิงก์ที่ลายเซ็นไม่ตรง → 403 ไม่ใช่ปล่อยไฟล์ออก"""
    res = await client.get(
        "/api/v1/media",
        params={"k": STORAGE_KEY, "e": int(time.time()) + 600, "s": "not-a-real-signature"},
    )
    assert res.status_code == 403


@pytest.mark.asyncio
async def test_media_endpoint_rejects_expired_link(client):
    exp = int(time.time()) - 10
    res = await client.get(
        "/api/v1/media", params={"k": STORAGE_KEY, "e": exp, "s": _sign(STORAGE_KEY, exp)}
    )
    assert res.status_code == 403


@pytest.mark.asyncio
async def test_media_endpoint_streams_object_when_signature_valid(client, monkeypatch):
    """ลายเซ็นถูก → ส่งไฟล์ออกมาจริง (mock S3 ไม่ให้ test ต้องพึ่ง MinIO)"""
    payload = b"\x89PNG\r\n\x1a\n" + b"0" * 128

    class _Body:
        def __init__(self, data: bytes):
            self._buf = memoryview(data)
            self._pos = 0

        def read(self, n: int = -1) -> bytes:
            chunk = self._buf[self._pos : self._pos + n].tobytes()
            self._pos += len(chunk)
            return chunk

        def close(self):
            pass

    def _fake_get_object(key, byte_range=None, bucket=None):
        assert key == STORAGE_KEY
        return {"Body": _Body(payload), "ContentLength": len(payload), "ContentType": "image/png"}

    monkeypatch.setattr("app.core.storage.get_object", _fake_get_object)

    exp = int(time.time()) + 600
    res = await client.get(
        "/api/v1/media", params={"k": STORAGE_KEY, "e": exp, "s": _sign(STORAGE_KEY, exp)}
    )
    assert res.status_code == 200, res.text
    assert res.headers["content-type"].startswith("image/png")
    assert res.content == payload


@pytest.mark.asyncio
async def test_public_endpoint_mode_signs_with_public_host(device_with_image_schedule, db_session, monkeypatch):
    """ตั้ง S3_PUBLIC_ENDPOINT → กลับไปใช้ presigned URL ตรงจาก MinIO ด้วย host สาธารณะ"""
    monkeypatch.setattr(settings, "s3_public_endpoint", "http://192.168.1.10:9000")
    manifest = await build_manifest(
        db_session, device_with_image_schedule, "http://192.168.1.10:8000/api/v1/media"
    )
    url = _first_content_url(manifest)
    assert url.startswith("http://192.168.1.10:9000/"), url
    assert "X-Amz-Signature" in url
