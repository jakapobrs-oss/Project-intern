# 📘 ข้อมูลเตรียมเล่มรายงานโครงงานฝึกงาน
## Digital Signage Management System — ระบบจัดการจอประชาสัมพันธ์

> เอกสารนี้รวบรวมข้อมูลทุกอย่างที่จำเป็นสำหรับเขียน "เล่มรายงานฝึกงาน" — นำแต่ละหัวข้อไปจัดรูปแบบตามเทมเพลตของมหาวิทยาลัย/หน่วยงานได้เลย
> อัปเดต: 2026-05-29 · สถานะโปรเจกต์: Phase 0–6 + Player polish (F) เสร็จสมบูรณ์

---

## 1. บทสรุปโครงงาน (Abstract / Executive Summary)

ระบบ Digital Signage Management System เป็นแพลตฟอร์มจัดการจอประชาสัมพันธ์แบบครบวงจร
ครอบคลุมการจัดการเนื้อหา (content) การจัดผังการแสดงผล (layout/presentation)
การจัดตารางเวลาออกอากาศ (schedule) การควบคุมจอโทรทัศน์ระยะไกล (HDMI-CEC + RS-232)
รวมถึงระบบประกาศฉุกเฉิน (emergency override) และการเฝ้าระวังสถานะอุปกรณ์ (monitoring)
ออกแบบให้ทำงานภายในเครือข่าย LAN รองรับการเล่นแบบ offline-friendly ผ่าน manifest
และใช้เทคโนโลยี Open Source ทั้งหมด

---

## 2. ที่มาและความสำคัญ (Background & Motivation)

องค์กรที่มีจอประชาสัมพันธ์หลายจุดต้องการระบบกลางในการอัปเดตเนื้อหา จัดตารางการแสดงผล
และควบคุมจอจากศูนย์กลาง แทนการเดินไปเสียบ USB หรือเปิด/ปิดจอด้วยมือ
โครงงานนี้พัฒนาเพื่อแก้ปัญหานั้น โดยรวมงานจัดการเนื้อหา การควบคุมฮาร์ดแวร์
และการประกาศฉุกเฉินไว้ในระบบเดียว ลดเวลาและความผิดพลาดในการดำเนินงาน

---

## 3. วัตถุประสงค์ (Objectives)

1. สร้างระบบจัดการเนื้อหาและตารางการแสดงผลของจอประชาสัมพันธ์จากศูนย์กลาง
2. รองรับการควบคุมทีวีระยะไกล (เปิด/ปิด/เปลี่ยน input) ผ่าน HDMI-CEC และ RS-232 หลายยี่ห้อ
3. มีระบบสิทธิ์ผู้ใช้ (RBAC) และกระบวนการอนุมัติเนื้อหา/ตาราง
4. รองรับการประกาศฉุกเฉินที่ override ตารางปกติได้ทันที
5. เฝ้าระวังสถานะอุปกรณ์และบันทึก audit log ทุกการกระทำ
6. ใช้เทคโนโลยี Open Source และ deploy ด้วย Docker ได้

---

## 4. ขอบเขตของโครงงาน (Scope)

- รองรับจอ 10–20 จุด (POC scale) ขยายได้ผ่าน player group
- แพลตฟอร์มจอ: Android TV / Android tablet / RPi kiosk / Windows PC / Web browser
- TV brand: Samsung MDC, LG, Sony และอื่น ๆ ผ่าน enum (6 protocol)
- Deploy แบบ on-premise Linux (Ubuntu 22.04) + Docker
- ชนิดเนื้อหา: image / video / web / stream / text
- ไม่รวม: LED board (รอ spec), data migration (เป็น greenfield)

---

## 5. เทคโนโลยีที่ใช้ (Tech Stack)

| Layer | เทคโนโลยี |
|---|---|
| Backend API | FastAPI 0.115 + Python 3.12 (async, OpenAPI) |
| ORM / Migration | SQLAlchemy 2.x async + Alembic |
| Database | PostgreSQL 16 |
| Cache / Queue | Redis 7 + Arq worker |
| Object Storage | MinIO (S3-compatible) |
| Admin UI | Next.js 14 + TypeScript + Tailwind CSS |
| Player | Android (Kotlin) + PWA kiosk |
| TV Control | libcec (HDMI-CEC) + pyserial (RS-232) |
| Deploy | Docker Compose (dev) → systemd / Nginx (prod) |

