# CLAUDE.md — Project-intern

> File roadmap สร้างจากการสำรวจจริง 2026-07-13 (Explore agent อ่านตรง filesystem)
> เป้าหมาย: ให้ session ใหม่หาของถูกจุดทันที ไม่ต้อง grep/read มั่วทั้ง repo — **อ่านไฟล์นี้ก่อนเริ่มสำรวจเสมอ**

**แก้ความเข้าใจเดิม**: นี่ไม่ใช่ "hospital intern template" ทั่วไป แต่คือ **ระบบจัดการจอประชาสัมพันธ์ (Digital Signage Management System)** สำหรับโรงพยาบาล — ควบคุมจอทีวี/LED ผ่าน HDMI-CEC/RS-232 บน LAN พร้อมจัดการ content/schedule/playlist งานฝึกงาน (internship) ของนักศึกษา 2 คน (แบ่ง backend/frontend). เป็น git repo แยกของตัวเอง (branch `docs/internship-book`), ไม่ใช่ 3-tier ธรรมดาแต่เป็น **5 หน่วย deploy**: admin-ui, backend, worker, Android player, web player + data layer (Postgres/Redis/MinIO).

## Tech stack ต่อชั้น

| ชั้น | ตัวที่ใช้จริง |
|---|---|
| **Frontend** `admin-ui/` | Next.js 14.2.18 (App Router), React 18.3.1, TypeScript 5.7.2, Tailwind 3.4.16, UI kit มือเขียนเอง (ไม่มี component library), auth = JWT localStorage หรือ httpOnly-cookie สลับด้วย `NEXT_PUBLIC_AUTH_MODE` |
| **Backend** `backend/` | Python 3.12, **FastAPI 0.115.5** + Uvicorn, Pydantic 2.10.3 + pydantic-settings, **SQLAlchemy 2.0 async** + asyncpg + **Alembic**, Redis + **Arq** (job queue, ไม่ใช่ Celery), JWT (`python-jose`) + bcrypt (`passlib`), RBAC มือเขียน (7 roles), MinIO ผ่าน boto3, ffmpeg-python/Pillow (media), sentry-sdk (optional) |
| **Database** | **PostgreSQL 16** (จริง) + Redis 7 (cache/queue) + MinIO (object storage) — SQLite/aiosqlite ใช้แค่ตอน pytest หรือ fallback dev ไม่มี Docker |
| **Player - Android** `player/android/` | Kotlin + Gradle (AGP 8.7.2, Kotlin 2.0.21), USB-Serial bridge (FTDI/CP210x/CH340/PL2303) |
| **Player - Web** `player/web/` | Vanilla JS/HTML/CSS PWA + service worker, สำหรับ Raspberry Pi/mini PC ที่รัน Chromium `--kiosk` |
| **TV control** `tv-control/` | Python (`pyserial` + HDMI-CEC) |
| **Deploy** | Docker Compose (dev/prod), nginx reverse-proxy+TLS, หรือ systemd units (ไม่ใช้ container) |

## Directory map

Monorepo แบบ sibling folders ที่ root (ไม่ใช่ nested `frontend/`+`backend/`):

```
Project-intern/
├── admin-ui/            Next.js frontend — src/app/(dashboard)/{devices,contents,groups,
│                        presentations,plans,schedules,emergency,tv-control,users,audit}/
│                        src/lib/{api.ts,auth.tsx,i18n.tsx,theme.tsx,types.ts}
├── backend/             FastAPI — app/main.py (entry) · app/config.py (Settings) · app/db.py
│   ├── app/api/v1/      router.py + deps.py (auth/RBAC) + endpoints/ (13 module: auth,users,
│   │                    devices,contents,presentations,plans,schedules,player,tv_control,
│   │                    emergency,monitoring,reports,led)
│   ├── app/core/        security.py, middleware.py(CSRF/rate-limit), storage.py(S3),
│   │                    antivirus.py(ClamAV), url_guard.py(SSRF guard)
│   ├── app/models/      SQLAlchemy ORM (9 ไฟล์: user,device,content,presentation,plan,
│   │                    schedule,emergency,audit,playback)
│   ├── app/services/    business logic (auth/device/content/manifest/schedule_eval/report/audit)
│   ├── app/workers/     Arq task functions (content/device/emergency/report tasks)
│   ├── alembic/versions/  0001_initial_users … 0005_playback_logs (5 migrations)
│   └── tests/           pytest suite (ดู §Test)
├── player/android/      Kotlin: MainActivity, PlayerService, ApiClient, ManifestCache, TvSerialBridge
├── player/web/          PWA: index.html, app.js, sw.js
├── tv-control/          HDMI-CEC/RS-232 helper + systemd unit
├── emulator/            software TV/player emulator (ทดสอบ protocol โดยไม่ต้องมีจอจริง)
├── nginx/signage.conf   prod reverse-proxy config
├── deploy/systemd/      signage.service, signage-backup.{service,timer}
├── docs/                ดู §Docs
├── e2e/                 puppeteer browser E2E (ดู §Test)
├── scripts/             run-e2e.{sh,ps1}, smoke_e2e.py, verify.{sh,ps1}, backup.{sh,ps1}
└── project-book-prep/   ⚠️ เอกสารเล่มรายงานฝึกงาน ไม่ใช่ doc ของแอป (ดู §ของใหญ่/เสี่ยง)
```

