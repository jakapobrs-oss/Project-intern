# 📒 Data Dictionary — Digital Signage Management System

> พจนานุกรมข้อมูล: อธิบายทุกตารางในฐานข้อมูลและรายละเอียดของแต่ละคอลัมน์
> ที่มา: สังเคราะห์จาก SQLAlchemy models จริงใน `backend/app/models/`
> อัปเดต: 2026-05-29 · ฐานข้อมูล PostgreSQL 16 (dev: SQLite)

**สรุปจำนวน:** 12 ตาราง = 11 mapped entity tables + 1 association table
**คำย่อ:** PK = Primary Key · FK = Foreign Key · UK = Unique Key · `?` = nullable (อนุญาตค่าว่าง)

---

## กลุ่มที่ 1 — 🔐 Identity & Audit

### ตาราง `users` — ผู้ใช้ระบบ admin (ไม่รวม player device)

เก็บข้อมูลบัญชีผู้ใช้ที่เข้าระบบจัดการ พร้อมระบบสิทธิ์ (RBAC) และกลไกล็อกบัญชี

| คอลัมน์ | ชนิด | คีย์/เงื่อนไข | คำอธิบาย |
|---|---|---|---|
| id | UUID | PK | รหัสผู้ใช้ (สุ่มอัตโนมัติ) |
| username | String(64) | UK, index, NOT NULL | ชื่อผู้ใช้สำหรับ login (ห้ามซ้ำ) |
| email | String(255) | UK, index, NOT NULL | อีเมล (ห้ามซ้ำ) |
| password_hash | String(255) | NOT NULL | รหัสผ่านที่ผ่านการ hash (bcrypt) |
| full_name | String(255) | default "" | ชื่อ-นามสกุลจริง |
| role | Enum | NOT NULL, default viewer | บทบาท 7 ระดับ: super_admin / admin / editor / approver / viewer / operator / device |
| is_active | Boolean | default true | บัญชีเปิดใช้งานอยู่หรือไม่ |
| is_locked | Boolean | default false | ผู้ดูแลระบบสั่งล็อกด้วยมือ — ปลดได้ด้วยคนเท่านั้น (§26) |
| failed_login_count | Integer | default 0 | จำนวนครั้งที่ login ผิดติดต่อกัน |
| locked_until | DateTime(tz) | ? | ระบบล็อกชั่วคราวจาก login ผิดเกินกำหนด ถึงเวลานี้แล้วปลดเอง (§26) |
| created_at | DateTime(tz) | NOT NULL | เวลาสร้างบัญชี |
| updated_at | DateTime(tz) | auto-update | เวลาแก้ไขล่าสุด |
| last_login_at | DateTime(tz) | ? | เวลา login ล่าสุด |

**RBAC 7 roles:** super_admin (จัดการ user + ทุกอย่าง) · admin (ทุกอย่างยกเว้น user mgmt) · editor (อัปโหลด content, สร้าง playlist/schedule รอ approve) · approver (อนุมัติ/ปฏิเสธ content+schedule) · viewer (ดู+export) · operator (emergency broadcast + restart player) · device (token เฉพาะของจอ)

---

### ตาราง `audit_logs` — บันทึก action ทั้งหมด (append-only)

บันทึกเหตุการณ์สำคัญทุกอย่างเพื่อ compliance + forensic **ห้าม update/delete** (เขียนอย่างเดียว)

| คอลัมน์ | ชนิด | คีย์/เงื่อนไข | คำอธิบาย |
|---|---|---|---|
| id | UUID | PK | รหัส log |
| actor_type | String(32) | NOT NULL, default "user" | ประเภทผู้กระทำ: user / device / system / anonymous |
| actor_id | String(64) | ?, index, **ไม่มี FK** | รหัสผู้กระทำ (เก็บเป็น string เพื่อให้คงอยู่แม้ user ถูกลบ) |
| actor_label | String(255) | ? | snapshot ชื่อผู้กระทำ ณ เวลานั้น |
| action | String(64) | NOT NULL, index | verb ของการกระทำ เช่น `auth.login`, `content.approve`, `schedule.activate` |
| target_type | String(32) | ? | ประเภทเป้าหมาย เช่น device, content |
| target_id | String(64) | ?, index | รหัสเป้าหมาย |
| outcome | Enum | NOT NULL, default success | ผลลัพธ์: success / fail / denied |
| ip_address | String(45) | ? | IP ผู้กระทำ (รองรับ IPv6) |
| user_agent | String(512) | ? | ข้อมูล browser/client |
| message | Text | ? | ข้อความอ่านง่ายสำหรับมนุษย์ |
| extra | JSON | ? | metadata เพิ่มเติมแบบ structured |
| created_at | DateTime(tz) | NOT NULL, index | เวลาเกิดเหตุการณ์ |

