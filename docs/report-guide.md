# 📘 ข้อมูลสำหรับทำเล่มรายงาน (ฝึกงาน / โครงงาน)

> **โปรเจกต์:** Digital Signage Management System — ระบบจัดการจอประชาสัมพันธ์ดิจิทัล
> **จุดประสงค์ของเอกสารนี้:** รวบรวม "ข้อมูลที่จำเป็นทั้งหมด" สำหรับเขียนเล่มรายงาน — คัดมาจากโค้ดและเอกสารจริงในโปรเจกต์ เพื่อให้นำไปกรอกในเทมเพลตของสถาบัน/บริษัทได้ทันที
> **อัปเดต:** 2026-06-18

---

## 🔑 วิธีใช้เอกสารนี้

- ส่วนที่มีสัญลักษณ์ **【กรอกเอง】** = ข้อมูลส่วนตัว/บริษัท ที่เอกสารนี้ไม่มี ต้องเติมเอง
- ส่วนที่เป็นเนื้อหาปกติ = ดึงจากโค้ด/เอกสารจริง นำไปใช้/เรียบเรียงต่อได้เลย
- เครื่องหมาย ☐ = checklist ติ๊กเมื่อทำเสร็จ
- อ้างอิงไฟล์จริงในวงเล็บ เช่น `backend/app/models/user.py` เพื่อให้ตรวจย้อนได้

---

## 1) องค์ประกอบของเล่ม (Checklist โครงเล่มมาตรฐาน)

### ส่วนนำ (Front matter)
- ☐ ปกนอก / ปกใน (ชื่อโครงงาน, ชื่อผู้จัดทำ, สถาบัน, ปีการศึกษา)
- ☐ หน้าอนุมัติ (ลายเซ็นอาจารย์ที่ปรึกษา / พนักงานพี่เลี้ยง / หัวหน้าหน่วยงาน)
- ☐ บทคัดย่อภาษาไทย (Abstract)
- ☐ บทคัดย่อภาษาอังกฤษ (ถ้าสถาบันกำหนด)
- ☐ กิตติกรรมประกาศ (Acknowledgements)
- ☐ สารบัญ (Table of Contents)
- ☐ สารบัญตาราง (List of Tables)
- ☐ สารบัญภาพ (List of Figures)

### เนื้อหาหลัก (Body)
- ☐ บทที่ 1 บทนำ
- ☐ บทที่ 2 ทฤษฎีและเทคโนโลยีที่เกี่ยวข้อง (และข้อมูลสถานประกอบการ)
- ☐ บทที่ 3 การวิเคราะห์และออกแบบระบบ
- ☐ บทที่ 4 ผลการดำเนินงาน
- ☐ บทที่ 5 สรุปผลและข้อเสนอแนะ

### ส่วนท้าย (Back matter)
- ☐ บรรณานุกรม (References)
- ☐ ภาคผนวก (Appendix) — คู่มือติดตั้ง, ตาราง API, ER, ตัวอย่างโค้ด
- ☐ ประวัติผู้จัดทำ (ถ้าสถาบันกำหนด)

---

## 2) ข้อมูลที่ต้องกรอกเอง 【กรอกเอง】

| หัวข้อ | ค่า |
|---|---|
| ชื่อ–นามสกุล ผู้จัดทำ | 【กรอกเอง】 |
| รหัสนักศึกษา | 【กรอกเอง】 |
| สาขาวิชา / คณะ / สถาบัน | 【กรอกเอง】 |
| ชื่อบริษัท / หน่วยงานที่ฝึกงาน | 【กรอกเอง】 |
| ที่อยู่บริษัท / แผนกที่สังกัด | 【กรอกเอง】 |
| ตำแหน่งงานที่ได้รับมอบหมาย | 【กรอกเอง】 |
| ชื่อพนักงานพี่เลี้ยง (Supervisor) | 【กรอกเอง】 |
| ชื่ออาจารย์ที่ปรึกษา | 【กรอกเอง】 |
| ระยะเวลาฝึกงาน (วันเริ่ม–วันสิ้นสุด) | 【กรอกเอง】 |
| จำนวนชั่วโมง/สัปดาห์ หรือชั่วโมงรวม | 【กรอกเอง】 |

---

## 3) บทคัดย่อ (ร่างให้ — ปรับตามจริง)

