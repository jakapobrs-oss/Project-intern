"""
SQLAlchemy 2.x async engine + session factory
ใช้ asyncpg เป็น driver
"""
from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.config import settings

# Engine — pool size ค่า default ของ SQLAlchemy คือ 5 + overflow 10 (พอ dev)
# production จะ tune ผ่าน env ภายหลัง (ดู §27 Reliability)
engine = create_async_engine(
    settings.database_url,
    echo=settings.app_debug,
    pool_pre_ping=True,
)

# Session factory — expire_on_commit=False เพื่อให้ object ใช้ได้หลัง commit
SessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
)


class Base(DeclarativeBase):
    """Base class สำหรับ SQLAlchemy models ทั้งหมด"""
    pass


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    FastAPI dependency — inject DB session ต่อ request
    ใช้แบบ: `async def endpoint(db: AsyncSession = Depends(get_db))`
    """
    async with SessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()