---

## กลุ่มที่ 2 — 📺 Devices

### ตาราง `devices` — จอประชาสัมพันธ์ 1 เครื่อง

เก็บข้อมูลฮาร์ดแวร์ + สถานะ + telemetry ของจอแต่ละจอ

| คอลัมน์ | ชนิด | คีย์/เงื่อนไข | คำอธิบาย |
|---|---|---|---|
| id | UUID | PK | รหัสจอ |
| name | String(128) | index, NOT NULL | ชื่อจอ |
| location | String(255) | default "" | ตำแหน่งติดตั้ง |
| pairing_code | String(16) | UK, index, ? | รหัสจับคู่ 6 หลัก (ตัด 0/O/I/1 ที่สับสน) |
| pairing_code_expires_at | DateTime(tz) | ? | เวลาหมดอายุของรหัสจับคู่ |
| paired_at | DateTime(tz) | ? | เวลาที่จับคู่สำเร็จ |
| device_token_hash | String(255) | ? | hash ของ token จอ (แยกจาก user JWT, revoke ได้) |
| platform | Enum | NOT NULL, default unknown | android_tv / android_tablet / rpi_kiosk / windows_pc / web_browser / unknown |
| mac_address | String(17) | ?, index | MAC address |
| ip_address | String(45) | ? | IP ปัจจุบัน |
| serial_number | String(128) | ? | serial ของเครื่อง |
| tv_brand | String(32) | ? | ยี่ห้อทีวี: samsung / lg / sony / ... |
| tv_model | String(128) | ? | รุ่นทีวี |
| status | Enum | NOT NULL, default unpaired | unpaired / online / offline / error |
| app_version | String(32) | ? | เวอร์ชันแอป player |
| last_heartbeat_at | DateTime(tz) | ? | heartbeat ล่าสุด (ใช้ตัดสิน online/offline) |
| last_manifest_version | String(64) | ? | เวอร์ชัน manifest ที่จอดึงไปล่าสุด |
| cpu_percent | Float | ? | %CPU ล่าสุด (telemetry) |
| temperature_c | Float | ? | อุณหภูมิล่าสุด (°C) |
| uptime_sec | Integer | ? | เวลาทำงานต่อเนื่อง (วินาที) |
| is_active | Boolean | default true | เปิดใช้งานอยู่หรือไม่ |
| created_at / updated_at | DateTime(tz) | | เวลาสร้าง/แก้ไข |

> Telemetry เก็บแค่ค่าล่าสุด — history (time-series) วางไว้ใน phase ถัดไป

---

### ตาราง `player_groups` — กลุ่มของจอ

ใช้ผูกกับ schedule (schedule ผูกกับ "กลุ่ม" ไม่ใช่จอตรง ๆ เพื่อจัดการเป็นชุด)

| คอลัมน์ | ชนิด | คีย์/เงื่อนไข | คำอธิบาย |
|---|---|---|---|
| id | UUID | PK | รหัสกลุ่ม |
| name | String(128) | UK, index, NOT NULL | ชื่อกลุ่ม (ห้ามซ้ำ) |
| description | Text | default "" | คำอธิบาย |
| created_at / updated_at | DateTime(tz) | | เวลาสร้าง/แก้ไข |

---

### ตาราง `player_group_members` — ตารางเชื่อม M:N (association)

จับคู่ device ↔ player_group แบบหลายต่อหลาย (1 จออยู่ได้หลายกลุ่ม, 1 กลุ่มมีหลายจอ)

| คอลัมน์ | ชนิด | คีย์/เงื่อนไข | คำอธิบาย |
|---|---|---|---|
| player_group_id | UUID | PK, FK → player_groups.id (ON DELETE CASCADE) | กลุ่ม |
| device_id | UUID | PK, FK → devices.id (ON DELETE CASCADE) | จอ |

---

## กลุ่มที่ 3 — 🎞️ Content & Composition

### ตาราง `contents` — สื่อ raw (1 record = 1 ไฟล์/URL)

