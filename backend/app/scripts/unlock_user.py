"""
Unlock script — ปลดล็อกบัญชีผู้ใช้แบบฉุกเฉิน (§26)

รัน: docker compose exec backend python -m app.scripts.unlock_user <username|email>
     python -m app.scripts.unlock_user --list        # ดูว่าใครถูกล็อกอยู่บ้าง

ใช้เมื่อไหร่:
- ปกติ **ไม่ต้องใช้** เพราะการกรอกรหัสผิดเกินกำหนดล็อกแค่ชั่วคราว ครบเวลาแล้วปลดเอง
  และ admin ปลดให้กันได้จากหน้าจัดการผู้ใช้
- เคสที่ต้องใช้จริง: บัญชีถูก admin สั่งล็อกด้วยมือ (is_locked) แล้วบัญชีนั้นคือ
  super_admin คนเดียวของระบบ → ไม่มีใครเหลือให้ปลดผ่านหน้าจอ

ความปลอดภัย: สคริปต์นี้ต้องรันบนเครื่องที่ต่อฐานข้อมูลได้เท่านั้น (เข้า shell ของ
เซิร์ฟเวอร์/คอนเทนเนอร์ได้) — ไม่ได้เปิดเป็น API จึงไม่เพิ่มช่องโจมตีจากภายนอก
"""
import asyncio
import sys
from sqlalchemy import or_, select

from app.db import SessionLocal
from app.models.user import User


async def list_locked() -> int:
    """แสดงบัญชีที่ถูกล็อกอยู่ (ทั้งแบบ admin สั่ง และแบบชั่วคราว)"""
    async with SessionLocal() as db:
        res = await db.execute(
            select(User).where(or_(User.is_locked.is_(True), User.locked_until.isnot(None)))
        )
        users = res.scalars().all()
        if not users:
            print("ไม่มีบัญชีที่ถูกล็อก")
            return 0
        print(f"บัญชีที่ถูกล็อก {len(users)} รายการ:")
        for u in users:
            # โดนได้ทั้ง 2 แบบพร้อมกัน — เครื่องมือวินิจฉัยต้องบอกครบ ไม่งั้นปลดแล้วงงว่าทำไมยังเข้าไม่ได้
            kinds = []
            if u.is_locked:
                kinds.append("admin สั่งล็อก")
            if u.locked_until is not None:
                kinds.append(f"ล็อกชั่วคราวถึง {u.locked_until}")
            print(f"  - {u.username} ({u.role.value}) — {' + '.join(kinds)}")
        return 0


async def unlock(identifier: str) -> int:
    """ปลดล็อกบัญชีเดียวตาม username หรือ email"""
    async with SessionLocal() as db:
        res = await db.execute(
            select(User).where(or_(User.username == identifier, User.email == identifier))
        )
        user = res.scalar_one_or_none()
        if user is None:
            print(f"ไม่พบผู้ใช้ '{identifier}'")
            return 1

        if not user.is_locked and user.locked_until is None and user.failed_login_count == 0:
            print(f"'{user.username}' ไม่ได้ถูกล็อกอยู่แล้ว — ไม่ต้องทำอะไร")
            return 0

        user.is_locked = False
        user.locked_until = None
        user.failed_login_count = 0
        await db.commit()
        print(f"ปลดล็อก '{user.username}' ({user.role.value}) เรียบร้อย")
        return 0


def main() -> int:
    args = sys.argv[1:]
    if not args or args[0] in ("-h", "--help"):
        print(__doc__)
        return 0 if args else 1
    if args[0] == "--list":
        return asyncio.run(list_locked())
    return asyncio.run(unlock(args[0]))


if __name__ == "__main__":
    raise SystemExit(main())
