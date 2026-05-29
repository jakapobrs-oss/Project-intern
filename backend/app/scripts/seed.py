"""
Seed script — สร้าง super_admin user ตัวแรก
รัน: docker compose exec backend python -m app.scripts.seed

อ่าน admin credential จาก ENV:
- SEED_ADMIN_USERNAME (default: admin)
- SEED_ADMIN_EMAIL    (default: admin@example.com)
- SEED_ADMIN_PASSWORD (default: ChangeMe123!) — ⚠️ เปลี่ยนทันทีหลัง login ครั้งแรก
"""
import asyncio
import os
from sqlalchemy import select

from app.core.security import hash_password
from app.db import SessionLocal
from app.models.user import User, Role


async def seed_admin() -> None:
    username = os.getenv("SEED_ADMIN_USERNAME", "admin")
    email = os.getenv("SEED_ADMIN_EMAIL", "admin@example.com")
    password = os.getenv("SEED_ADMIN_PASSWORD", "ChangeMe123!")

    async with SessionLocal() as db:
        # มี admin อยู่แล้วหรือยัง
        res = await db.execute(select(User).where(User.username == username))
        existing = res.scalar_one_or_none()
        if existing:
            print(f"✓ admin '{username}' มีอยู่แล้ว — skip")
            return

        admin = User(
            username=username,
            email=email,
            full_name="System Administrator",
            role=Role.SUPER_ADMIN,
            is_active=True,
            password_hash=hash_password(password),
        )
        db.add(admin)
        await db.commit()
        print(f"✅ สร้าง super_admin: username='{username}' password='{password}'")
        print("⚠️  เปลี่ยน password ทันทีหลัง login ครั้งแรก!")


if __name__ == "__main__":
    asyncio.run(seed_admin())