| คอลัมน์ | ชนิด | คีย์/เงื่อนไข | คำอธิบาย |
|---|---|---|---|
| id | UUID | PK | รหัสสื่อ |
| name | String(255) | index, NOT NULL | ชื่อสื่อ |
| description | Text | default "" | คำอธิบาย |
| type | Enum | NOT NULL | image / video / web / stream / text |
| storage_key | String(512) | ? | path ไฟล์บน S3/MinIO (กรณี image/video) |
| mime_type | String(128) | ? | MIME type |
| file_size | BigInteger | ? | ขนาดไฟล์ (byte) |
| sha256 | String(64) | ?, index | hash สำหรับ dedupe (กันอัปโหลดซ้ำ §22) |
| width / height | Integer | ? | ขนาดภาพ/วิดีโอ (px) |
| duration_sec | Float | ? | ความยาว (เฉพาะ video) |
| thumbnail_key | String(512) | ? | path ของ thumbnail |
| url | String(2048) | ? | URL (กรณี web/stream) |
| approval_status | Enum | NOT NULL, default draft | draft / pending / approved / rejected |
| approved_by | UUID | FK → users.id, ? | ผู้อนุมัติ |
| approved_at | DateTime(tz) | ? | เวลาอนุมัติ |
| rejection_reason | Text | ? | เหตุผลที่ปฏิเสธ |
| expires_at | DateTime(tz) | ? | เวลาหมดอายุ (auto-archive) |
| created_by | UUID | FK → users.id, NOT NULL | ผู้สร้าง |
| is_active | Boolean | default true | เปิดใช้งานอยู่หรือไม่ |
| created_at / updated_at | DateTime(tz) | | เวลาสร้าง/แก้ไข |

---

### ตาราง `presentations` — layout/template ที่ compose แล้ว (1 หน้าจอ)

| คอลัมน์ | ชนิด | คีย์/เงื่อนไข | คำอธิบาย |
|---|---|---|---|
| id | UUID | PK | รหัส presentation |
| name | String(255) | index, NOT NULL | ชื่อ |
| description | Text | default "" | คำอธิบาย |
| layout_json | JSON | NOT NULL, default {} | โครงสร้าง layout เช่น `{"template":"split_70_30","zones":[{"key":"main","x":0,"y":0,"w":70,"h":100}]}` |
| duration_sec | Integer | NOT NULL, default 30 | ระยะเวลาแสดงเริ่มต้น (ถ้า plan_item ไม่ override) |
| created_by | UUID | FK → users.id, NOT NULL | ผู้สร้าง |
| created_at / updated_at | DateTime(tz) | | เวลาสร้าง/แก้ไข |

---

### ตาราง `presentation_zones` — 1 ช่อง (zone) ใน layout → ผูกกับ content

| คอลัมน์ | ชนิด | คีย์/เงื่อนไข | คำอธิบาย |
|---|---|---|---|
| id | UUID | PK | รหัส zone |
| presentation_id | UUID | FK → presentations.id (ON DELETE CASCADE), index, NOT NULL | presentation ที่สังกัด |
| zone_key | String(64) | NOT NULL | คีย์ที่ match กับ layout_json |
| content_id | UUID | FK → contents.id, NOT NULL | สื่อที่แสดงใน zone นี้ |
| params_json | JSON | NOT NULL, default {} | พารามิเตอร์เฉพาะ zone เช่น volume, mute, fit_mode |
| order_index | Integer | NOT NULL, default 0 | ลำดับ |

> ลบ presentation → zones ลบตาม (CASCADE) · ห้ามลบ content ที่ยังถูก zone ใช้ (RESTRICT)

---

## กลุ่มที่ 4 — 📋 Playlists & Schedules

### ตาราง `plans` — ลำดับของ presentation (เดิมเรียก "playlist")

| คอลัมน์ | ชนิด | คีย์/เงื่อนไข | คำอธิบาย |
|---|---|---|---|
| id | UUID | PK | รหัส plan |
| name | String(255) | UK, index, NOT NULL | ชื่อ plan (ห้ามซ้ำ) |
| description | Text | default "" | คำอธิบาย |
| created_by | UUID | FK → users.id, NOT NULL | ผู้สร้าง |
| created_at / updated_at | DateTime(tz) | | เวลาสร้าง/แก้ไข |

---

### ตาราง `plan_items` — 1 รายการใน plan

| คอลัมน์ | ชนิด | คีย์/เงื่อนไข | คำอธิบาย |
|---|---|---|---|
| id | UUID | PK | รหัส item |
| plan_id | UUID | FK → plans.id (ON DELETE CASCADE), index, NOT NULL | plan ที่สังกัด |
| presentation_id | UUID | FK → presentations.id, NOT NULL | presentation ที่อ้างถึง |
| order_index | Integer | NOT NULL, default 0 | ลำดับการเล่น |
| duration_sec_override | Integer | ? | override ระยะเวลา (ถ้า null ใช้ของ presentation) |

---

### ตาราง `schedules` — ผูก plan ↔ player_group + เวลา + priority

