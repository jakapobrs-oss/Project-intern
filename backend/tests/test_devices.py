"""
ทดสอบ device + pairing flow
"""
import pytest
from httpx import AsyncClient

from app.models.user import User


@pytest.mark.asyncio
async def test_device_create_generates_pairing_code(client: AsyncClient, super_admin: User):
    login = await client.post(
        "/api/v1/auth/login",
        data={"username": super_admin.username, "password": "testpass123"},
    )
    access = login.json()["access_token"]
    resp = await client.post(
        "/api/v1/devices",
        headers={"Authorization": f"Bearer {access}"},
        json={"name": "Lobby TV", "location": "1F lobby"},
    )
    assert resp.status_code == 201, resp.text
    data = resp.json()
    assert data["name"] == "Lobby TV"
    assert data["pairing_code"] is not None
    assert len(data["pairing_code"]) == 6
    assert data["status"] == "unpaired"


@pytest.mark.asyncio
async def test_player_pair_flow(client: AsyncClient, super_admin: User):
    """admin สร้าง device → player claim ด้วย code → ได้ device_token"""
    # 1. admin สร้าง device
    login = await client.post(
        "/api/v1/auth/login",
        data={"username": super_admin.username, "password": "testpass123"},
    )
    access = login.json()["access_token"]
    create = await client.post(
        "/api/v1/devices",
        headers={"Authorization": f"Bearer {access}"},
        json={"name": "Test Device", "platform": "android_tv"},
    )
    device_data = create.json()
    pairing_code = device_data["pairing_code"]

    # 2. player claim
    pair = await client.post(
        "/api/v1/player/pair",
        json={
            "pairing_code": pairing_code,
            "platform": "android_tv",
            "mac_address": "AA:BB:CC:DD:EE:FF",
            "app_version": "0.1.0",
        },
    )
    assert pair.status_code == 200, pair.text
    pair_data = pair.json()
    assert "device_token" in pair_data
    assert pair_data["device_id"] == device_data["id"]

    # 3. ใช้ device token เรียก /player/me
    token = pair_data["device_token"]
    me = await client.get("/api/v1/player/me", headers={"Authorization": f"Bearer {token}"})
    assert me.status_code == 200
    assert me.json()["status"] == "online"


@pytest.mark.asyncio
async def test_player_pair_invalid_code(client: AsyncClient):
    resp = await client.post(
        "/api/v1/player/pair",
        json={"pairing_code": "INVALID", "platform": "unknown"},
    )
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_heartbeat_updates_device(client: AsyncClient, super_admin: User):
    # setup: create + pair
    login = await client.post(
        "/api/v1/auth/login",
        data={"username": super_admin.username, "password": "testpass123"},
    )
    access = login.json()["access_token"]
    create = await client.post(
        "/api/v1/devices",
        headers={"Authorization": f"Bearer {access}"},
        json={"name": "HBDev"},
    )
    code = create.json()["pairing_code"]
    pair = await client.post(
        "/api/v1/player/pair",
        json={"pairing_code": code, "platform": "rpi_kiosk"},
    )
    token = pair.json()["device_token"]

    # send heartbeat
    hb = await client.post(
        "/api/v1/player/heartbeat",
        headers={"Authorization": f"Bearer {token}"},
        json={"status": "online", "cpu_percent": 12.3, "temperature_c": 42.0, "uptime_sec": 100},
    )
    assert hb.status_code == 200, hb.text
    data = hb.json()
    assert "server_time" in data
    assert "manifest_outdated" in data


@pytest.mark.asyncio
async def test_player_group_with_devices(client: AsyncClient, super_admin: User):
    """สร้าง group + ผูก device + อัปเดต member"""
    login = await client.post(
        "/api/v1/auth/login",
        data={"username": super_admin.username, "password": "testpass123"},
    )
    access = login.json()["access_token"]
    headers = {"Authorization": f"Bearer {access}"}

    # devices 2 ตัว
    d1 = (await client.post("/api/v1/devices", headers=headers, json={"name": "D1"})).json()
    d2 = (await client.post("/api/v1/devices", headers=headers, json={"name": "D2"})).json()

    # group ที่มี d1
    g = await client.post(
        "/api/v1/groups",
        headers=headers,
        json={"name": "Lobby Group", "device_ids": [d1["id"]]},
    )
    assert g.status_code == 201, g.text
    assert d1["id"] in g.json()["device_ids"]

    # update เพิ่ม d2
    upd = await client.patch(
        f"/api/v1/groups/{g.json()['id']}",
        headers=headers,
        json={"device_ids": [d1["id"], d2["id"]]},
    )
    assert upd.status_code == 200
    assert set(upd.json()["device_ids"]) == {d1["id"], d2["id"]}
