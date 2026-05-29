"""
ทดสอบ auth flow — login / refresh / me / RBAC denial
"""
import pytest
from httpx import AsyncClient

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


@pytest.mark.asyncio
async def test_account_lockout(client: AsyncClient, super_admin: User):
    """fail login 5 ครั้ง → lock account"""
    for _ in range(5):
        await client.post(
            "/api/v1/auth/login",
            data={"username": super_admin.username, "password": "wrong"},
        )
    # ครั้งที่ 6 ใส่ password ถูก ก็ยัง denied (locked)
    resp = await client.post(
        "/api/v1/auth/login",
        data={"username": super_admin.username, "password": "testpass123"},
    )
    assert resp.status_code == 403
    assert resp.json()["detail"]["code"] == "ACCOUNT_LOCKED"


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
            "email": "new@test.local",
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
            "email": "different@test.local",
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
