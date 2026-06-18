"""
Shared async DB session สำหรับ background worker

worker ไม่มี FastAPI request lifecycle เลยต้องสร้าง engine/sessionmaker
ที่ระดับ module (lazy init เพื่อ test mock ได้ + ไม่กิน resource ตอน import)
"""
from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.config import settings

_engine = None
_sessionmaker: async_sessionmaker[AsyncSession] | None = None


def get_sessionmaker() -> async_sessionmaker[AsyncSession]:
    global _engine, _sessionmaker
    if _sessionmaker is None:
        _engine = create_async_engine(settings.database_url, pool_pre_ping=True, future=True)
        _sessionmaker = async_sessionmaker(_engine, expire_on_commit=False)
    return _sessionmaker
