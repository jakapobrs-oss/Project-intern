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

## Production
- ดู §15-§16 ใน PLAN.md สำหรับ cost + server spec แต่ละ tier
- Phase 7 deployment: nginx reverse proxy + Let's Encrypt + systemd / k8s