> ระบบจัดการจอประชาสัมพันธ์ดิจิทัล (Digital Signage Management System) พัฒนาขึ้นเพื่อรวมศูนย์การควบคุมจอแสดงผลหลายจอภายในองค์กรผ่านเครือข่าย LAN โดยผู้ดูแลสามารถอัปโหลดสื่อ (ภาพ/วิดีโอ/เว็บ), จัดวาง Layout, กำหนดผังการเล่น (Plan), ตั้งตารางเวลาออกอากาศ (Schedule) ตามกลุ่มจอ, สั่งเปิด–ปิด/ปรับเสียง/สลับ Input ของทีวีผ่าน HDMI-CEC และ RS-232 รวมถึงประกาศข่าวฉุกเฉิน (Emergency Broadcast) แทรกทับผังปกติได้ทันที
>
> ระบบออกแบบเป็นสถาปัตยกรรมแยกส่วน (Backend API, Admin Web UI, Player) ใช้รูปแบบ **Pre-computed Manifest** เพื่อให้เครื่องเล่น (Player) ทำงานแบบ offline-friendly และจัดโครงสร้างเนื้อหาแบบ **ลำดับชั้น 5 ระดับ** เพื่อให้นำสื่อกลับมาใช้ซ้ำได้ มีระบบสิทธิ์ผู้ใช้ (RBAC) 7 บทบาท พร้อมระบบ Audit Log, Monitoring และ Backup
>
> ผลการดำเนินงานสามารถพัฒนาได้ครบ Phase 0–6 ครอบคลุม API จำนวน 58 endpoint พร้อมชุดทดสอบอัตโนมัติ 90 รายการ และ Admin UI 13 หน้า

**คำสำคัญ (Keywords):** Digital Signage, FastAPI, PostgreSQL, HDMI-CEC, RS-232, RBAC, Docker

---

## 4) บทที่ 1 — บทนำ

### 1.1 ความเป็นมาและความสำคัญของปัญหา
- จอประชาสัมพันธ์ในองค์กรมักถูกจัดการแบบแยกเครื่อง (เสียบ USB ทีละจอ) ทำให้อัปเดตเนื้อหาช้าและไม่สอดคล้องกัน
- ขาดระบบกำหนดสิทธิ์/อนุมัติเนื้อหา ทำให้ควบคุมคุณภาพและความถูกต้องของสื่อได้ยาก
- ต้องเดินไปเปิด–ปิดทีวีเองหน้างาน ไม่มีการควบคุมรวมศูนย์
- เมื่อมีเหตุฉุกเฉิน ไม่สามารถแทรกประกาศขึ้นทุกจอพร้อมกันได้ทันที
- จึงพัฒนา "ระบบจัดการจอประชาสัมพันธ์ดิจิทัล" เพื่อรวมศูนย์การจัดการเนื้อหา ตารางเวลา และการควบคุมฮาร์ดแวร์ทีวี

### 1.2 วัตถุประสงค์
1. เพื่อพัฒนาระบบบริหารจัดการเนื้อหาและจอแสดงผลแบบรวมศูนย์ผ่านเว็บ
2. เพื่อให้กำหนดผังการเล่นและตารางเวลาออกอากาศตามกลุ่มจอได้
3. เพื่อควบคุมฮาร์ดแวร์ทีวี (เปิด–ปิด/เสียง/Input) ผ่าน HDMI-CEC และ RS-232
4. เพื่อรองรับการประกาศข่าวฉุกเฉินแทรกทับผังปกติได้แบบทันที
5. เพื่อให้ระบบมีการจัดการสิทธิ์ผู้ใช้ การอนุมัติเนื้อหา และบันทึกการใช้งาน (Audit)

### 1.3 ขอบเขตของโครงงาน
**ทำได้ (In scope):**
- จัดการผู้ใช้ + สิทธิ์ (RBAC 7 บทบาท), Login ด้วย JWT
- อัปโหลด/อนุมัติสื่อ (image/video/web/stream/text) เก็บบน Object Storage
- จับคู่ (Pair) เครื่องเล่นด้วย Pairing Code, ติดตามสถานะ/Heartbeat
- ประกอบ Presentation (Layout + Zone), จัด Plan, ตั้ง Schedule (รองรับ RRULE)
- ควบคุมทีวีหลายยี่ห้อผ่าน RS-232 / HDMI-CEC
- Emergency Broadcast พร้อม Auto-expire
- Monitoring (Prometheus), Audit Log, Backup

