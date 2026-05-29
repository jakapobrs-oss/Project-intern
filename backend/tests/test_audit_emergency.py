"""
Phase 5 tests: audit log + emergency broadcast + /metrics
"""
import pytest
from sqlalchemy import select

from app.models.audit import AuditLog, AuditOutcome
from app.models.emergency import EmergencyBroadcast, EmergencyStatus


async def _login(client, username: str, password: str = "testpass123") -> str:
    res = await client.post(
        "/api/v1/auth/login",
        data={"username": username, "password": password},
    )
    assert res.status_code == 200, res.text
    return res.json()["access_token"]


# ----- AUDIT -----

@pytest.mark.asyncio
async def test_login_success_writes_audit(client, db_session, super_admin):
    await _login(client, "superadmin")
    rows = (await db_session.execute(
        select(AuditLog).where(AuditLog.action == "auth.login")
    )).scalars().all()
    assert any(r.outcome == AuditOutcome.SUCCESS for r in rows)


@pytest.mark.asyncio
async def test_login_fail_writes_audit(client, db_session, super_admin):
    res = await client.post(
        "/api/v1/auth/login",
        data={"username": "superadmin", "password": "WRONG"},
    )
    assert res.status_code == 401
    rows = (await db_session.execute(
        select(AuditLog).where(AuditLog.action == "auth.login")
    )).scalars().all()
    assert any(r.outcome == AuditOutcome.FAIL for r in rows)


@pytest.mark.asyncio
async def test_audit_list_requires_admin(client, super_admin, viewer_user):
    # viewer denied
    token = await _login(client, "viewer1")
    res = await client.get(
        "/api/v1/audit/logs",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 403

    # super_admin allowed
    token2 = await _login(client, "superadmin")
    res = await client.get(
        "/api/v1/audit/logs",
        headers={"Authorization": f"Bearer {token2}"},
    )
    assert res.status_code == 200
    assert isinstance(res.json(), list)


# ----- EMERGENCY -----

@pytest.mark.asyncio
async def test_emergency_create_activate_cancel_flow(client, db_session, super_admin):
    token = await _login(client, "superadmin")
    headers = {"Authorization": f"Bearer {token}"}

    # create
    res = await client.post(
        "/api/v1/emergency/",
        headers=headers,
        json={
            "title": "ทดสอบแจ้งเตือนฉุกเฉิน",
            "kind": "text",
            "payload": {"message": "เกิดเหตุไฟไหม้ กรุณาอพยพ"},
            "target": {"all": True},
            "priority": 2000,
        },
    )
    assert res.status_code == 201, res.text
    bid = res.json()["id"]
    assert res.json()["status"] == "draft"

    # activate
    res = await client.post(f"/api/v1/emergency/{bid}/activate", headers=headers)
    assert res.status_code == 200
    assert res.json()["status"] == "active"
    assert res.json()["acknowledged_at"] is not None

    # activate twice → 409
    res = await client.post(f"/api/v1/emergency/{bid}/activate", headers=headers)
    assert res.status_code == 409

    # cancel
    res = await client.post(f"/api/v1/emergency/{bid}/cancel", headers=headers)
    assert res.status_code == 200
    assert res.json()["status"] == "cancelled"

    # audit trail บันทึก create + activate + cancel
    rows = (await db_session.execute(
        select(AuditLog).where(AuditLog.target_id == bid)
    )).scalars().all()
    actions = {r.action for r in rows}
    assert {"emergency.create", "emergency.activate", "emergency.cancel"} <= actions


@pytest.mark.asyncio
async def test_emergency_viewer_denied(client, viewer_user):
    token = await _login(client, "viewer1")
    res = await client.post(
        "/api/v1/emergency/",
        headers={"Authorization": f"Bearer {token}"},
        json={"title": "x", "kind": "text", "payload": {}, "target": {"all": True}},
    )
    assert res.status_code == 403


# ----- METRICS -----

@pytest.mark.asyncio
async def test_metrics_endpoint_returns_prometheus_text(client):
    res = await client.get("/api/v1/metrics")
    assert res.status_code == 200
    body = res.text
    assert "signage_devices_total" in body
    assert "# TYPE signage_devices_total gauge" in body
    assert "signage_emergency_active" in body
