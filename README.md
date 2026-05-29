# 🖥️ Digital Signage Management System

ระบบจัดการจอประชาสัมพันธ์ — ครอบคลุม LAN, HDMI-CEC, RS-232 control + Content/Schedule/Playlist management

> **สถานะ (2026-05-28):** Phase 0–6 + Player polish (F) ✅ — backend + admin UI + Web/Android player พร้อมใช้
> 🗂️ [docs/er-diagram.md](docs/er-diagram.md) — Mermaid ER diagram · [docs/](docs/) — architecture / api / deployment

---

## 📐 Tech Stack

| Layer | Tech | หมายเหตุ |
|---|---|---|
| Backend API | FastAPI 0.115 + Python 3.12 | async, OpenAPI auto-doc |
| ORM / Migration | SQLAlchemy 2.x async + Alembic | |
| Database | PostgreSQL 16 | |
| Cache / Queue | Redis 7 | broker ของ Arq |
| Worker | Arq | background jobs (§37) |
| Object Storage | MinIO (S3-compatible) | self-host ฟรี |
| Admin UI | Next.js 14 + TypeScript | |
| Player | Android (Kotlin) + PWA kiosk | USB-Serial bridge — FTDI/CP210x/CH340/PL2303 (§36) |
| TV Control | libcec + pyserial | HDMI-CEC + RS-232 |
| Deploy | Docker Compose (dev) → systemd / k8s (prod) | |

ทุกตัวเป็น **OSS / ฟรี** ตามกฎข้อ 1 ✅

---

## 🚀 Quick Start

### Option A — One-command E2E (recommended)
```bash
bash scripts/run-e2e.sh         # Linux/macOS
.\scripts\run-e2e.ps1           # Windows
```
Script จะ: build + start + รอ healthy + pytest + smoke_e2e + แสดง URL ให้ทุก service

### Option B — Manual
```bash
cp .env.example .env             # แก้ JWT_SECRET_KEY ก่อน production
docker compose up -d --build     # auto-migrate + auto-seed admin

# ตรวจสอบ
curl http://localhost:8000/healthz                 # liveness
curl http://localhost:8000/api/v1/readiness        # readiness (DB OK)
open http://localhost:8000/api/docs                # Swagger UI
open http://localhost:3000                         # Admin UI (login: admin/ChangeMe123!)
open http://localhost:9001                         # MinIO console (minioadmin/minioadmin)
```

### Option C — Demo data (เห็น flow ทันที)
```bash
docker compose exec backend python -m app.scripts.seed_demo
# สร้าง 3 device + 1 group + 2 content + 1 presentation + 1 plan + 1 schedule active
# + editor1/approver1/operator1 users สำหรับทดสอบ RBAC
```

ดูเพิ่ม: **[docs/production-deployment.md](docs/production-deployment.md)** (production guide + secret rotation) · [docs/deployment.md](docs/deployment.md)

---

## 📁 โครงสร้าง

```
Project-intern/
├── docker-compose.yml          ← dev stack: postgres + redis + minio + backend + worker + admin-ui
├── .env.example                ← template — copy เป็น .env
├── README.md                   ← ไฟล์นี้
│
├── backend/                    ← FastAPI
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── pyproject.toml          ← ruff + mypy + pytest config
│   ├── alembic.ini
│   ├── alembic/
│   │   ├── env.py              ← async migration
│   │   └── versions/           ← migration files (ว่างใน Phase 0)
│   ├── app/
│   │   ├── main.py             ← FastAPI entry
│   │   ├── config.py           ← Pydantic Settings
│   │   ├── db.py               ← SQLAlchemy engine + session
│   │   ├── worker.py           ← Arq worker entry
│   │   ├── api/v1/             ← API routes
│   │   ├── models/             ← SQLAlchemy ORM (Phase 1+)
│   │   ├── schemas/            ← Pydantic request/response (Phase 1+)
│   │   └── services/           ← Business logic (Phase 1+)
│   └── tests/
│       └── test_health.py      ← smoke test
│
├── admin-ui/                   ← Next.js 14
│   ├── Dockerfile
│   ├── package.json
│   ├── tsconfig.json
│   ├── next.config.mjs
│   └── src/app/
│       ├── layout.tsx
│       └── page.tsx
│
├── player/                     ← Player apps (Phase 3+)
│   ├── android/                ← Kotlin (USB-Serial bridge §36)
│   └── web/                    ← PWA kiosk mode
│
├── tv-control/                 ← HDMI-CEC + RS-232 service (Phase 4+)
│
└── docs/
    ├── architecture.md
    ├── api.md
    └── deployment.md
```

---

## ✅ Phase ที่จบแล้ว

| Phase | Done | สรุป |
|---|---|---|
| 0 — Scaffolding | ✅ | docker-compose + skeleton services |
| 1 — Auth & Users | ✅ | JWT + RBAC 7 roles + 14 tests |
| 2 — Devices & Contents | ✅ | Pairing + S3 upload + dedupe + approval |
| 3 — Plans + Schedules + Manifest | ✅ | 5-tier hierarchy + RRULE + priority |
| 4 — TV Control | ✅ | 6 brand protocols + Redis queue + Web Serial / USB-Serial |
| 5 — Emergency + Monitoring | ✅ | Override + auto-expire + Prometheus + audit + Sentry + backup |
| 6 — Admin UI | ✅ | 11 pages (Next.js + Tailwind) + auth flow + drag-drop + composer |
| F — Player polish | ✅ | Zone renderer + plan carousel + emergency overlay + backoff + LRU |

## ⏭️ Next: Option E run / Phase 7 deploy hardening
- รันใน environment user: `bash scripts/run-e2e.sh`
- Phase 7: HDMI-CEC native, httpOnly cookie, i18n, CI/CD, hardening

---

## ⚠️ Defaults ใช้ใน Phase 0 (รอ user confirm)

ตามคำสั่ง "เริ่มทำได้เลย" ใช้ default ที่สมเหตุสมผลก่อน — ถ้าต้องเปลี่ยน แจ้งได้:

| คำถาม | Default ที่ใช้ |
|---|---|
| จำนวนจอ (§12.1) | 10-20 (POC scale) |
| TV brand (§12.2) | Samsung MDC + LG (รองรับทั้ง 5 ผ่าน enum) |
| LED board (§12.3) | ยังไม่ scaffold (รอ spec) |
| Deploy (§12.4) | On-premise Linux + Docker |
| Hardware POC (§12.5) | code-first, ยังไม่ต้องมี hardware |
| Timeline (§12.6) | ~8 สัปดาห์ |
| OS server (§12.7) | Ubuntu 22.04 LTS |
| Presentation layer (§38) | **เอา** (5-tier hierarchy) |
| Manifest pattern (§38) | **เอา** (offline-friendly) |
| Reuse Kotlin RS-232 (§38) | **เอา** (copy เข้า player/android Phase 3) |
| Data migration (§39) | **ไม่ต้อง** (greenfield) |
