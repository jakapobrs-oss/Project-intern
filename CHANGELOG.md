# 📜 CHANGELOG

บันทึกการเปลี่ยนแปลงทั้งหมดของ **ระบบจัดการจอประชาสัมพันธ์ (Digital Signage Management System)**

รูปแบบอ้างอิง [Keep a Changelog](https://keepachangelog.com/) และใช้ [Semantic Versioning](https://semver.org/lang/th/)
ที่มาของข้อมูล: `WORKLOG.md` (permission + progress tracker) และ `SESSION.md` (log ละเอียดทุก session)

---

## [1.0.0] — 2026-05-28 — 🎉 Production-ready v1

เวอร์ชันแรกที่ครบทุกส่วน (backend + admin UI + player) พร้อม deploy hardening
สรุปงานทั้งหมด Phase 0–7 (sessions #1–#28). ทุกเครื่องมือเป็น **OSS / ฟรี** ตามบรีฟ

### 🧱 โครงสร้างพื้นฐาน (Phase 0 — Scaffolding)
- ตั้งค่า monorepo: `backend/` (FastAPI), `admin-ui/` (Next.js 14), `player/` (Android + Web PWA), `tv-control/`, `docs/`
- `docker-compose.yml` (dev): PostgreSQL 16 + Redis 7 + MinIO + backend + Arq worker + admin-ui
- Backend skeleton: Pydantic Settings, SQLAlchemy 2.x async engine, Alembic async migration, Arq worker entry
- เครื่องมือคุณภาพโค้ด: ruff + mypy + pytest (`pyproject.toml`)

### 🔐 Authentication & Authorization (Phase 1)
- โมเดล `User` + RBAC **7 roles**: `super_admin / admin / editor / approver / viewer / operator / device`
- JWT auth (access + refresh) — `POST /auth/login`, `/auth/refresh`, `GET /auth/me`
- Account lockout: นับ `failed_login_count` + ล็อกบัญชีเมื่อพยายามเกินกำหนด
- User CRUD endpoint + seed admin เริ่มต้น
- ครอบคลุมด้วย 14 unit tests

### 📺 Devices & Content (Phase 2)
- โมเดล `Device` + `PlayerGroup` (M:N ผ่าน `player_group_members`) + `Content` + `Presentation`
- **Device pairing**: 6-digit pairing code (ตัดอักษรกำกวม 0/O/I/1) + device token แยกจาก user JWT (revoke ได้)
- อัปโหลดสื่อขึ้น MinIO/S3 (boto3) + ตรวจ **magic-bytes** + **dedupe ด้วย sha256**
- Content approval workflow: `draft → pending → approved / rejected`

### 📋 Playlists, Schedules & Manifest (Phase 3)
- **5-tier composition hierarchy** (§35.1): Content → Zone → Presentation → Plan → Schedule
- โมเดล `Plan` + `PlanItem` (เรียงลำดับ + override duration) และ `Schedule`
- Schedule: iCal `RRULE` repeat + daily time window + `priority` + สถานะ `draft/pending_approval/active/paused/expired`
- **Manifest service** (§35.2): pre-compute JSON ให้ player ดึง (offline-friendly) + `GET /player/manifest`

### 🎛️ TV Control — HDMI-CEC + RS-232 (Phase 4)
- Protocol builder **6 ยี่ห้อ**: Samsung MDC / LG / Sony / Panasonic / NEC / Toshiba (+ CEC generic)
- คำสั่งผ่าน **Redis command queue** → admin ส่ง / player pull + ack
- HDMI-CEC native helper (Python wrapper + systemd unit + HTTP API) สำหรับ player บน Linux
- ครอบคลุมด้วย 14 tests

### 🖥️ Player — Android + Web PWA (Phase 4-player, Option F)
- **Web PWA kiosk**: zone renderer (fullscreen / split / main+ticker) + plan carousel + emergency overlay
- Web Serial API bridge สำหรับ RS-232 + USB-Serial (FTDI / CP210x / CH340 / PL2303)
- Resilience: exponential backoff แบบ jittered + Cache Storage LRU + service-worker size cap
- **Android (Kotlin)**: usb-serial-for-android + Backoff util + ManifestCache LRU + media pre-cache

### 🚨 Emergency Broadcast & Monitoring (Phase 5)
- โมเดล `EmergencyBroadcast`: kind `text/image/url` + targeting แบบ JSON (`all` / device_ids / group_ids)
- **Manifest emergency override**: priority-sorted แทรกทับ schedule ปกติ
- Auto-expire worker (Arq cron) ปลดประกาศหมดอายุอัตโนมัติ
- **Prometheus `/metrics`** + `/readiness` (เช็ค DB) + `/healthz` (liveness)
- **Audit log** (append-only, no-FK เพื่อคงประวัติแม้ user ถูกลบ) — บันทึก auth.login / content.approve|reject / schedule.activate|pause / device.pair / tv.command_sent
- Sentry SDK (เปิด/ปิดผ่าน env) + สคริปต์ backup (`backup.sh` / `backup.ps1`)

### 🎨 Admin UI — Next.js 14 (Phase 6)
- **11 หน้า**: Dashboard, Devices, Contents, Presentations, Plans, Schedules, Groups, TV-Control, Emergency, Audit, Users
- Auth flow: login + JWT storage + refresh interceptor
- UX ขั้นสูง: Toast, drag-drop playlist composer, presentation composer, schedule wizard, emergency target picker, device detail
- **Dark mode + i18n (ไทย/อังกฤษ)**: theme/i18n provider + topbar switcher + กัน flash ตอน hydrate

### 🛡️ Deploy Hardening (Phase 7)
- Security headers + rate-limit middleware (Redis-backed, INCR+EXPIRE, fail-open)
- Production Dockerfiles (multi-stage, non-root) + `docker-compose.prod.yml` + nginx TLS + systemd units
- GitHub Actions CI + security workflow
- **httpOnly cookie auth (dual-mode)**: สลับ header / cookie ผ่าน `NEXT_PUBLIC_AUTH_MODE`
- **CSRF protection**: double-submit cookie + `/auth/csrf` endpoint (toggle ผ่าน env)
- Sentry PII scrubbing (`before_send` scrubber)
- เอกสาร `docs/production-deployment.md` (TLS / secrets / rotation / backup verify)

### 🧪 Integration & Tooling
- `scripts/verify.sh` / `.ps1` + `scripts/smoke_e2e.py` (10 ขั้น ครอบคลุม Phase 0–6 + emergency override)
- `scripts/run-e2e.sh` / `.ps1`: build → start → รอ healthy → pytest → smoke → แสดง URL
- Docker auto-migrate + auto-seed + healthcheck + `seed_demo.py` (demo data ครบ flow)
- `.env.example` พร้อม Sentry + seed config + `RUNBOOK.md`

### 📚 เอกสารประกอบ
- `PLAN.md` (roadmap 39 sections), `ARCHITECTURE-ANALYSIS.md`, `SESSION.md`, `WORKLOG.md`
- `docs/`: architecture / api / deployment / production-deployment / er-diagram
- `project-book-prep/`: เอกสารเล่มฝึกงาน — internship-book-materials, data-dictionary, tools-list, ER diagram (+ PNG/SVG/.mmd + mermaid.live links)

---

## รุ่นถัดไป (Unreleased / รอ permission)
- **Option E** — รันจริงใน environment user: `docker compose up`, build APK Android, smoke E2E เต็มรูปแบบ
- **Phase 6 Pass 3** — calendar view สำหรับ schedule, bulk operations, custom presentation layout (drag corners)
- ตารางที่ยังไม่ลง DB (อยู่ใน PLAN): `device_telemetry_history`, `tv_command_log`, `content_tags`, `notification_preferences`, `pdpa_consents`

---

> **หมายเหตุ:** การกำหนด `1.0.0` อ้างอิงจากสถานะ "production-ready" ที่บันทึกไว้ใน `WORKLOG.md` หลัง session #28
> ระบบยังไม่ถูก deploy จริงในเครื่อง user (รอ permission — ดู Option E)