> รายละเอียดครบทุกเครื่องมือดูที่ไฟล์ **`tools-list.md`**

---

## 6. สถาปัตยกรรมระบบ (System Architecture)

ส่วนประกอบหลัก 6 ส่วนทำงานร่วมกันใน Docker stack:

1. **Backend (FastAPI)** — REST API, business logic, auth
2. **Worker (Arq)** — งานเบื้องหลัง เช่น auto-expire emergency, media processing
3. **PostgreSQL** — ฐานข้อมูลหลัก
4. **Redis** — cache + broker คิวงานและคิวคำสั่งควบคุมทีวี
5. **MinIO** — เก็บไฟล์สื่อ (S3-compatible)
6. **Admin UI (Next.js)** — หน้าจอจัดการสำหรับผู้ดูแล

Player (จอ) ดึง **manifest** จาก backend แล้วเล่นเนื้อหาแบบ offline-friendly
มี backoff + LRU cache รองรับเน็ตหลุด
รายละเอียดเพิ่มเติม: `docs/architecture.md`, `ARCHITECTURE-ANALYSIS.md`

---

## 7. การออกแบบฐานข้อมูล (ER Diagram)

ฐานข้อมูลมีทั้งหมด **12 ตาราง** = **11 mapped entity tables + 1 association table (M:N)** (8 entity หลัก + 3 ตารางลูก/สนับสนุน: audit_logs, presentation_zones, plan_items) แบ่ง 5 กลุ่ม:
Identity & Audit · Devices · Content & Composition · Playlists & Schedules · Emergency

