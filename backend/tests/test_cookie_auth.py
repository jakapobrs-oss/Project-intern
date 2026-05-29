"""
Phase 7 — httpOnly cookie auth tests

ตรวจ:
  - login set cookies + คืน JSON
  - /me อ่าน cookie ได้ (ไม่มี Authorization header)
  - /me อ่าน Authorization header ได้ (cookie ไม่มี)
  - refresh จาก cookie (body ว่าง)
  - logout ลบ cookies
  - /csrf endpoint คืน token + cookie
"""
import pytest


async def _login_and_get_cookies(client, username, password="testpass123"):
    """login + return (response, cookies dict)"""
    res = await client.post(
        "/api/v1/auth/login",
        data={"username": username, "password": password},
    )
    assert res.status_code == 200, res.text
    return res, dict(res.cookies)


# ─── Login cookie set ───────────────────────────────────────────────

@pytest.mark.asyncio
async def test_login_sets_httponly_cookies(client, super_admin):
    res, cookies = await _login_and_get_cookies(client, "superadmin")
    assert "signage_access_token" in cookies
    assert "signage_refresh_token" in cookies
    # JSON body มี tokens ด้วย (backward compat)
    body = res.json()
    assert body["access_token"] == cookies["signage_access_token"]
    assert body["refresh_token"] == cookies["signage_refresh_token"]


# ─── /me ผ่าน cookie ────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_me_via_cookie_only(client, super_admin):
    await _login_and_get_cookies(client, "superadmin")
    # client เก็บ cookies เอง — ไม่ใส่ Authorization
    res = await client.get("/api/v1/auth/me")
    assert res.status_code == 200, res.text
    assert res.json()["username"] == "superadmin"


@pytest.mark.asyncio
async def test_me_via_authorization_header(client, super_admin):
    """Bearer mode ต้องยังใช้ได้ — ไม่ระบุ cookies"""
    login_res = await client.post(
        "/api/v1/auth/login",
        data={"username": "superadmin", "password": "testpass123"},
    )
    token = login_res.json()["access_token"]

    # ลบ cookies ออกจาก client เพื่อยืนยันว่า header ทำงานเอง
    client.cookies.clear()
    res = await client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert res.status_code == 200
    assert res.json()["username"] == "superadmin"


@pytest.mark.asyncio
async def test_me_without_token_returns_401(client):
    res = await client.get("/api/v1/auth/me")
    assert res.status_code == 401


# ─── Refresh จาก cookie ─────────────────────────────────────────────

@pytest.mark.asyncio
async def test_refresh_via_cookie_with_empty_body(client, super_admin):
    """refresh ที่ส่ง body ว่าง → อ่าน refresh จาก cookie"""
    await _login_and_get_cookies(client, "superadmin")
    res = await client.post("/api/v1/auth/refresh", json={})
    assert res.status_code == 200, res.text
    new_body = res.json()
    assert "access_token" in new_body
    # cookies ต้อง rotate ด้วย
    assert "signage_access_token" in dict(res.cookies)


@pytest.mark.asyncio
async def test_refresh_via_body_still_works(client, super_admin):
    """Bearer mode: ส่ง refresh_token ใน JSON body"""
    login_res = await client.post(
        "/api/v1/auth/login",
        data={"username": "superadmin", "password": "testpass123"},
    )
    refresh = login_res.json()["refresh_token"]
    client.cookies.clear()
    res = await client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": refresh},
    )
    assert res.status_code == 200


@pytest.mark.asyncio
async def test_refresh_without_token_returns_401(client):
    res = await client.post("/api/v1/auth/refresh", json={})
    assert res.status_code == 401


# ─── Logout clear cookies ───────────────────────────────────────────

@pytest.mark.asyncio
async def test_logout_clears_cookies(client, super_admin):
    await _login_and_get_cookies(client, "superadmin")
    res = await client.post("/api/v1/auth/logout")
    assert res.status_code == 204
    # หลัง logout เรียก /me ควร 401
    client.cookies.clear()
    res = await client.get("/api/v1/auth/me")
    assert res.status_code == 401


# ─── CSRF endpoint ──────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_csrf_endpoint_returns_token_and_cookie(client):
    res = await client.get("/api/v1/auth/csrf")
    assert res.status_code == 200
    body = res.json()
    assert "csrf_token" in body
    # cookie ต้องถูก set ด้วย ค่าตรงกับ body
    cookie_val = res.cookies.get("csrf_token")
    assert cookie_val == body["csrf_token"]


@pytest.mark.asyncio
async def test_csrf_endpoint_idempotent(client):
    """เรียก /csrf ซ้ำ → คืน token เดิม (อ่านจาก cookie ก่อน)"""
    res1 = await client.get("/api/v1/auth/csrf")
    res2 = await client.get("/api/v1/auth/csrf")
    assert res1.json()["csrf_token"] == res2.json()["csrf_token"]