**ข้อจำกัด (Out of scope):**
- รองรับ POC ระดับ 10–20 จอ (ไม่ใช่ระดับ public cloud หลายพันจอ)
- LED Board แบบ controller card เฉพาะ ยังไม่รองรับ (รอ spec)
- ไม่มีการย้ายข้อมูลจากระบบเดิม (พัฒนาใหม่ทั้งหมด / greenfield)

### 1.4 ประโยชน์ที่คาดว่าจะได้รับ
- ลดเวลาและขั้นตอนการอัปเดตเนื้อหาบนจอหลายจอ
- ควบคุมคุณภาพเนื้อหาด้วยกระบวนการอนุมัติ (Approval Workflow)
- ลดการเดินไปควบคุมทีวีหน้างานด้วยการสั่งงานระยะไกล
- เพิ่มความปลอดภัย/ตรวจสอบย้อนหลังได้ด้วย Audit Log
- เผยแพร่ประกาศฉุกเฉินได้รวดเร็วและทั่วถึง

### 1.5 ระยะเวลาดำเนินงาน
- รวมประมาณ 8 สัปดาห์ (แบ่งเป็น Phase 0–6) — 【ปรับตามจริง / ใส่ Gantt chart】

### 1.6 นิยามศัพท์เฉพาะ
| ศัพท์ | ความหมาย |
|---|---|
| Digital Signage | ระบบป้าย/จอแสดงผลดิจิทัลเพื่อการประชาสัมพันธ์ |
| Manifest | ไฟล์ JSON ที่ Backend คำนวณล่วงหน้าว่าจอแต่ละเครื่องต้องเล่นอะไร |
| Player | โปรแกรมเครื่องเล่นที่ต่อกับจอ (Android / Raspberry Pi PWA) |
| Presentation | หน้าจอที่ประกอบเสร็จแล้ว (Layout + เนื้อหาในแต่ละ Zone) |
| Plan | ลำดับของ Presentation ที่เล่นต่อเนื่องกัน |
| Schedule | การจับคู่ Plan กับกลุ่มจอ + ช่วงเวลา + ลำดับความสำคัญ |
| RBAC | Role-Based Access Control — การจำกัดสิทธิ์ตามบทบาท |
| HDMI-CEC | โปรโตคอลควบคุมอุปกรณ์ผ่านสาย HDMI |
| RS-232 | พอร์ตอนุกรมสำหรับสั่งงานทีวีระดับมืออาชีพ |

---

## 5) บทที่ 2 — ทฤษฎีและเทคโนโลยีที่เกี่ยวข้อง

### 2.1 ข้อมูลสถานประกอบการ 【กรอกเอง】
- ประวัติบริษัท, ลักษณะธุรกิจ, โครงสร้างองค์กร, แผนกที่ฝึกงาน

### 2.2 เทคโนโลยีที่ใช้ (Tech Stack)
| ส่วน | เทคโนโลยี | บทบาทในระบบ |
|---|---|---|
| Backend API | FastAPI 0.115 + Python 3.12 (async) | ให้บริการ REST API + auto OpenAPI doc |
| ORM / Migration | SQLAlchemy 2.x (async) + Alembic | จัดการฐานข้อมูล + เวอร์ชัน schema |
| ฐานข้อมูล | PostgreSQL 16 | เก็บข้อมูลหลักทั้งหมด |
| Cache / Queue | Redis 7 | broker ของ Arq + rate limit |
| Worker | Arq | งานเบื้องหลัง (background jobs) |
| Object Storage | MinIO (S3-compatible) | เก็บไฟล์สื่อ |
| Admin UI | Next.js 14 + TypeScript + Tailwind | หน้าเว็บผู้ดูแล |
| Player | Android (Kotlin) + PWA kiosk | เครื่องเล่นต่อจอ |
| TV Control | libcec + pyserial | สั่งงานทีวีผ่าน HDMI-CEC / RS-232 |
| Deploy | Docker Compose → systemd / k8s | ติดตั้งและรันระบบ |
> ทุกตัวเป็นซอฟต์แวร์ Open Source / ฟรี

