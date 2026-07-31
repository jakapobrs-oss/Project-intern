"""
ทดสอบว่า audit บันทึกครบจริง — ไม่ใช่แค่มีโค้ดเรียก

ที่มา: user-test 2026-07-31 พบว่าหน้าจอเคลมว่า "บันทึก action ทุกอย่างใน system"
แต่ของจริงบันทึกแค่ 11 ชนิด (สร้าง/แก้/ลบ ไม่เคยถูกบันทึกเลย) และตัวกรองในหน้าจอ
มีตัวเลือกที่ไม่มีวันมีข้อมูลเพราะ hardcode ไว้แล้วหลุดจากของจริง
"""
import re
from pathlib import Path

import pytest
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.audit import AuditLog, AuditOutcome
from app.models.user import User
from app.services import audit_service


async def _login(client: AsyncClient, username: str, password: str = "testpass123") -> str:
    res = await client.post(
        "/api/v1/auth/login", data={"username": username, "password": password}
    )
    assert res.status_code == 200, res.text
    return res.json()["access_token"]


async def _actions_in_db(db: AsyncSession) -> list[str]:
    rows = (await db.execute(select(AuditLog.action))).scalars().all()
    return list(rows)


# ===== ไม่ให้รายชื่อ action หลุดจากของจริงอีก =====

APP_DIR = Path(__file__).resolve().parent.parent / "app"
# ไฟล์ที่เก็บลิสต์เอง — ต้องกันออกจากการสแกน ไม่งั้นลิสต์จะยืนยันตัวเอง
_DECLARATION_FILE = APP_DIR / "services" / "audit_service.py"


def _source_files() -> list[Path]:
    return [p for p in APP_DIR.rglob("*.py") if p != _DECLARATION_FILE]


def _actions_written_in_code() -> set[str]:
    """
    ดึง action ที่โค้ดเขียนจริง — รองรับทั้ง 3 รูปแบบที่ใช้อยู่:
      action="x.y"                          (log_event แบบ keyword)
      log_action(db, request, user, "x.y")  (positional arg ตัวที่ 4)
      audit_action = "x.y"                  (เก็บใส่ตัวแปรก่อน)
    """
    literal = re.compile(r'["\']([a-z_]+\.[a-z_]+)["\']')
    call_start = re.compile(r"log_action\(|log_event\(")
    found: set[str] = set()
    for py in _source_files():
        src = py.read_text(encoding="utf-8")
        # จุดเรียกจริงเขียนคร่อมหลายบรรทัด — ชื่อ action ไม่ได้อยู่บรรทัดเดียวกับ log_action(
        # จึงมองเป็นหน้าต่างท้ายคำสั่งแทนการอ่านทีละบรรทัด
        for m in call_start.finditer(src):
            window = src[m.end(): m.end() + 400]
            hit = literal.search(window)
            if hit:
                found.add(hit.group(1))
        for line in src.splitlines():
            if "action=" in line or "audit_action" in line:
                found.update(literal.findall(line))
    return found


def test_declared_actions_are_actually_written():
    """
    ทุก action ใน AUDIT_ACTIONS ต้องมีโค้ดเขียนจริงอย่างน้อยหนึ่งที่

    นี่คือทิศที่ตรงกับบั๊กเดิม: ตัวเลือกในตัวกรองที่ไม่มีวันมีข้อมูล
    (เดิมหน้าจอมี auth.login_failed / auth.refresh / content.upload / rbac.denied
    ทั้งที่ backend ไม่เคยเขียนสักตัว)
    """
    sources = "\n".join(p.read_text(encoding="utf-8") for p in _source_files())
    dead = [a for a in audit_service.AUDIT_ACTIONS if f'"{a}"' not in sources]
    assert not dead, f"action เหล่านี้ประกาศไว้แต่ไม่มีโค้ดเขียนจริง (ตัวเลือกตาย): {dead}"


def test_written_actions_are_declared():
    """ทิศกลับกัน — เขียน action ใหม่แล้วลืมประกาศ ตัวกรองหน้าจอจะไม่มีให้เลือก"""
    found = _actions_written_in_code()
    # กันเทสผ่านแบบว่างเปล่าเพราะ regex พัง
    assert len(found) >= 30, f"สแกนเจอ action แค่ {len(found)} ตัว — ตัวสแกนน่าจะพัง"
    undeclared = sorted(found - set(audit_service.AUDIT_ACTIONS))
    assert not undeclared, (
        f"action เหล่านี้ถูกเขียนในโค้ดแต่ไม่ได้ประกาศใน AUDIT_ACTIONS: {undeclared}"
    )