ER diagram ฉบับเต็ม (Mermaid) อยู่ที่ไฟล์ **`er-diagram.md`**
และไฟล์ source สำหรับ render PNG อยู่ที่ **`assets/er-full.mmd`**
(วางบล็อก Mermaid ที่ https://mermaid.live เพื่อ export เป็นรูปใส่เล่มได้)

แนวคิดเด่น: **5-Tier Content Hierarchy**
Content (สื่อดิบ) → Zone → Presentation (layout) → Plan (ลำดับ) → Schedule (เวลา + กลุ่มจอ)
ทำให้ reuse เนื้อหาได้ และเปลี่ยน schedule ครั้งเดียวกระทบทั้งกลุ่มจอ

---

## 8. ฟังก์ชันการทำงานหลัก (Features / Modules)

| Module | ความสามารถ |
|---|---|
| Auth & Users | JWT + RBAC 7 roles (super_admin/admin/editor/approver/viewer/operator/device), lock account, cookie auth |
| Devices | Pairing ด้วยรหัส, heartbeat, telemetry (CPU/temp/uptime), จัดกลุ่มจอ (M:N) |
| Contents | อัปโหลดสื่อ + dedupe (sha256) + thumbnail + กระบวนการอนุมัติ (draft→pending→approved/rejected) |
| Presentations | จัด layout หลาย zone (composer) ใน Admin UI |
| Plans | จัดลำดับ presentation พร้อม override duration |
| Schedules | ผูก plan กับกลุ่มจอ + RRULE (iCal) + daily window + priority + อนุมัติ |
| TV Control | สั่งเปิด/ปิด/เปลี่ยน input ผ่าน HDMI-CEC + RS-232 (6 brand) ผ่าน Redis queue |
| Emergency | ประกาศฉุกเฉิน override ทุกตาราง + auto-expire + requires_ack |
| Monitoring | Prometheus metrics + readiness/liveness + audit log + Sentry + backup |
| Player | Zone renderer + plan carousel + emergency overlay + offline cache |

---

## 9. รายการ API (สรุป)

API เวอร์ชัน v1 รวมประมาณ **58 endpoints** ใน 12 กลุ่ม:

| กลุ่ม (prefix) | จำนวน routes |
|---|---|
| /auth | 5 |
| /users | 5 |
| /devices (+/groups) | 6 |
| /contents | 8 |
| /presentations | 5 |
| /plans | 5 |
| /schedules | 7 |
| /player | 6 |
| /tv | 2 |
| /emergency | 6 |
| /monitoring | 3 |

> เอกสาร API อัตโนมัติ (Swagger): `http://localhost:8000/api/docs` · ดูเพิ่ม `docs/api.md`

---

## 10. การทดสอบ (Testing)

- ใช้ pytest + pytest-asyncio + pytest-cov
- มีประมาณ **90 test cases** ใน 9 ไฟล์ ครอบคลุม auth, devices, content pipeline,
  tv control, emergency/audit, security middleware, cookie auth, Sentry scrub, health
- มี E2E smoke test (`scripts/smoke_e2e.py`) + script รัน E2E ครบ stack
- CI ผ่าน GitHub Actions (ci.yml + security.yml)

---

## 11. การติดตั้งและใช้งาน (Deployment)

- **Dev:** `docker compose up -d --build` (auto-migrate + auto-seed admin)
- **One-command E2E:** `bash scripts/run-e2e.sh` / `.\scripts\run-e2e.ps1`
- **Demo data:** `docker compose exec backend python -m app.scripts.seed_demo`
- **Prod:** systemd service + Nginx reverse proxy + backup timer
- ค่าเริ่มต้น login: `admin / ChangeMe123!` (เปลี่ยนก่อน production)
- ดูเพิ่ม: `docs/deployment.md`, `docs/production-deployment.md`, `RUNBOOK.md`

---

## 12. ผลลัพธ์และสถานะ (Results)

ระบบทำงานครบ Phase 0–6 + Player polish:
backend + Admin UI (13 หน้า) + Web/Android player พร้อมใช้งานจริง
รองรับ flow ตั้งแต่ upload เนื้อหา → จัด layout → ตั้งตาราง → จอเล่นจริง → ประกาศฉุกเฉิน

**งานที่เหลือ/ต่อยอด (Phase 7):** HDMI-CEC native, httpOnly cookie hardening,
i18n, CI/CD เพิ่มเติม, security hardening, ตาราง time-series telemetry

---

## 13. โครงสร้างเล่มที่แนะนำ (Suggested Report Outline)

1. ปก/ กิตติกรรมประกาศ / บทคัดย่อ
2. บทที่ 1 บทนำ — ที่มา, วัตถุประสงค์, ขอบเขต, ประโยชน์ที่คาดว่าจะได้รับ (§2–4)
3. บทที่ 2 ทฤษฎีและเทคโนโลยีที่เกี่ยวข้อง — tech stack (§5), ความรู้ Digital Signage, HDMI-CEC/RS-232
4. บทที่ 3 การวิเคราะห์และออกแบบระบบ — architecture (§6), ER diagram (§7), 5-tier hierarchy
5. บทที่ 4 การพัฒนาระบบ — modules (§8), API (§9), หน้าจอ Admin UI, player
6. บทที่ 5 การทดสอบและผลลัพธ์ — testing (§10), results (§12)
7. บทที่ 6 สรุปและข้อเสนอแนะ — สิ่งที่ได้เรียนรู้, ปัญหาที่พบ, แนวทางต่อยอด
8. ภาคผนวก — คู่มือติดตั้ง (§11), รายการเครื่องมือ (tools-list.md), screenshot

---

## 14. ไฟล์อ้างอิงในโปรเจกต์ (Source References)

| หัวข้อในเล่ม | ไฟล์ต้นทาง |
|---|---|
| ภาพรวม / tech stack | `README.md` |
| ER diagram | `docs/er-diagram.md` |
| สถาปัตยกรรม | `docs/architecture.md`, `ARCHITECTURE-ANALYSIS.md` |
| API | `docs/api.md` + Swagger |
| Deploy | `docs/deployment.md`, `docs/production-deployment.md`, `RUNBOOK.md` |
| แผนงาน / phases | `PLAN.md`, `WORKLOG.md`, `SESSION.md` |
| โค้ดโมเดล | `backend/app/models/` |
| โค้ด API | `backend/app/api/v1/endpoints/` |
| Admin UI | `admin-ui/src/app/` |

---

> **หมายเหตุการทำงานอัตโนมัติ (scheduled run):** เอกสารนี้สร้างจากการอ่านไฟล์จริงในโปรเจกต์
> ตัวเลข route/test เป็นการนับจาก source code ณ วันที่อัปเดต ควรตรวจสอบซ้ำก่อนส่งเล่มจริง
