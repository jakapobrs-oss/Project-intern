# 📕 โครงเล่มรายงานสหกิจศึกษา (5 บท) — Backbone

> **เรื่อง:** ระบบจัดการจอประชาสัมพันธ์ดิจิทัล (Digital Signage Management System)
> **รูปแบบ:** อิงเล่มสหกิจฯ ของเดชธนา นาเมืองรักษ์ (5 บท + ส่วนหน้า + ภาคผนวก)
> **สร้าง:** 2026-06-19 · ใช้เป็น backbone เติมเนื้อหาทีละบท
> เครื่องหมาย `[ ]` = ยังต้องเติม · `[x]` = มีวัตถุดิบแล้ว

---

## 🔢 ข้อเท็จจริงล่าสุด (refreshed จากโค้ดจริง 2026-06-19 — ใช้เลขชุดนี้ในเล่ม)

| รายการ | ค่า | หมายเหตุ |
|---|---|---|
| API endpoints | **66** | นับจาก `@router.*` ใน `backend/app/api/v1/endpoints/` |
| API groups | **13** | /auth /users /devices /groups /contents /presentations /plans /schedules /player /tv /emergency /led /reports (+monitoring ที่ root) |
| ตารางฐานข้อมูล | **12 entity + 1 M:N** = ~13 | __tablename__ 12 ตัว (รวม playback_logs ใหม่) + association player↔group — *ตรวจซ้ำ association* |
| Migrations | **5** | 0001–0005 (0005 = playback_logs) |
| Test cases | **133** ใน **15 ไฟล์** | pytest (เดิม 90/9) |
| RBAC roles | 7 | super_admin/admin/editor/approver/viewer/operator/device |
| Player platforms | Android TV/tablet, RPi kiosk, Windows, Web PWA | |

**ฟีเจอร์ที่เพิ่มหลัง material เก่า (ต้องเขียนเพิ่มในเล่ม):** LED control (`/led` + `led_control/`), Reporting (`/reports` + `report_service`/`report_export` + `playback_logs`), SSRF guard (`url_guard`), ClamAV antivirus scan, schedule conflict-eval, async workers (content/device/report/session)

---

## 📐 โครงเล่ม

### ส่วนหน้า (Front matter) — เลขหน้า ก/ข/ค
- [ ] **ปกนอก/ปกใน** — ชื่อเรื่อง (ไทย+อังกฤษ), ชื่อ-รหัสนักศึกษา, สาขา/คณะ/สถาบัน, สถานประกอบการที่ฝึก, ปีการศึกษา → *รอข้อมูลจาก user*
- [ ] **หน้าอนุมัติ** — อาจารย์ที่ปรึกษา + กรรมการ (เส้นประลายเซ็น) → *รอข้อมูล*
- [ ] **บทคัดย่อ (ภาษาไทย)** — ~1 หน้า สรุประบบ+ผล (ฐาน: material §1)
- [ ] **ABSTRACT (English)** — แปลจากบทคัดย่อไทย
- [ ] **กิตติกรรมประกาศ** — ขอบคุณสถานประกอบการ/อาจารย์ → *รอข้อมูล*
- [x] **สารบัญ / สารบัญรูปภาพ / สารบัญตาราง** — gen อัตโนมัติตอน layout

### บทที่ 1 บทนำ — `ch1-intro.md` ✅ (ร่างแล้ว)
- 1.1 ความเป็นมาและความสำคัญของโครงงาน
- 1.2 วัตถุประสงค์ของโครงงาน (6 ข้อ)
- 1.3 ขอบเขตของโครงงาน (1.3.1–1.3.6)
- 1.4 ประโยชน์ที่คาดว่าจะได้รับ

### บทที่ 2 ทฤษฎีและเทคโนโลยีที่เกี่ยวข้อง — `ch2-theory.md` [ ]
> แต่ละหัวข้อ: นิยาม + บทบาทในระบบนี้ + รูปประกอบ (โลโก้/แผนภาพ) แบบเดชธนา
- 2.1 ระบบ Digital Signage (แนวคิด/องค์ประกอบ)
- 2.2 FastAPI & Python 3.12 (async API)
- 2.3 PostgreSQL & SQLAlchemy/Alembic
- 2.4 Next.js + TypeScript + Tailwind CSS
- 2.5 Redis & Arq (cache + queue งานเบื้องหลัง)
- 2.6 MinIO (object storage S3-compatible)
- 2.7 Docker & Containerization
- 2.8 HDMI-CEC & RS-232 (การควบคุมทีวีระยะไกล)
- 2.9 ความปลอดภัย: JWT/RBAC, ClamAV, SSRF guard *(หัวข้อใหม่)*
- รูปที่ต้องใช้: 2.1–2.9 (โลโก้/ไดอะแกรมของแต่ละเทคโนโลยี)

