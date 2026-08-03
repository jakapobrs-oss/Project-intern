# Deployment Guide

## Development (local)

### Requirements
- Docker Desktop หรือ Docker Engine + Compose
- (optional) Node.js 20 + Python 3.12 ถ้าจะรันนอก Docker

### Run
```bash
# 1. คัดลอก .env.example → .env แล้วแก้ค่า (โดยเฉพาะ JWT_SECRET_KEY)
cp .env.example .env

# 2. start ทุก service
docker compose up -d

# 3. รัน DB migration (Phase 1+)
docker compose exec backend alembic upgrade head

# 4. เช็คว่า service พร้อม
curl http://localhost:8000/healthz       # → {"status": "ok"}
curl http://localhost:8000/api/v1/ping   # → {"pong": true}
open http://localhost:3000               # Admin UI
open http://localhost:9001               # MinIO console (minioadmin / minioadmin)
```

### Stop
```bash
docker compose down              # หยุด + ลบ container (data ยังอยู่)
docker compose down -v           # หยุด + ลบ volume ด้วย (เริ่มใหม่หมด)
```

### แก้โค้ด admin-ui แล้วหน้าเว็บไม่เปลี่ยน

Next.js ในคอนเทนเนอร์ไม่ได้รับสัญญาณไฟล์เปลี่ยนจากฝั่ง Windows/macOS (inotify ไม่ข้าม
ระบบไฟล์) → เสิร์ฟหน้าที่คอมไพล์ค้างไว้เดิม ต้อง `docker restart signage_admin_ui`
รายละเอียด: [troubleshooting.md §กับดักตอนพัฒนาบน Docker](troubleshooting.md)

---

## ⚠️ ลำดับการอัปเดตเวอร์ชัน (สำคัญ — ทำผิดลำดับแล้วระบบล่ม)

backend โหลดโค้ดใหม่เองอัตโนมัติ **แต่ migration ไม่ได้รันตาม** ถ้าปล่อยโค้ดใหม่ที่ต้องใช้
คอลัมน์ใหม่ออกไปรับ traffic ก่อน migrate ทุก request ที่แตะตารางนั้นจะตอบ 500
(เจอจริงระหว่างพัฒนา: `column users.locked_until does not exist` → ล็อกอินพังทั้งระบบ)

```bash
# 1. สำรอง DB ก่อนเสมอ (เก็บไว้นอก git — .gitignore กัน /backups/ ไว้แล้ว)
docker exec signage_postgres pg_dump -U signage signage > backups/signage-$(date +%Y%m%d-%H%M).sql

# 2. ดึงโค้ดใหม่ + build image
git pull && docker compose build

# 3. migrate ก่อน   ← ห้ามสลับกับข้อ 4
docker compose run --rm backend alembic upgrade head

# 4. ค่อยปล่อยโค้ดใหม่รับ traffic
docker compose up -d

# 5. ยืนยัน
curl http://localhost:8000/api/v1/readiness   # → {"status":"ready","db":"ok"}
```

**ถ้า migration ตัวใหม่ลบ/เปลี่ยนชนิดคอลัมน์ที่โค้ดเก่ายังใช้อยู่** ต้องแยกเป็น 2 รอบ deploy
(รอบแรกเพิ่มของใหม่ให้โค้ดเก่ายังรันได้ → รอบสองค่อยลบของเก่า) ไม่งั้นช่วงที่ยังปล่อยไม่ครบ
จะมีทั้งโค้ดเก่าและ schema ใหม่อยู่พร้อมกัน

## Production
- ดู §15-§16 ใน PLAN.md สำหรับ cost + server spec แต่ละ tier
- Phase 7 deployment: nginx reverse proxy + Let's Encrypt + systemd / k8s