@pytest.mark.asyncio
async def test_audit_actions_endpoint_returns_list(client: AsyncClient, super_admin: User):
    """หน้าจอต้องดึงรายชื่อ action จาก backend ได้ (แทนการ hardcode)"""
    token = await _login(client, super_admin.username)
    res = await client.get(
        "/api/v1/audit/actions", headers={"Authorization": f"Bearer {token}"}
    )
    assert res.status_code == 200, res.text
    actions = res.json()
    assert "user.create" in actions
    assert "content.delete" in actions
    assert "rbac.denied" in actions
    # ของที่เคยเป็นตัวเลือกตายต้องไม่กลับมา
    assert "auth.login_failed" not in actions


# ===== CRUD ต้องถูกบันทึก =====

@pytest.mark.asyncio
async def test_user_create_and_delete_are_audited(
    client: AsyncClient, super_admin: User, db_session: AsyncSession
):
    """สร้างและลบบัญชีผู้ใช้ต้องมีร่องรอยเสมอ (อ่อนไหวสุดในระบบ)"""
    token = await _login(client, super_admin.username)
    headers = {"Authorization": f"Bearer {token}"}

    created = await client.post(
        "/api/v1/users",
        json={
            "username": "audit_target",
            "email": "audit_target@example.com",
            "full_name": "ผู้ใช้ทดสอบ",
            "role": "viewer",
            "password": "testpass123",
        },
        headers=headers,
    )
    assert created.status_code == 201, created.text
    new_id = created.json()["id"]

    deleted = await client.delete(f"/api/v1/users/{new_id}", headers=headers)
    assert deleted.status_code == 204, deleted.text

    actions = await _actions_in_db(db_session)
    assert "user.create" in actions
    assert "user.delete" in actions

    # เนื้อความต้องบอกได้ว่าใครทำอะไรกับใคร
    row = (
        await db_session.execute(
            select(AuditLog).where(AuditLog.action == "user.create")
        )
    ).scalars().first()
    assert row.actor_label == super_admin.username
    assert row.target_id == new_id
    assert "audit_target" in (row.message or "")


@pytest.mark.asyncio
async def test_user_update_does_not_log_password_value(
    client: AsyncClient, super_admin: User, viewer_user: User, db_session: AsyncSession
):
    """แก้ไขผู้ใช้ต้องบันทึกว่า 'ฟิลด์ไหนถูกแก้' แต่ห้ามมีค่ารหัสผ่านโผล่ใน log"""
    token = await _login(client, super_admin.username)
    secret = "SuperSecret999"
    res = await client.patch(
        f"/api/v1/users/{viewer_user.id}",
        json={"password": secret, "full_name": "ชื่อใหม่"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 200, res.text

    row = (
        await db_session.execute(
            select(AuditLog).where(AuditLog.action == "user.update")
        )
    ).scalars().first()
    assert row is not None
    assert "password" in (row.extra or {}).get("fields", [])
    assert secret not in (row.message or "")
    assert secret not in str(row.extra)


@pytest.mark.asyncio
async def test_rbac_denial_is_audited(
    client: AsyncClient, viewer_user: User, db_session: AsyncSession
):
    """ถูกปฏิเสธสิทธิ์ต้องมีร่องรอย พร้อม outcome=denied"""
    token = await _login(client, viewer_user.username)
    res = await client.get(
        "/api/v1/users", headers={"Authorization": f"Bearer {token}"}
    )
    assert res.status_code == 403, res.text

    row = (
        await db_session.execute(
            select(AuditLog).where(AuditLog.action == "rbac.denied")
        )
    ).scalars().first()
    assert row is not None
    assert row.outcome == AuditOutcome.DENIED
    assert row.actor_label == viewer_user.username
    assert "/api/v1/users" in (row.message or "")


@pytest.mark.asyncio
async def test_logout_is_audited(
    client: AsyncClient, super_admin: User, db_session: AsyncSession
):
    """ออกจากระบบต้องถูกบันทึก — เดิมมีแต่ตอนเข้า ไม่มีตอนออก"""
    token = await _login(client, super_admin.username)
    res = await client.post(
        "/api/v1/auth/logout", headers={"Authorization": f"Bearer {token}"}
    )
    assert res.status_code == 204, res.text
    assert "auth.logout" in await _actions_in_db(db_session)
