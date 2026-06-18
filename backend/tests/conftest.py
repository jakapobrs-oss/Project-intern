"""
pytest fixtures — DB ทดสอบใช้ SQLite in-memory (async)
override get_db ของ app เพื่อไม่ต้องพึ่ง postgres ตอน unit test
"""
import asyncio
import uuid
import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import StaticPool

from app.db import Base, get_db
from app.main import app
from app.core.security import hash_password
from app.models.user import User, Role


@pytest.fixture(autouse=True)
def _fresh_middleware_stack():
    """
    Reset middleware stack ก่อนทุก test → rate-limit bucket (in-memory) เริ่มใหม่
    กัน test-isolation: ทุก test ใช้ client IP เดียวกัน ถ้า bucket สะสมข้าม test
    login หลายครั้งจะโดน 429 (ทำให้ KeyError: access_token ใน test อื่น)
    setting middleware_stack=None → Starlette rebuild พร้อม bucket ว่างตอน request แรก
    """
    app.middleware_stack = None
    yield


@pytest_asyncio.fixture
async def db_engine():
    """SQLite in-memory engine ต่อ 1 test"""
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    # patch UUID/Enum ของ Postgres → ใช้ String กับ SQLite
    # (สำหรับ smoke test, Phase 2+ ค่อยใช้ testcontainers + real postgres)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield engine
    await engine.dispose()


@pytest_asyncio.fixture
async def db_session(db_engine) -> AsyncSession:
    """Session factory ต่อ test"""
    SessionLocal = async_sessionmaker(db_engine, expire_on_commit=False)
    async with SessionLocal() as session:
        yield session


@pytest_asyncio.fixture
async def client(db_session) -> AsyncClient:
    """HTTP client พร้อม override get_db"""
    async def _override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = _override_get_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def super_admin(db_session) -> User:
    """User super_admin สำหรับ test (password: 'testpass123')"""
    user = User(
        username="superadmin",
        email="superadmin@example.com",
        full_name="Test Super Admin",
        role=Role.SUPER_ADMIN,
        is_active=True,
        password_hash=hash_password("testpass123"),
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest_asyncio.fixture
async def viewer_user(db_session) -> User:
    """User viewer สำหรับทดสอบ RBAC denial (password: 'testpass123')"""
    user = User(
        username="viewer1",
        email="viewer1@example.com",
        full_name="Test Viewer",
        role=Role.VIEWER,
        is_active=True,
        password_hash=hash_password("testpass123"),
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user