### 2.3 แนวคิด/ทฤษฎีที่เกี่ยวข้อง (อธิบายในเล่ม)
- **REST API & OpenAPI** — รูปแบบการออกแบบ API และเอกสารอัตโนมัติ
- **JWT (JSON Web Token)** — กลไก Authentication (access token 30 นาที, refresh 7 วัน)
- **RBAC** — การควบคุมสิทธิ์ตามบทบาท
- **Relational Database & Normalization** — การออกแบบฐานข้อมูลเชิงสัมพันธ์
- **Containerization (Docker)** — การห่อหุ้มแอปให้รันได้ทุกที่
- **Message Queue / Background Worker** — การประมวลผลงานหนักแบบ async
- **iCalendar RRULE (RFC 5545)** — กฎการเล่นซ้ำของตารางเวลา
- **HDMI-CEC & RS-232 Serial Protocol** — การสื่อสารควบคุมฮาร์ดแวร์ทีวี
- **PWA & Service Worker** — เครื่องเล่นแบบ offline-friendly

---

## 6) บทที่ 3 — การวิเคราะห์และออกแบบระบบ

### 6.1 สถาปัตยกรรมระบบ (System Architecture)
ระบบแยกเป็น 4 ส่วนหลัก เชื่อมกันดังนี้ (อ้างอิง `docs/architecture.md`):

```
Admin UI (Next.js) ──HTTPS──▶ Backend API (FastAPI) ──SQL──▶ PostgreSQL
                                      │  └────Redis────▶ Redis
                                      │ enqueue
                                      ▼
                                Worker (Arq) ──S3 API──▶ MinIO (media)
                                      ▲
                                      │ manifest + media (pull)
                          ┌───────────┼───────────┐
                       Player 1    Player 2   Player N
                     (Android)    (RPi PWA)     ...
                          │ HDMI-CEC / RS-232
                          ▼
                         TV
```

**รูปแบบการออกแบบสำคัญ (Key Patterns):**
- **Pre-computed Manifest** — Backend สร้าง JSON ต่อ player → player cache local → render (ทำงานต่อได้แม้เน็ตหลุด)
- **ลำดับชั้น 5 ระดับ** — Content → Presentation → Plan → PlayerGroup → Player
- **Device JWT แยกจาก User JWT** — โทเค็นคนละชุด, อายุต่างกัน (user 30 นาที / device 1 ปี)
- **Worker เดียวรวมงานเบื้องหลัง** — ใช้ Arq จัดการ background jobs

### 6.2 การวิเคราะห์ผู้ใช้และสิทธิ์ (RBAC 7 บทบาท)
อ้างอิง `backend/app/models/user.py`:

| บทบาท (Role) | สิทธิ์โดยสรุป |
|---|---|
| `super_admin` | จัดการผู้ใช้ + ทำได้ทุกอย่าง |
| `admin` | ทำได้ทุกอย่าง ยกเว้นจัดการผู้ใช้ |
| `editor` | อัปโหลดสื่อ, สร้าง playlist/schedule (รออนุมัติ) |
| `approver` | อนุมัติ/ปฏิเสธ สื่อ + ตารางเวลา |
| `viewer` | ดูอย่างเดียว + export รายงาน |
| `operator` | ประกาศฉุกเฉิน + สั่ง restart player |
| `device` | โทเค็นเฉพาะของเครื่องเล่น — เรียก player API |

