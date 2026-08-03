"""
ทดสอบพฤติกรรม dedupe ตอนอัปโหลดสื่อ (SHA-256)

ที่มา: user-test 2026-08-03 เจอว่าอัปโหลดไฟล์ซ้ำแล้ว "เงียบ" — ระบบคืนสื่อเดิมกลับไป
ถูกต้องตามดีไซน์ แต่ไม่มีใครบอกผู้ใช้ ทำให้ชื่อที่ผู้ใช้เพิ่งตั้งหายไปโดยไม่รู้ตัว
และหน้าจอเอาของเดิมมาต่อเป็นแถวใหม่ (แถวซ้ำ id เดียวกัน)

เทสชุดนี้ล็อกสัญญาไว้ว่า ระบบต้อง "บอกได้" ว่าครั้งนี้เป็นไฟล์ซ้ำ ผ่านธง deduplicated
"""
import io

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.content import Content
from app.models.user import User
from app.services import content_service

# PNG 1x1 ที่ถูกต้องตาม magic bytes — เนื้อไฟล์เดียวกันทุกไบต์เมื่อใช้ซ้ำ
PNG_BYTES = (
    b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
    b"\x08\x06\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\nIDATx\x9cc\x00\x01"
    b"\x00\x00\x05\x00\x01\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82"
)


@pytest.fixture(autouse=True)
def _fake_storage(monkeypatch):
    """ตัด S3/MinIO ออกจากเทส — สนใจแค่ตรรกะ dedupe ไม่ใช่การส่งไฟล์จริง"""
    monkeypatch.setattr(content_service, "ensure_bucket", lambda *a, **k: None)
    monkeypatch.setattr(content_service, "upload_fileobj", lambda *a, **k: None)


@pytest.mark.asyncio
async def test_service_flags_duplicate_and_keeps_original(
    db_session: AsyncSession, super_admin: User
):
    """อัปโหลดไฟล์เดิมซ้ำ → ต้องไม่สร้างแถวใหม่ และต้องบอกว่าเป็นของซ้ำ"""
    first, dedup_first = await content_service.upload_content_file(
        db_session,
        file=io.BytesIO(PNG_BYTES),
        filename="poster.png",
        name="โปสเตอร์ต้นฉบับ",
        description="ของจริง",
        created_by=super_admin.id,
    )
    assert dedup_first is False

    second, dedup_second = await content_service.upload_content_file(
        db_session,
        file=io.BytesIO(PNG_BYTES),
        filename="poster-copy.png",
        name="ชื่อใหม่ที่ผู้ใช้ตั้ง",
        description="คำอธิบายใหม่",
        created_by=super_admin.id,
    )

    assert dedup_second is True, "ไฟล์ซ้ำแล้วต้องรายงานว่าเป็นของซ้ำ ไม่ใช่เงียบ"
    assert second.id == first.id, "ต้องคืนรายการเดิม ไม่ใช่สร้างใหม่"
    # ชื่อของเดิมต้องไม่ถูกทับ — ผู้ใช้คนอื่นอาจกำลังใช้สื่อชิ้นนี้อยู่
    assert second.name == "โปสเตอร์ต้นฉบับ"

    rows = (await db_session.execute(select(Content))).scalars().all()
    assert len(rows) == 1, "ต้องมีสื่อแค่ชิ้นเดียวในฐานข้อมูล"


@pytest.mark.asyncio
async def test_upload_endpoint_reports_deduplicated(client: AsyncClient, super_admin: User):
    """หน้าจอต้องอ่านได้จาก response ว่าครั้งนี้เป็นไฟล์ซ้ำหรือของใหม่"""
    login = await client.post(
        "/api/v1/auth/login",
        data={"username": super_admin.username, "password": "testpass123"},
    )
    headers = {"Authorization": f"Bearer {login.json()['access_token']}"}

    first = await client.post(
        "/api/v1/contents/upload",
        headers=headers,
        data={"name": "โปสเตอร์ต้นฉบับ", "description": ""},
        files={"file": ("poster.png", PNG_BYTES, "image/png")},
    )
    assert first.status_code == 201, first.text
    assert first.json()["deduplicated"] is False

    second = await client.post(
        "/api/v1/contents/upload",
        headers=headers,
        data={"name": "ชื่อใหม่ที่ผู้ใช้ตั้ง", "description": ""},
        files={"file": ("poster-copy.png", PNG_BYTES, "image/png")},
    )
    assert second.status_code == 201, second.text
    body = second.json()
    assert body["deduplicated"] is True
    assert body["id"] == first.json()["id"]
    assert body["name"] == "โปสเตอร์ต้นฉบับ"

    listing = await client.get("/api/v1/contents", headers=headers)
    assert len(listing.json()) == 1, "อัปโหลดซ้ำต้องไม่ทำให้มีสื่อเพิ่มในรายการ"


@pytest.mark.asyncio
async def test_duplicate_upload_is_written_to_audit(client: AsyncClient, super_admin: User):
    """ผู้ตรวจสอบต้องแยกออกว่าครั้งไหนเป็นการอัปโหลดซ้ำ (ไม่มีสื่อใหม่เกิดขึ้น)"""
    login = await client.post(
        "/api/v1/auth/login",
        data={"username": super_admin.username, "password": "testpass123"},
    )
    headers = {"Authorization": f"Bearer {login.json()['access_token']}"}
    for name in ("โปสเตอร์ต้นฉบับ", "ชื่อใหม่ที่ผู้ใช้ตั้ง"):
        await client.post(
            "/api/v1/contents/upload",
            headers=headers,
            data={"name": name, "description": ""},
            files={"file": ("poster.png", PNG_BYTES, "image/png")},
        )

    audit = await client.get("/api/v1/audit/logs?action=content.upload", headers=headers)
    assert audit.status_code == 200, audit.text
    messages = [row["message"] for row in audit.json()]
    assert any("ไฟล์ซ้ำ" in m for m in messages), f"audit ไม่ได้บอกว่าเป็นไฟล์ซ้ำ: {messages}"
    assert any("ชื่อใหม่ที่ผู้ใช้ตั้ง" in m for m in messages), "ต้องเก็บชื่อที่ผู้ใช้พยายามตั้งไว้ด้วย"