## Entry points

| ทำอะไร | คำสั่ง |
|---|---|
| Full stack (แนะนำ) | `cp .env.example .env` แล้ว `docker compose up -d --build` (auto migrate+seed+reload) |
| One-command E2E | `bash scripts/run-e2e.sh` (หรือ `.ps1`) — build+start+รอ `/healthz`+pytest ใน container+`smoke_e2e.py` |
| Backend เดี่ยว (ไม่ผ่าน Docker) | `cd backend && uvicorn app.main:app --reload` — **⚠️ อ่าน `backend/.env` ตาม CWD ซึ่งตอนนี้ยัง SQLite ค้าง (ดู §Env)** |
| Worker | `arq app.worker.WorkerSettings` (จาก `backend/`) |
| Frontend เดี่ยว | `cd admin-ui && npm run dev` (port 3000) |
| Web player | `npx serve player/web -p 8080 -s` |

**Ports (dev)**: postgres 5432 · redis 6379 · minio 9000/9001 · **backend 8000** · admin-ui 3000. Swagger ที่ `http://localhost:8000/api/docs`. Login default seed: `admin` / `ChangeMe123!`.

**DB schema**: source of truth = `backend/app/models/*.py`, migration = `backend/alembic/versions/`, ER diagram ที่อ่านง่ายสุด = `docs/er-diagram.md` (generate จาก model จริง — **เชื่อถือได้มากกว่า** doc อื่น)

## ⚠️ Env files ตีกันเอง — เช็คก่อนทุกครั้งที่รันนอก Docker

| ไฟล์ | สถานะ | ผลกระทบ |
|---|---|---|
| `Project-intern/.env` (root) | ✅ ล่าสุด/ถูกต้อง — ชี้ Postgres จริง, `NEXT_PUBLIC_API_URL` ถูกต้อง | ใช้กับ docker-compose ทุก service |
| `backend/.env` | ❌ **ค้าง SQLite** (`sqlite+aiosqlite:///./signage_dev.db`), `NEXT_PUBLIC_API_URL` ยังเป็น LAN IP เก่า | ใครรัน backend ตรงๆ (ไม่ผ่าน Docker) จะได้ SQLite แทน Postgres แบบเงียบๆ |
| `admin-ui/.env.local` | ❌ **ค้าง LAN IP เก่า** `http://192.168.1.141:8001/api` | **นี่คือ "baked wrong at build time" ตัวจริง** — build/run admin-ui เครื่องอื่นจะยิง API URL ที่ตายแล้ว |

**กฎปฏิบัติ**: เชื่อ root `.env` เป็นหลักเสมอ ถ้าจะรัน backend/admin-ui แยกนอก Docker ต้องเช็ค/แก้ 2 ไฟล์ stale ข้างต้นก่อน อย่าสมมติว่าทั้ง 3 ตรงกัน. `docker-compose.override.yml` (gitignored) มีไว้แก้ port ชนกับโปรเจกต์ `concert-*` บนเครื่องเดียวกัน.

## Docs inventory

**`docs/`** (ทั้งหมด track ใน git): `admin-manual-th.md`(คู่มือผู้ใช้), `api.md`(ชี้ไป Swagger), `architecture.md`(ภาพรวม, รายละเอียดจริงอยู่ `PLAN.md §2-3,§34-38`), `demo-presentation-guide-th.md`, `deployment.md`, `disaster-recovery.md`, **`er-diagram.md`(น่าเชื่อสุด — generate จาก model จริง)**, `installation-guide-th.md`, `player-config.md`, `production-deployment.md`, `troubleshooting.md`.