### บทที่ 3 การวิเคราะห์และออกแบบระบบ — `ch3-design.md` [ ]
- 3.1 การวิเคราะห์ความต้องการ (functional/non-functional) + **Gantt chart** `[ ] ต้องทำรูป`
- 3.2 เครื่องมือที่ใช้พัฒนา
  - 3.2.1 ฮาร์ดแวร์ · 3.2.2 ซอฟต์แวร์ (ดู `tools-list.md`)
- 3.3 การออกแบบระบบ
  - 3.3.1 สถาปัตยกรรมระบบ — 6 ส่วนใน Docker stack `[ ] รูป architecture`
  - 3.3.2 การออกแบบฐานข้อมูล / **ER Diagram** (~13 ตาราง) `[x] มี er-diagram.png/svg`
  - 3.3.3 แนวคิด 5-Tier Content Hierarchy (Content→Zone→Presentation→Plan→Schedule)
  - 3.3.4 การออกแบบ API (66 endpoints / 13 กลุ่ม)
- 3.4 วิธีการพัฒนา (workflow, Git, CI)
- 3.5 การออกแบบการทดสอบ (pytest 133 cases + E2E smoke)

### บทที่ 4 ผลการดำเนินงาน — `ch4-results.md` [ ]
> หัวใจของเล่ม — โชว์ของจริง + screenshot (รูป 4.x) แบบเดชธนา
- 4.1 ภาพรวมระบบที่พัฒนาเสร็จ
- 4.2 โมดูลหลักและความสามารถ (จาก material §8 + ฟีเจอร์ใหม่)
  - Auth & RBAC · Devices · Contents · Presentations · Plans · Schedules · TV Control · Emergency · Monitoring · Player · **LED control** · **Reporting**
- 4.3 หน้าจอ Admin UI (13 หน้า) `[ ] screenshot 4.x`
- 4.4 Player + emergency overlay `[ ] screenshot`
- รูปที่ต้องใช้: 4.1–4.1x (screenshot ทุกหน้าจอหลัก)

### บทที่ 5 สรุปผลและข้อเสนอแนะ — `ch5-conclusion.md` [ ]
- 5.1 สรุปผลการดำเนินงาน
- 5.2 ปัญหาที่พบและแนวทางแก้ไข
- 5.3 ข้อเสนอแนะและการพัฒนาต่อยอด (Phase 7)
- (+ สิ่งที่ได้เรียนรู้จากการฝึกงาน)

### ส่วนท้าย (Back matter)
- [ ] **บรรณานุกรม** — แหล่งอ้างอิงเทคโนโลยี (ดู `tools-list.md`) + เว็บ
- [ ] **ภาคผนวก** — คู่มือติดตั้ง (`docs/installation-guide-th.md`), data dictionary (`data-dictionary.md`), คู่มือผู้ดูแล (`docs/admin-manual-th.md`), screenshot เพิ่มเติม

---

## 📦 บัญชีวัตถุดิบ (Asset inventory)

| สถานะ | รายการ | ที่อยู่ |
|---|---|---|
| ✅ มีแล้ว | เนื้อหา 14 หัวข้อ | `internship-book-materials.md` |
| ✅ มีแล้ว | ER diagram (png/svg/mmd) | `assets/er-diagram.*` |
| ✅ มีแล้ว | Data dictionary | `data-dictionary.md` |
| ✅ มีแล้ว | รายการเครื่องมือ | `tools-list.md` |
| ✅ มีแล้ว | คู่มือ 6 ฉบับ | `docs/*.md` |
| ✅ บางส่วน | screenshot login/player | `user-test-demo/` (gitignored) |
| ⚠️ ต้องทำ | screenshot Admin UI 13 หน้า | รัน app + ถ่าย (มี pipeline `web-demos/shot.mjs`) |
| ⚠️ ต้องทำ | Gantt chart / timeline | บทที่ 3 |
| ⚠️ ต้องทำ | รูปโลโก้เทคโนโลยี บท 2 | 2.1–2.9 |
| ⚠️ รอ user | ข้อมูลหน้าปก + อาจารย์ที่ปรึกษา + สถานประกอบการ | — |

---

## ▶️ สถานะการร่าง
- [x] บทที่ 1 — `ch1-intro.md`
- [ ] บทที่ 2–5
- [ ] ส่วนหน้า (บทคัดย่อ/ABSTRACT)
- [ ] รวมเล่ม + จัด format (.docx ตามเดชธนา) + ใส่รูป
