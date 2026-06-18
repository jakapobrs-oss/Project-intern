"""
Smoke test ของ Phase 0 — เช็คว่า app start ได้และ /healthz ตอบ 200
รันด้วย: pytest backend/tests/ -v
"""
import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app


@pytest.mark.asyncio
async def test_healthz():
    """healthz endpoint ต้อง return 200 + status ok"""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.get("/healthz")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


@pytest.mark.asyncio
async def test_root():
    """root endpoint คืน app info"""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.get("/")
    assert resp.status_code == 200
    data = resp.json()
    assert data["name"] == "Digital Signage Management API"
    assert "version" in data


@pytest.mark.asyncio
async def test_api_ping():
    """API v1 ping endpoint"""
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.get("/api/v1/ping")
    assert resp.status_code == 200
    assert resp.json() == {"pong": True}