**Root ที่ track ใน git**: `README.md`(ภาพรวม+quickstart), `CHANGELOG.md`, `SECURITY.md`, `TODO-backend.md`/`TODO-frontend.md` (**มี checklist เตือนเรื่อง env gotcha ข้างบนอยู่แล้ว**).

**Root ที่ local-only (gitignored, ไม่ push)**: `PLAN.md`(สเปกเต็ม 71KB, ทุก `§N` ในโค้ด comment อ้างถึงไฟล์นี้), `ARCHITECTURE-ANALYSIS.md`, `SESSION.md`(106KB, log รายเซสชัน), `WORKLOG.md`, `RUNBOOK.md`.

**`project-book-prep/`** — ⚠️ **ไม่ใช่ doc ของแอป** เป็นต้นฉบับ+ผลลัพธ์เล่มรายงานฝึกงานนักศึกษา (บทที่ 1-5, docx 3 ไฟล์, รูปหน้า 29 ไฟล์) — ดู §ของใหญ่/เสี่ยง

## Test layout

- **Backend**: `pytest` + `pytest-asyncio`, `backend/tests/` (15 ไฟล์ `test_*.py` + `conftest.py`, 133 `def test_*`/`async def test_*` — verified ตรง, pytest collect-only ได้ 142 เพราะมี parametrize บางเคส ตรงกับที่ README อ้าง "142 passed") — ใช้ **SQLite in-memory** เสมอ (ไม่แตะ Postgres จริงแม้แต่ตอน test)
- **Frontend**: ไม่มี unit/component test — CI แค่ `lint`+`type-check`+`build`
- **Browser E2E**: `e2e/` (puppeteer-core, `package.json`แยกของตัวเอง) — `login_e2e.mjs`, `webplayer_e2e.mjs` — ต้องมี stack รันอยู่แล้ว + **hardcode path Chrome เครื่อง Windows** (`C:\Program Files\Google\Chrome\Application\chrome.exe`)
- **Integration smoke**: `scripts/smoke_e2e.py` (pure stdlib, ไม่ใช้ pytest) — เดินครบ flow login→device→content→presentation→schedule→emergency→cleanup
- **Orchestrator ("run-e2e"/"smoke test" ที่เคยพูดถึง)**: `scripts/run-e2e.sh`/`.ps1` — เรียก 3 อย่างข้างบนต่อกัน, ใช้ `docker-compose.e2e.yml` บังคับ Postgres จริง+เลี่ยง port ชน
- CI (`.github/workflows/ci.yml`): backend pytest (`DATABASE_URL=sqlite`) + ruff + non-blocking mypy + admin-ui lint/type-check/build; `e2e` job รันเฉพาะ push `main`

## ห้ามอ่านเข้า context (build artifacts)

| Path | ขนาด |
|---|---|
| `admin-ui/node_modules/` | 361 MB |
| `admin-ui/.next/` | 102 MB |
| `backend/.venv/` | 215 MB |
| `e2e/node_modules/` | 28 MB |
| `project-book-prep/` | 51 MB — ดูด้านล่าง |
| `backend/**/__pycache__/` | 405 folder ย่อย |

Pattern ทั่วไป: `__pycache__/`, `.venv/`, `.pytest_cache/`, `node_modules/`, `.next/`, `*.tsbuildinfo`, `*.log`, `.gradle/`, `*.apk`, `*.db`. รวมทั้ง repo ~768MB แต่ source จริงที่ track ใน git มีแค่ **275 ไฟล์**.

## ของใหญ่/เสี่ยง — ระวังอย่าอ่านมั่ว

- **`project-book-prep/`** (51MB) — เอกสารเล่มรายงานนักศึกษา (`digital-signage-report{,-jakapob,-phornchanok}.docx`, รูปหน้า 29 PNG) **ไม่ใช่ source ของแอป** อย่าใช้เป็นอ้างอิงพฤติกรรมระบบ
- **`backend/signage_dev.db`** + **`Project-intern/signage_dev.db`** (root) — ไฟล์ SQLite binary 2 ตัวจากการรัน backend คนละที่ — ไม่ต้องอ่านเป็น text
- **`user-test-demo/`** (585KB, gitignored) — มี JWT token คู่ (dev account, หมดอายุแล้ว) + default password `ChangeMe123!` จาก log ทดสอบเก่า — ความเสี่ยงต่ำ (dev only) แต่ไม่ต้อง quote token ตรงๆ
- **`messageImage_1778496968661.jpg`**, **`รูปเล่มเดชธนา นาเมืองรักษ์2 (2).pdf`** — ไฟล์อ้างอิง/ต้นฉบับโจทย์ ไม่ใช่โค้ด
