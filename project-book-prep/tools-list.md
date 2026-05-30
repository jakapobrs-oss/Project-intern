# 🧰 รายการเครื่องมือ/เทคโนโลยีทั้งหมดในโปรเจกต์ (Tools & Tech Inventory)

> โปรเจกต์: **Digital Signage Management System** — ระบบจัดการจอประชาสัมพันธ์
> สังเคราะห์จาก `requirements.txt`, `package.json`, `docker-compose.yml`, source code และ docs
> อัปเดต: 2026-05-29

ทุกเครื่องมือเป็น **Open Source / ฟรี** ตามข้อกำหนดของโปรเจกต์

---

## 1) Backend (FastAPI / Python)

| เครื่องมือ | เวอร์ชัน | หน้าที่ |
|---|---|---|
| Python | 3.12 | ภาษาหลักฝั่ง backend |
| FastAPI | 0.115.5 | Web API framework (async, OpenAPI auto-doc) |
| Uvicorn | 0.32.1 | ASGI server |
| Pydantic | 2.10.3 | Data validation / schema |
| Pydantic-Settings | 2.7.0 | จัดการ config จาก env |
| SQLAlchemy (asyncio) | 2.0.36 | ORM แบบ async |
| asyncpg | 0.30.0 | PostgreSQL async driver |
| Alembic | 1.14.0 | Database migration |
| aiosqlite | 0.20.0 | SQLite driver (ใช้ตอนทดสอบ) |
| Redis (client) | 5.2.1 | เชื่อมต่อ cache / queue broker |
| Arq | 0.26.3 | Background worker / job queue |
| python-jose[cryptography] | 3.3.0 | JWT สร้าง/ตรวจสอบ token |
| passlib[bcrypt] | 1.7.4 | Hash รหัสผ่าน |
| python-multipart | 0.0.18 | รับ multipart/form upload |
| boto3 / botocore | 1.35.81 | S3 client (เชื่อม MinIO) |
| ffmpeg-python | 0.2.0 | ประมวลผลวิดีโอ (ดึง metadata/thumbnail) |
| Pillow | 11.0.0 | ประมวลผลรูปภาพ |
| httpx | 0.28.1 | HTTP client |
| python-dotenv | 1.0.1 | โหลด .env |
| loguru | 0.7.3 | Logging |
| tenacity | 9.0.0 | Retry logic |
| sentry-sdk[fastapi] | 2.19.0 | Error monitoring (optional) |

## 2) Frontend / Admin UI (Next.js)

| เครื่องมือ | เวอร์ชัน | หน้าที่ |
|---|---|---|
| Next.js | 14.2.18 | React framework (App Router) |
| React / React-DOM | 18.3.1 | UI library |
| TypeScript | 5.7.2 | ภาษา (typed JS) |
| Tailwind CSS | 3.4.16 | Utility-first CSS |
| PostCSS / Autoprefixer | 8.4.49 / 10.4.20 | CSS pipeline |
| lucide-react | 0.468.0 | Icon set |
| clsx | 2.1.1 | จัดการ conditional className |
| ESLint + eslint-config-next | 8.57.1 | Linting |

## 3) Player (จอแสดงผล)

| เครื่องมือ | หน้าที่ |
|---|---|
| Android (Kotlin) | Native player app + USB-Serial bridge |
| PWA (HTML/CSS/JS + Service Worker) | Web kiosk player (`player/web/`) — offline-friendly |
| Web Serial API / USB-Serial | สะพานควบคุม RS-232 ผ่านสาย FTDI / CP210x / CH340 / PL2303 |

## 4) TV Control

| เครื่องมือ | หน้าที่ |
|---|---|
| libcec | ควบคุมทีวีผ่าน HDMI-CEC |
| pyserial | ควบคุมทีวีผ่าน RS-232 (6 brand protocols: Samsung MDC, LG, Sony, ฯลฯ) |
| Redis queue | คิวคำสั่งควบคุมทีวี |

## 5) Database / Storage / Infrastructure

| เครื่องมือ | เวอร์ชัน | หน้าที่ |
|---|---|---|
| PostgreSQL | 16 | ฐานข้อมูลหลัก |
| Redis | 7 | Cache + broker ของ Arq |
| MinIO | S3-compatible | Object storage (เก็บไฟล์สื่อ) self-host |

## 6) DevOps / Deployment / Tooling

| เครื่องมือ | หน้าที่ |
|---|---|
| Docker + Docker Compose | dev stack (postgres + redis + minio + backend + worker + admin-ui) |
| systemd | run service ใน production (`deploy/systemd/`) |
| Nginx | reverse proxy (`nginx/signage.conf`) |
| GitHub Actions | CI + security workflow (`.github/workflows/ci.yml`, `security.yml`) |
| Git | version control |
| Prometheus | metrics / monitoring (Phase 5) |
| Sentry | error tracking (optional) |

## 7) Dev / Test / Quality

| เครื่องมือ | เวอร์ชัน | หน้าที่ |
|---|---|---|
| pytest | 8.3.4 | Test runner |
| pytest-asyncio | 0.25.0 | ทดสอบ async |
| pytest-cov | 6.0.0 | Code coverage |
| ruff | 0.8.3 | Linter / formatter |
| mypy | 1.13.0 | Static type checker |
| Bash / PowerShell scripts | — | run-e2e, verify, backup (`scripts/`) |

## 8) สรุปจำนวน (เชิงปริมาณสำหรับเล่มรายงาน)

- **API endpoints รวม ~58 routes** ใน 12 กลุ่ม (auth, users, devices, groups, contents, presentations, plans, schedules, player, tv, emergency, monitoring)
- **โมเดลฐานข้อมูล: 12 ตาราง** = 11 mapped entity tables + 1 association table (M:N) — ในจำนวนนี้เป็น entity หลัก 8 ตาราง
- **Admin UI: 13 หน้า** (dashboard, devices, contents, presentations, plans, schedules, groups, tv-control, emergency, users, audit, device detail, login)
- **Unit/Integration tests: ~90 test cases** ใน 9 ไฟล์ทดสอบ
- **Phase ที่จบแล้ว: 0–6 + Player polish (F)**