| คอลัมน์ | ชนิด | คีย์/เงื่อนไข | คำอธิบาย |
|---|---|---|---|
| id | UUID | PK | รหัส schedule |
| name | String(255) | index, NOT NULL | ชื่อ |
| description | Text | default "" | คำอธิบาย |
| plan_id | UUID | FK → plans.id, index, NOT NULL | plan ที่จะเล่น |
| player_group_id | UUID | FK → player_groups.id, index, NOT NULL | กลุ่มจอเป้าหมาย |
| start_at | DateTime(tz) | index, NOT NULL | เวลาเริ่ม |
| end_at | DateTime(tz) | ?, index | เวลาสิ้นสุด (null = ไม่หมดอายุ) |
| repeat_rule | String(512) | ? | กฎเล่นซ้ำแบบ iCal RRULE (§23) |
| daily_window_start | String(8) | ? | เล่นเฉพาะช่วงเวลาในวัน (HH:MM) — day-parting |
| daily_window_end | String(8) | ? | สิ้นสุดช่วงเวลาในวัน (HH:MM) |
| priority | Integer | NOT NULL, default 100, index | เลขมาก = สำคัญกว่า (แก้ conflict) |
| status | Enum | NOT NULL, default draft, index | draft / pending_approval / active / paused / expired |
| created_by | UUID | FK → users.id, NOT NULL | ผู้สร้าง |
| approved_by | UUID | FK → users.id, ? | ผู้อนุมัติ |
| approved_at | DateTime(tz) | ? | เวลาอนุมัติ |
| is_active | Boolean | default true | เปิดใช้งานอยู่หรือไม่ |
| created_at / updated_at | DateTime(tz) | | เวลาสร้าง/แก้ไข |

---

## กลุ่มที่ 5 — 🚨 Emergency

### ตาราง `emergency_broadcasts` — ประกาศฉุกเฉิน override ทุก schedule

| คอลัมน์ | ชนิด | คีย์/เงื่อนไข | คำอธิบาย |
|---|---|---|---|
| id | UUID | PK | รหัสประกาศ |
| title | String(255) | NOT NULL | หัวข้อ |
| kind | Enum | NOT NULL | text / image / url |
| payload | JSON | NOT NULL, default {} | เนื้อหาตาม kind เช่น text: `{"message":"...","bg_color":"#c00"}` · image: `{"content_id":"..."}` · url: `{"url":"...","refresh_sec":60}` |
| target | JSON | NOT NULL, default {} | เป้าหมาย: `{"all":true}` หรือ `{"device_ids":[...]}` หรือ `{"group_ids":[...]}` |
| status | Enum | NOT NULL, default draft | draft / active / expired / cancelled |
| priority | Integer | NOT NULL, default 1000 | สูงกว่า schedule ปกติเสมอ |
| starts_at | DateTime(tz) | ? | เวลาเริ่ม (null = ทันที) |
| ends_at | DateTime(tz) | ? | เวลาสิ้นสุด (null = ไม่หมดอายุ) |
| requires_ack | Boolean | NOT NULL, default false | ต้องให้ operator ยืนยันก่อนส่ง (กันส่งผิด) |
| acknowledged_at | DateTime(tz) | ? | เวลายืนยัน |
| created_by | UUID | NOT NULL, **ไม่มี FK** | ผู้สร้าง (เก็บไว้แม้ user ถูกลบ) |
| notes | Text | ? | หมายเหตุ |
| created_at / updated_at | DateTime(tz) | | เวลาสร้าง/แก้ไข |

---

## ภาคผนวก — นโยบายการลบข้อมูล (Cascade & Deletion)

| ความสัมพันธ์ | ON DELETE | เหตุผล |
|---|---|---|
| player_group_members → player_groups / devices | CASCADE | ตารางเชื่อม ลบตามเมื่อต้น/ปลายหาย |
| presentation_zones → presentations | CASCADE | zone ไม่มีความหมายถ้า presentation หาย |
| plan_items → plans | CASCADE | item ไม่มีความหมายถ้า plan หาย |
| presentation_zones.content_id → contents | RESTRICT | ห้ามลบ content ที่ยังถูกใช้ |
| plan_items.presentation_id → presentations | RESTRICT | ห้ามลบ presentation ที่ยังถูกใช้ |
| schedules.plan_id / player_group_id | RESTRICT | ห้ามลบของที่ยัง schedule อยู่ |
| audit_logs / emergency_broadcasts → users | ไม่มี FK | append-only — ลบ user แล้ว log/ประกาศยังอยู่ |

> ดูเพิ่ม: `er-diagram.md` (แผนผังความสัมพันธ์), `assets/er-diagram.png` (รูป)
