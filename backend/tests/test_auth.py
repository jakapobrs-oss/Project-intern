"""
ทดสอบ auth flow — login / refresh / me / RBAC denial
"""
from datetime import datetime, timedelta, timezone

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User, Role


# ===== Login =====

@pytest.mark.asyncio
async def test_login_success(client: AsyncClient, super_admin: User):
    """login สำเร็จ → ได้ access + refresh token"""
    resp = await client.post(
        "/api/v1/auth/login",
        data={"username": super_admin.username, "password": "testpass123"},
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["token_type"] == "bearer"
    assert data["expires_in"] > 0


@pytest.mark.asyncio
async def test_login_with_email(client: AsyncClient, super_admin: User):
    """รับ email แทน username ก็ login ได้"""
    resp = await client.post(
        "/api/v1/auth/login",
        data={"username": super_admin.email, "password": "testpass123"},
    )
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_login_wrong_password(client: AsyncClient, super_admin: User):
    """password ผิด → 401"""
    resp = await client.post(
        "/api/v1/auth/login",
        data={"username": super_admin.username, "password": "wrong"},
    )
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_login_unknown_user(client: AsyncClient):
    """user ไม่มี → 401 (ไม่บอก enumeration)"""
    resp = await client.post(
        "/api/v1/auth/login",
        data={"username": "nobody", "password": "whatever"},
    )
    assert resp.status_code == 401


async def _fail_login_until_locked(client: AsyncClient, username: str, times: int = 5):
    """กรอกรหัสผิดซ้ำ ๆ จนบัญชีโดนล็อก แล้วคืน response ครั้งสุดท้าย"""
    resp = None
    for _ in range(times):
        resp = await client.post(
            "/api/v1/auth/login",
            data={"username": username, "password": "wrong"},
        )
    return resp


@pytest.mark.asyncio
async def test_account_lockout_is_temporary(
    client: AsyncClient, super_admin: User, db_session: AsyncSession
):
    """กรอกรหัสผิด 5 ครั้ง → ล็อก 'ชั่วคราว' (ไม่ใช่ถาวร) และรหัสถูกก็ยังเข้าไม่ได้ระหว่างล็อก"""
    last = await _fail_login_until_locked(client, super_admin.username)
    assert last.status_code == 403
    assert last.json()["detail"]["code"] == "ACCOUNT_LOCKED_TEMP"

    resp = await client.post(
        "/api/v1/auth/login",
        data={"username": super_admin.username, "password": "testpass123"},
    )
    assert resp.status_code == 403
    assert resp.json()["detail"]["code"] == "ACCOUNT_LOCKED_TEMP"

    # ต้องไม่แตะ is_locked (ช่องนั้นสงวนไว้ให้ admin สั่งล็อกด้วยมือเท่านั้น)
    await db_session.refresh(super_admin)
    assert super_admin.is_locked is False
    assert super_admin.locked_until is not None


@pytest.mark.asyncio
async def test_lockout_expires_by_itself(
    client: AsyncClient, super_admin: User, db_session: AsyncSession
):
    """ครบเวลาแล้วปลดเอง — ไม่ต้องมี admin มาปลด (นี่คือจุดที่กันไม่ให้ super_admin ล็อกตัวเองตาย)"""
    await _fail_login_until_locked(client, super_admin.username)

    # เร่งเวลา: ย้อน locked_until ไปเป็นอดีต แทนการรอจริง 15 นาที
    super_admin.locked_until = datetime.now(timezone.utc) - timedelta(seconds=1)
    await db_session.commit()

    resp = await client.post(
        "/api/v1/auth/login",
        data={"username": super_admin.username, "password": "testpass123"},
    )
    assert resp.status_code == 200, resp.text
    await db_session.refresh(super_admin)
    assert super_admin.locked_until is None
    assert super_admin.failed_login_count == 0


@pytest.mark.asyncio
async def test_admin_lock_is_separate_and_permanent(
    client: AsyncClient, super_admin: User, db_session: AsyncSession
):
    """is_locked (admin สั่งล็อก) ยังบล็อกถาวรเหมือนเดิม และแยก error code ออกจากล็อกชั่วคราว"""
    super_admin.is_locked = True
    await db_session.commit()

    resp = await client.post(
        "/api/v1/auth/login",
        data={"username": super_admin.username, "password": "testpass123"},
    )
    assert resp.status_code == 403
    assert resp.json()["detail"]["code"] == "ACCOUNT_LOCKED"


@pytest.mark.asyncio
async def test_temp_lockout_does_not_kill_active_session(
    client: AsyncClient, super_admin: User, db_session: AsyncSession
):
    """
    ล็อกชั่วคราวต้องไม่เตะ session ที่ล็อกอินอยู่แล้ว

    ถ้าเตะ = ใครก็ตามที่รู้ชื่อผู้ใช้เรา กรอกรหัสผิด 5 ครั้งก็ไล่เราออกจากระบบกลางคันได้
    """
    login = await client.post(
        "/api/v1/auth/login",
        data={"username": super_admin.username, "password": "testpass123"},
    )
    token = login.json()["access_token"]

    await _fail_login_until_locked(client, super_admin.username)

    # เฉพาะในเทส: แอปกับเทสใช้ session เดียวกัน (conftest override get_db) พอ UPDATE
    # ไปโดน updated_at ที่คำนวณฝั่ง SQL ค่าในหน่วยความจำจะถูกทำเป็นหมดอายุ แล้วตอนแปลง
    # เป็น JSON จะไปโหลดค่าใหม่กลางทาง async ไม่ได้ — ของจริงแต่ละ request แยก session
    # จึงโหลด user สดทุกครั้ง ไม่เจอเคสนี้
    await db_session.refresh(super_admin)

    me = await client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me.status_code == 200, me.text


@pytest.mark.asyncio
async def test_admin_can_unlock_through_api(
    client: AsyncClient, super_admin: User, viewer_user: User, db_session: AsyncSession
):
    """
    ปุ่มปลดล็อกในหน้าจัดการผู้ใช้ต้องมีผลจริง

    บั๊กเดิม: UserUpdate ไม่ประกาศ is_locked → Pydantic ทิ้งฟิลด์เงียบ ๆ
    API ตอบ 200 แต่บัญชียังล็อกอยู่ ปลดได้ทางเดียวคือแก้ฐานข้อมูลตรง ๆ
    """
    viewer_user.is_locked = True
    viewer_user.locked_until = datetime.now(timezone.utc) + timedelta(minutes=15)
    await db_session.commit()

    login = await client.post(
        "/api/v1/auth/login",
        data={"username": super_admin.username, "password": "testpass123"},
    )
    token = login.json()["access_token"]

    resp = await client.patch(
        f"/api/v1/users/{viewer_user.id}",
        json={"is_locked": False},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["is_locked"] is False
    # ปลดล็อกด้วยมือต้องล้างล็อกชั่วคราวด้วย ไม่งั้นปลดแล้วยังเข้าไม่ได้จนกว่าจะครบเวลา
    assert resp.json()["locked_until"] is None

    resp = await client.post(
        "/api/v1/auth/login",
        data={"username": viewer_user.username, "password": "testpass123"},
    )
    assert resp.status_code == 200, resp.text


# ===== /me =====

@pytest.mark.asyncio
async def test_me_with_valid_token(client: AsyncClient, super_admin: User):
    login = await client.post(
        "/api/v1/auth/login",
        data={"username": super_admin.username, "password": "testpass123"},
    )
    access = login.json()["access_token"]
    resp = await client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {access}"})
    assert resp.status_code == 200
    assert resp.json()["username"] == super_admin.username
    assert resp.json()["role"] == "super_admin"


@pytest.mark.asyncio
async def test_me_no_token(client: AsyncClient):
    resp = await client.get("/api/v1/auth/me")
    assert resp.status_code == 401


@pytest.mark.asyncio
async def test_me_invalid_token(client: AsyncClient):
    resp = await client.get(
        "/api/v1/auth/me",
        headers={"Authorization": "Bearer not.a.real.jwt"},
    )
    assert resp.status_code == 401


# ===== Refresh =====

@pytest.mark.asyncio
async def test_refresh_rotates_tokens(client: AsyncClient, super_admin: User):
    """refresh → access + refresh ใหม่ (rotate)"""
    login = await client.post(
        "/api/v1/auth/login",
        data={"username": super_admin.username, "password": "testpass123"},
    )
    old_refresh = login.json()["refresh_token"]

    resp = await client.post("/api/v1/auth/refresh", json={"refresh_token": old_refresh})
    assert resp.status_code == 200
    new_data = resp.json()
    assert new_data["access_token"] != login.json()["access_token"]
    assert new_data["refresh_token"] != old_refresh


@pytest.mark.asyncio
async def test_refresh_with_access_token_rejected(client: AsyncClient, super_admin: User):
    """ส่ง access token ไป refresh → ปฏิเสธ (ต้องเป็น refresh type)"""
    login = await client.post(
        "/api/v1/auth/login",
        data={"username": super_admin.username, "password": "testpass123"},
    )
    access = login.json()["access_token"]
    resp = await client.post("/api/v1/auth/refresh", json={"refresh_token": access})
    assert resp.status_code == 401


# ===== RBAC =====

@pytest.mark.asyncio
async def test_viewer_cannot_list_users(client: AsyncClient, viewer_user: User):
    """viewer ไม่มีสิทธิ์ user CRUD"""
    login = await client.post(
        "/api/v1/auth/login",
        data={"username": viewer_user.username, "password": "testpass123"},
    )
    access = login.json()["access_token"]
    resp = await client.get("/api/v1/users", headers={"Authorization": f"Bearer {access}"})
    assert resp.status_code == 403


@pytest.mark.asyncio
async def test_super_admin_can_list_users(client: AsyncClient, super_admin: User):
    login = await client.post(
        "/api/v1/auth/login",
        data={"username": super_admin.username, "password": "testpass123"},
    )
    access = login.json()["access_token"]
    resp = await client.get("/api/v1/users", headers={"Authorization": f"Bearer {access}"})
    assert resp.status_code == 200
    assert len(resp.json()) >= 1


@pytest.mark.asyncio
async def test_super_admin_create_user(client: AsyncClient, super_admin: User):
    login = await client.post(
        "/api/v1/auth/login",
        data={"username": super_admin.username, "password": "testpass123"},
    )
    access = login.json()["access_token"]
    resp = await client.post(
        "/api/v1/users",
        headers={"Authorization": f"Bearer {access}"},
        json={
            "username": "newuser",
            "email": "new@example.com",
            "password": "Newpass123",
            "role": "editor",
            "full_name": "New User",
        },
    )
    assert resp.status_code == 201, resp.text
    data = resp.json()
    assert data["username"] == "newuser"
    assert data["role"] == "editor"
    assert "password" not in data


@pytest.mark.asyncio
async def test_create_user_duplicate(client: AsyncClient, super_admin: User):
    """username ซ้ำ → 409"""
    login = await client.post(
        "/api/v1/auth/login",
        data={"username": super_admin.username, "password": "testpass123"},
    )
    access = login.json()["access_token"]
    resp = await client.post(
        "/api/v1/users",
        headers={"Authorization": f"Bearer {access}"},
        json={
            "username": super_admin.username,  # ซ้ำ
            "email": "different@example.com",
            "password": "Pass1234",
            "role": "viewer",
        },
    )
    assert resp.status_code == 409


@pytest.mark.asyncio
async def test_cannot_delete_self(client: AsyncClient, super_admin: User):
    login = await client.post(
        "/api/v1/auth/login",
        data={"username": super_admin.username, "password": "testpass123"},
    )
    access = login.json()["access_token"]
    resp = await client.delete(
        f"/api/v1/users/{super_admin.id}",
        headers={"Authorization": f"Bearer {access}"},
    )
    assert resp.status_code == 400
