# ✅ TODO — Backend (เรา)

> เจ้าของ: **เรา** · ขอบเขต: backend + DB + workers + TV/LED protocol + Android player + emulator + DevOps + hardware
> สถานะโค้ด: เสร็จแล้ว (142 tests ผ่าน, smoke 10/10 บน Postgres เมื่อ 2026-06-16) — งานที่เหลือคือ "ยืนยัน + hardware + เล่ม"

---

## A. ยืนยันระบบยังเขียว (ทำก่อนเลย ใช้เวลาน้อย)
- [ ] รัน unit test: `cd backend; .venv\Scripts\python.exe -m pytest -q` → ต้อง **142 passed**
- [ ] รัน integration: `docker compose up -d --build` แล้ว `backend\.venv\Scripts\python.exe scripts\smoke_e2e.py http://localhost:8000` → **10/10**
  - ⚠️ gotcha: port ชน stack `concert-*` (5432/6379/9000/9001) — มี `docker-compose.override.yml` ปิด host-port ให้แล้ว ไม่ต้องแก้
  - ⚠️ `.env` บรรทัด DATABASE_URL ต้องชี้ Postgres (ไม่ใช่ sqlite) — เคยมีบั๊กชี้ผิด
- [ ] เปิดดู Swagger `http://localhost:8000/api/docs` ว่า endpoint ครบ (ใช้เป็นหลักฐานในเล่มได้)

## B. Hardware bring-up (งานหลักที่เหลือของฝั่งเรา)
- [ ] Build APK จาก `player/android/` (เปิด Android Studio → build)
- [ ] ทดสอบบน Android TV จริง: pair (6-digit) → heartbeat → ดึง manifest → render
- [ ] ทดสอบ RS-232 กับ TV จริงผ่าน USB-serial (chip CH340/CP2102/FTDI/PL2303):
  - [ ] Samsung MDC (power/volume/HDMI) · [ ] LG · [ ] ยี่ห้ออื่นเท่าที่มีจอ
- [ ] ทดสอบ HDMI-CEC ผ่าน cec helper (`tv-control/` + `player/web` cec integration)
- [ ] LED controller จริง — protocol ตอนนี้เป็น **generic** ต้องปรับตาม spec บอร์ดจริง (`led_control/base.py`)
- [ ] **ถ้าไม่มี hardware:** ใช้ `emulator/` (tv_emulator + emulated_player + cec stub) เป็นหลักฐานแทน — verify in-process round-trip ผ่านแล้ว → ระบุในเล่มชัดว่าเป็น **simulation/emulator** ไม่ใช่จอจริง

## C. Go-live / Security (เฉพาะถ้าต้อง deploy จริง — ดู SECURITY.md + installation-guide-th.md)
- [ ] rotate secrets ใน `.env` (JWT_SECRET, SEED_ADMIN_PASSWORD)
- [ ] เปิด HTTPS (nginx TLS) + ClamAV (`ANTIVIRUS_ENABLED`) + Sentry DSN
- [ ] ตั้ง backup timer (`scripts/backup.sh` / `backup.ps1`)

## D. เล่มรายงาน — ส่วน Backend
- [ ] ch2: tech stack ฝั่ง server (FastAPI / Postgres / Redis / Arq / MinIO / Docker) + RS-232/CEC theory
- [ ] ch3: architecture diagram (3-tier) + ER diagram + API/manifest design + hierarchy 5 ชั้น
- [ ] ch4: ผล test (142 unit + smoke 10/10) + ผลทดสอบ hardware/emulator
- [ ] ch1 + ch5: เขียนร่วมกับแฟน (ภาพรวม + สรุป)

## E. Git ค้าง
- [ ] commit `project-book-prep/` (ยัง untracked) + `admin-ui/tsconfig.tsbuildinfo`

---
**Minor (ไม่กระทบใช้งาน):** `docker-compose.yml` มี `version:` ตกยุค · `/emergency` มี 307 redirect · upload response `size_bytes=None`