### 6.3 การออกแบบฐานข้อมูล (ER Diagram)
- ดู ER เต็มแบบ Mermaid ที่ `docs/er-diagram.md` (คัดลอกไป render ที่ https://mermaid.live เพื่อ export เป็นภาพใส่เล่ม)
- มี **8 entity หลัก + ตารางเชื่อม M:N** จัดเป็น 5 กลุ่ม:

| กลุ่ม | ตาราง |
|---|---|
| 🔐 Identity & Audit | `users`, `audit_logs` |
| 📺 Devices | `devices`, `player_groups`, `player_group_members` |
| 🎞️ Content & Composition | `contents`, `presentations`, `presentation_zones` |
| 📋 Playlists & Schedules | `plans`, `plan_items`, `schedules` |
| 🚨 Emergency | `emergency_broadcasts` |

> หมายเหตุการออกแบบ: `audit_logs` และ `emergency_broadcasts` ตั้งใจ **ไม่ผูก FK** กับ `users` เพื่อให้ประวัติคงอยู่แม้ผู้ใช้ถูกลบ (รูปแบบ audit trail / PDPA retention)

### 6.4 ลำดับชั้นเนื้อหา 5 ระดับ (5-Tier Hierarchy)
1. **Content** — สื่อดิบ 1 ชิ้น (ใช้ซ้ำได้หลายที่)
2. **Zone** — 1 zone = 1 content + พารามิเตอร์ ภายใน Layout
3. **Presentation** — Layout + Zones รวมกัน = 1 หน้าจอที่ประกอบแล้ว
4. **Plan** — ลำดับของ Presentation (ปรับ duration ได้)
5. **Schedule** — จับ Plan กับกลุ่มจอ + เวลา + ลำดับความสำคัญ

### 6.5 รายการ API (สรุป — 58 endpoints, 11 กลุ่ม)
อ้างอิง `backend/app/api/v1/endpoints/` (ดู Swagger เต็มที่ `/api/docs`):

| กลุ่ม | Prefix | จำนวน | หน้าที่หลัก |
|---|---|---|---|
| Auth | `/api/v1/auth` | 5 | login, refresh, logout, me |
| Users | `/api/v1/users` | 5 | CRUD ผู้ใช้ + role |
| Devices | `/api/v1/devices` | 6 | pair, list, heartbeat, สถานะ |
| Contents | `/api/v1/contents` | 8 | upload, approve/reject, list |
| Presentations | `/api/v1/presentations` | 5 | จัด layout + zones |
| Plans | `/api/v1/plans` | 5 | จัดลำดับ presentation |
| Schedules | `/api/v1/schedules` | 7 | ตั้งเวลา + อนุมัติ |
| Player (pull) | `/api/v1/player` | 6 | ดึง manifest + media |
| TV Control | `/api/v1/tv-control` | 2 | ส่งคำสั่งคุมทีวี |
| Emergency | `/api/v1/emergency` | 6 | ประกาศฉุกเฉิน |
| Monitoring | `/api/v1/...` | 3 | metrics, audit, readiness |
| Health (meta) | `/healthz`, `/readiness`, `/metrics` | — | liveness / readiness / prometheus |

### 6.6 การควบคุมทีวี (TV Control)
อ้างอิง `backend/app/services/tv_control/base.py`:
- **รองรับ 7 แบบ:** Samsung (MDC), LG (RS-232C), Sony (SimpleIP/IR), Panasonic, NEC, Toshiba และ **HDMI-CEC** (ทีวีทั่วไป)
- **12 คำสั่ง:** power_on, power_off, volume_up, volume_down, mute, unmute, set_volume(0–100), input_hdmi1/2/3, get_status
- คำสั่งถูกส่งผ่าน **Redis queue** ไปยัง player แล้วบันทึกลง audit_log

### 6.7 การออกแบบส่วนติดต่อผู้ใช้ (Admin UI — 13 หน้า)
อ้างอิง `admin-ui/src/app/`:
`login`, `dashboard`, `devices`, `device detail`, `groups`, `contents`, `presentations`, `plans`, `schedules`, `tv-control`, `emergency`, `users`, `audit`

---

## 7) บทที่ 4 — ผลการดำเนินงาน

### 7.1 ผลการพัฒนาตาม Phase
| Phase | สรุปผลที่ทำได้ |
|---|---|
| 0 — Scaffolding | docker-compose + โครงสร้าง service ครบ |
| 1 — Auth & Users | JWT + RBAC 7 บทบาท + 14 tests |
| 2 — Devices & Contents | Pairing + S3 upload + dedupe (sha256) + approval |
| 3 — Plans + Schedules + Manifest | ลำดับชั้น 5 ระดับ + RRULE + priority |
| 4 — TV Control | 7 โปรโตคอล + Redis queue + Web Serial / USB-Serial |
| 5 — Emergency + Monitoring | Override + auto-expire + Prometheus + audit + Sentry + backup |
| 6 — Admin UI | 13 หน้า (Next.js + Tailwind) + auth flow + drag-drop |
| F — Player polish | Zone renderer + carousel + emergency overlay + backoff + LRU cache |

### 7.2 การทดสอบระบบ (Testing)
- มีชุดทดสอบอัตโนมัติ **90 รายการ** (pytest) อยู่ใน `backend/tests/`:

| ไฟล์ทดสอบ | จำนวน | ครอบคลุม |
|---|---|---|
| `test_auth.py` | 15 | login, JWT, RBAC |
| `test_tv_control.py` | 15 | คำสั่งคุมทีวีแต่ละยี่ห้อ |
| `test_phase5_rest.py` | 11 | monitoring/emergency rest |
| `test_sentry_scrub.py` | 11 | ปกปิดข้อมูลอ่อนไหวใน log |
| `test_cookie_auth.py` | 10 | httpOnly cookie auth |
| `test_security_middleware.py` | 8 | security header / rate limit |
| `test_audit_emergency.py` | 6 | audit + emergency |
| `test_content_pipeline.py` | 6 | upload → approve |
| `test_devices.py` | 5 | pairing + heartbeat |
| `test_health.py` | 3 | liveness/readiness |
| **รวม** | **90** | |

- **วิธีรันทดสอบ:** `bash scripts/run-e2e.sh` (build → start → รอ healthy → pytest → smoke E2E)

### 7.3 ภาพหน้าจอผลงาน (ต้องแคปใส่เล่ม) — ดูรายการในข้อ 11

---

## 8) บทที่ 5 — สรุปผลและข้อเสนอแนะ

### 8.1 สรุปผลการดำเนินงาน
- พัฒนาระบบจัดการจอประชาสัมพันธ์ได้ครบตามวัตถุประสงค์ Phase 0–6 + Player polish
- ครอบคลุม Backend API 58 endpoint, Admin UI 13 หน้า, Player ทั้ง Web (PWA) และ Android
- ผ่านชุดทดสอบอัตโนมัติ 90 รายการ

### 8.2 ปัญหาและอุปสรรค 【เรียบเรียงจากประสบการณ์จริง — ตัวอย่าง】
- การเชื่อมต่อ/สั่งงานทีวีต่างยี่ห้อใช้โปรโตคอลต่างกัน ต้องออกแบบ abstraction รวม
- การทำให้ player ทำงานต่อได้เมื่อเครือข่ายหลุด (ใช้ manifest cache + backoff)
- การจัดการสิทธิ์/อนุมัติให้ครบทุกบทบาทโดยไม่ซับซ้อนเกินไป

### 8.3 ข้อเสนอแนะ / การพัฒนาต่อ (Phase 7+)
- ทำ HDMI-CEC native บนฮาร์ดแวร์จริง, httpOnly cookie auth, i18n
- ตั้ง CI/CD + security hardening (nginx + Let's Encrypt)
- เพิ่ม telemetry history, tagging เนื้อหา, PDPA consent (อ้างอิง `docs/er-diagram.md` §8)

### 8.4 ความรู้ที่ได้รับ 【กรอกเอง — เรียบเรียงเอง】
- ตัวอย่าง: การออกแบบ REST API, การออกแบบฐานข้อมูลเชิงสัมพันธ์, Docker, async Python, การควบคุมฮาร์ดแวร์ผ่าน serial/CEC, การทำงานเป็นทีมด้วย Git

---

## 9) บรรณานุกรม (References — ตัวอย่างรายการที่ควรมี)
- FastAPI Documentation — https://fastapi.tiangolo.com
- SQLAlchemy 2.0 Documentation — https://docs.sqlalchemy.org
- PostgreSQL 16 Documentation — https://www.postgresql.org/docs/
- Redis Documentation — https://redis.io/docs/
- MinIO Documentation — https://min.io/docs/
- Next.js Documentation — https://nextjs.org/docs
- RFC 5545 (iCalendar) — https://datatracker.ietf.org/doc/html/rfc5545
- Docker Documentation — https://docs.docker.com
> จัดรูปแบบอ้างอิงตามที่สถาบันกำหนด (APA / IEEE)

---

## 10) ภาคผนวก (Appendix — เนื้อหาพร้อมใช้)

### ภาคผนวก ก — คู่มือติดตั้งและรันระบบ
```bash
cp .env.example .env            # แก้ JWT_SECRET_KEY ก่อน production
docker compose up -d --build    # auto-migrate + auto-seed admin

curl http://localhost:8000/healthz             # liveness
open http://localhost:8000/api/docs            # Swagger UI
open http://localhost:3000                     # Admin UI (admin / ChangeMe123!)
open http://localhost:9001                     # MinIO console (minioadmin/minioadmin)
```
ใส่ข้อมูล demo: `docker compose exec backend python -m app.scripts.seed_demo`

### ภาคผนวก ข — บัญชีทดสอบ (จาก seed_demo)
- `admin / ChangeMe123!` (super_admin)
- `editor1`, `approver1`, `operator1` (สำหรับทดสอบ RBAC)

### ภาคผนวก ค — ตัวแปรสภาพแวดล้อมสำคัญ (`.env.example`)
| ตัวแปร | ความหมาย |
|---|---|
| `DATABASE_URL` | การเชื่อมต่อ PostgreSQL (asyncpg) |
| `REDIS_URL` | การเชื่อมต่อ Redis |
| `S3_ENDPOINT` / `S3_BUCKET` | MinIO object storage |
| `JWT_SECRET_KEY` | กุญแจเซ็น JWT (ต้องเปลี่ยนก่อน production) |
| `DEVICE_TOKEN_SECRET` | กุญแจโทเค็นเครื่องเล่น (แยกจาก user) |
| `APP_TIMEZONE` | Asia/Bangkok |
| `RATE_LIMIT_*` / `CSRF_ENABLED` | การ hardening ความปลอดภัย |

### ภาคผนวก ง — ตาราง API เต็ม
- คัดจาก Swagger UI (`/api/docs`) หรือสรุปจากข้อ 6.5

### ภาคผนวก จ — ER Diagram
- คัดบล็อก Mermaid จาก `docs/er-diagram.md`

---

## 11) รายการภาพประกอบที่ต้องแคปหน้าจอ (List of Figures)
- ☐ รูปที่ 1 — แผนภาพสถาปัตยกรรมระบบ (จากข้อ 6.1)
- ☐ รูปที่ 2 — ER Diagram (export จาก mermaid.live)
- ☐ รูปที่ 3 — ลำดับชั้นเนื้อหา 5 ระดับ
- ☐ รูปที่ 4 — หน้า Login
- ☐ รูปที่ 5 — หน้า Dashboard
- ☐ รูปที่ 6 — หน้าจัดการอุปกรณ์ (Devices) + รายละเอียดจอ
- ☐ รูปที่ 7 — หน้าอัปโหลด/อนุมัติเนื้อหา (Contents)
- ☐ รูปที่ 8 — หน้าจัด Presentation (Layout + Zones)
- ☐ รูปที่ 9 — หน้า Plans
- ☐ รูปที่ 10 — หน้า Schedules (ตั้งเวลา/RRULE)
- ☐ รูปที่ 11 — หน้า TV Control
- ☐ รูปที่ 12 — หน้า Emergency Broadcast
- ☐ รูปที่ 13 — หน้า Users (RBAC)
- ☐ รูปที่ 14 — หน้า Audit Log
- ☐ รูปที่ 15 — Swagger UI (`/api/docs`)
- ☐ รูปที่ 16 — Player แสดงผลบนจอจริง
- ☐ รูปที่ 17 — ผลการรัน pytest (90 ผ่าน)

## 12) รายการตาราง (List of Tables)
- ☐ ตารางที่ 1 — Tech Stack (ข้อ 5.2)
- ☐ ตารางที่ 2 — บทบาทผู้ใช้ RBAC (ข้อ 6.2)
- ☐ ตารางที่ 3 — สรุป API ตามกลุ่ม (ข้อ 6.5)
- ☐ ตารางที่ 4 — คำสั่ง/ยี่ห้อทีวีที่รองรับ (ข้อ 6.6)
- ☐ ตารางที่ 5 — ผลการพัฒนาตาม Phase (ข้อ 7.1)
- ☐ ตารางที่ 6 — สรุปการทดสอบ (ข้อ 7.2)

---

## 13) แหล่งอ้างอิงภายในโปรเจกต์ (ไว้ตรวจย้อน)
| ต้องการข้อมูล | ดูที่ |
|---|---|
| ภาพรวม + Quick Start | `README.md` |
| สถาปัตยกรรม | `docs/architecture.md` |
| ER / ฐานข้อมูล | `docs/er-diagram.md` |
| API | `docs/api.md` + Swagger `/api/docs` |
| การ deploy | `docs/deployment.md`, `docs/production-deployment.md` |
| โมเดลข้อมูล | `backend/app/models/` |
| ตรรกะธุรกิจ | `backend/app/services/` |
| คำสั่งคุมทีวี | `backend/app/services/tv_control/base.py` |
| หน้าเว็บ Admin | `admin-ui/src/app/` |
| เครื่องเล่น | `player/web/`, `player/android/` |
| ชุดทดสอบ | `backend/tests/` |
</content>
</invoke>
