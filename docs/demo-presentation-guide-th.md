# 🎤 คู่มือเตรียมนำเสนอ + สาธิต (Demo / Presentation Guide)
> ระบบจัดการจอประชาสัมพันธ์ (Digital Signage Management System)
> ใช้สำหรับวันสอบ/นำเสนอโครงงาน — เตรียมล่วงหน้า + สคริปต์เดโม + แผนสำรอง

---

## 0. สรุปสั้น: ต้องเตรียมอะไรบ้าง (Checklist)

| # | ของที่ต้องมี | หมายเหตุ |
|---|---|---|
| ☐ | **โน้ตบุ๊ก** ที่มี **Docker Desktop** | หัวใจของเดโม — ต้องเปิดได้ก่อนขึ้นเวที |
| ☐ | โปรเจกต์ `Project-intern` + `backend/.venv` + `pyserial` | ครบแล้วในเครื่องนี้ |
| ☐ | **Chrome หรือ Edge** | สำหรับ Admin UI + web player |
| ☐ | **อินเทอร์เน็ต** (มือถือ tether ก็ได้) | ใช้โหลด content เดโม (example.com); ถ้าไม่มี → ใช้ Emergency text (ข้อ 4.5) |
| ☐ | **สาย/ปลั๊ก + จอ/โปรเจกเตอร์** ของห้องสอบ | เทสต่อจอก่อน |
| ☐ | (option) **com0com** ติดตั้งแล้ว | สำหรับเดโม virtual serial — ดู `emulator/README.md` |
| ☐ | (option) **player/TV จริง** | ถ้ามี → เดโม hardware จริงได้ (ดูข้อ 6) |
| ☐ | **Slide + เล่มรายงาน + ภาพ architecture** | ภาพบรีฟ 5 กล่อง (DB/Web Server/Admin/IPTV/Signage) |
| ☐ | **Screenshot สำรอง** | `user-test-demo/login-e2e.png`, `webplayer-e2e.png` (เผื่อสดพัง) |

> ⚠️ **ซ้อมจริงเต็มรอบอย่างน้อย 1 ครั้งก่อนวันสอบ** บนเครื่อง + เน็ตเดียวกับที่จะใช้

---

## 1. ขั้นตอนเปิดระบบก่อนนำเสนอ (Startup — ทำก่อนขึ้นเวที ~10 นาที)

> ทำตามลำดับ เปิด PowerShell ที่โฟลเดอร์ `E:\Claude-WorkSpace\Project-intern`

```powershell
# (1) เปิด Docker Desktop (รอ ~30s ให้ daemon พร้อม) แล้วสตาร์ททั้ง stack
docker compose up -d
#    รอจน backend healthy:
#    docker compose ps   → ทุกตัวต้อง running / healthy

# (2) เช็คว่าระบบพร้อม (E2E 10 ขั้น ต้องเขียวหมด)
$env:PYTHONUTF8="1"
backend\.venv\Scripts\python.exe scripts\smoke_e2e.py http://localhost:8000

# (3) เสิร์ฟ web player (จอจำลอง) — เปิดหน้าต่าง PowerShell ค้างไว้
backend\.venv\Scripts\python.exe -m http.server 8080 --directory player\web

# (4) สร้าง content เดโม + ได้ pairing code (เปิดอีกหน้าต่าง)
cd emulator
..\backend\.venv\Scripts\python.exe _webplayer_setup.py      # → จด PAIR_CODE ที่พิมพ์ออกมา
```

เปิดแท็บเบราว์เซอร์เตรียมไว้:
- **Admin UI** → http://localhost:3000  (login `admin` / `ChangeMe123!`)
- **Web player (จอ)** → http://localhost:8080  (ใส่ server `http://localhost:8000` + PAIR_CODE)
- (สำรอง) Swagger API → http://localhost:8000/api/docs

> หมายเหตุสภาพแวดล้อมปัจจุบัน: `.env` ตั้ง DB เป็น Postgres + เปิด CORS ให้ :8080 + `NEXT_PUBLIC_API_URL=http://backend:8000/api` แล้ว
> ถ้ารันคู่กับโปรเจกต์ `concert-*` จะมี `docker-compose.override.yml` กันพอร์ตชนอยู่ (ปล่อยไว้ได้)

---

## 2. โครงการนำเสนอ (เล่าให้ตรงบรีฟ)

เปิดด้วย **ภาพ architecture 5 กล่อง** แล้วบอกว่าโครงงานครอบ:
- **วัตถุประสงค์ 1–3** → ระบบจัดการ PR จากศูนย์กลาง, stack ทันสมัย, นำ HDMI-CEC/RS-232 มาใช้
- **สิ่งที่ทำ 1** → player เชื่อมต่อผ่าน LAN
- **สิ่งที่ทำ 2** → player แสดงผล + ควบคุม TV ผ่าน HDMI/Serial

แล้วสาธิตทีละข้อตามลำดับด้านล่าง (โยงกลับบรีฟทุกครั้ง)

---

## 3. สคริปต์เดโม — ระบบจัดการ (วัตถุประสงค์ 1–3)

**Admin UI** (http://localhost:3000):
1. Login → โชว์ **แดชบอร์ด** (มีเมนู: จอ / กลุ่มจอ / สื่อ / Presentations / Playlists / ตารางเล่น / ควบคุมจอ TV / ฉุกเฉิน / Audit / ผู้ใช้)
2. **สื่อ (Content)** → อัปโหลด/ใส่ URL → กระบวนการอนุมัติ (draft → pending → approved)
3. **Presentations** → จัด layout/zone → **Playlists** → **ตารางเล่น** ผูกกลุ่มจอ + เวลา
4. พูดถึง **RBAC 7 roles + Audit log** (จุดเด่นด้านความปลอดภัย/ตรวจสอบได้)

---

## 4. สคริปต์เดโม — "สิ่งที่ทำ" (หัวใจของการให้คะแนน)

### 4.1 สิ่งที่ทำ 1 + 2a — player เชื่อมต่อ LAN + แสดงผล (จอจริงในเบราว์เซอร์)
1. เปิด http://localhost:8080 → กรอก `http://localhost:8000` + PAIR_CODE → **Pair**
2. จอจะ **pair ผ่าน LAN → ดึง manifest → แสดงเนื้อหาเต็มจอ** (info-bar ล่างขวาโชว์ `items=1`)
3. พูด: "เครื่องเล่นเชื่อมผ่าน LAN ทั้งหมด และแสดงผลข้อมูลตามตารางที่ตั้งจาก Admin" ✔ ตรงสิ่งที่ทำ 1+2a

### 4.2 สิ่งที่ทำ 2b — ควบคุม TV ผ่าน Serial/HDMI (Emulator — ไม่ต้องมี TV จริง)
เปิด PowerShell ที่ `emulator/`:
```powershell
$env:PYTHONUTF8="1"
..\backend\.venv\Scripts\python.exe emulated_player.py --brand samsung
```
จะเห็น: admin สั่ง power_on / input / volume / mute → backend สร้าง **byte จริง** (เช่น `aa1100010113`) → Virtual TV เปลี่ยนสถานะตาม
- เปลี่ยนยี่ห้อได้: `--brand lg` / `sony` / `panasonic` / `cec` (โชว์ว่ารองรับหลายโปรโตคอล)
- พูด: "byte ที่เห็น = byte จริงที่จะยิงเข้า Serial Port ของ TV" ✔ ตรงสิ่งที่ทำ 2b

### 4.3 (เต็มสูบ) Virtual Serial ผ่าน com0com — byte วิ่งผ่าน COM port จริง
ถ้าติดตั้ง com0com (COM10↔COM11) แล้ว (ดู `emulator/README.md` ข้อ Demo D):
```powershell
# หน้าต่าง 1
..\backend\.venv\Scripts\python.exe tv_emulator.py --port COM11 --brand samsung
# หน้าต่าง 2
..\backend\.venv\Scripts\python.exe emulated_player.py --brand samsung --serial-out COM10
```
หน้าต่าง 1 (Virtual TV) อัปเดตตามคำสั่งที่วิ่งผ่าน **serial port จริง** — น่าเชื่อถือสุดสำหรับ "ผ่าน Serial Port"

### 4.4 (option) HDMI-CEC stub
```powershell
..\backend\.venv\Scripts\python.exe cec_helper_stub.py   # แล้วโชว์ Admin สั่ง brand=cec
```

### 4.5 Emergency override (จุดเด่น + เป็น fallback ตอนเน็ตล่ม)
- ใน Admin UI → ฉุกเฉิน → สร้างข้อความ (kind=text, ใส่สี) → **activate**
- จอ web player จะขึ้น **overlay แดงเต็มจอทับทุกอย่างทันที** (ไม่ต้องใช้เน็ต — ใช้เป็น demo "แสดงผล" สำรองได้)

---

## 5. แผนสำรอง (ถ้าสดพัง)

| ปัญหา | ทางแก้ |
|---|---|
| เน็ตล่ม → content example.com ไม่ขึ้น | ใช้ **Emergency text** (ข้อ 4.5) แทน — ไม่ต้องใช้เน็ต |
| Docker เปิดไม่ขึ้น / ช้า | เปิด **screenshot สำรอง** `user-test-demo/login-e2e.png`, `webplayer-e2e.png` |
| com0com มีปัญหา | ใช้โหมด **in-process** (4.2) แทน — ได้ผลเหมือนกัน |
| ทุกอย่างพัง | อัด **วิดีโอเดโม** ไว้ล่วงหน้า (ซ้อมรอบที่ work แล้วอัดจอ) |

---

## 6. (ถ้ามี hardware จริง) — ปิดช่องว่างบรีฟให้สมบูรณ์
1. player จริง (Android box / RPi เปิด `player/web` แบบ kiosk) ต่อ LAN เดียวกับ backend → pair
2. ต่อ TV จริงผ่าน **RS-232** (สาย serial + USB-serial adapter) และ/หรือ **HDMI-CEC** (สาย HDMI)
3. สั่ง power/input จาก Admin → TV จริงตอบสนอง
4. ยืนยันยี่ห้อ TV ของหน่วยงานอยู่ในลิสต์ที่รองรับ (Samsung/LG/Sony/Panasonic/NEC/Toshiba/CEC)

---

## 7. สิ่งที่ต้องพูดเรื่อง Emulator (ความซื่อสัตย์ทางวิชาการ)
> "การทดสอบควบคุม TV ทำผ่าน **emulator/virtual device** ซึ่งพิสูจน์ว่า **โปรโตคอลและซอฟต์แวร์ถูกต้อง** (byte ที่ส่งออกตรงสเปกของแต่ละยี่ห้อ) — การทดสอบกับ TV รุ่นจริงเป็นขั้นถัดไป (future work) เมื่อมีอุปกรณ์"

ระบุให้ชัดในเล่ม/สไลด์ว่าผลทดสอบส่วน TV control เป็น virtual device — จะได้ไม่ถูกจับผิดว่าอ้างเกินจริง

---

## 8. คำถามที่อาจโดนถาม (เตรียมคำตอบ)
- **ทำไมเลือก stack นี้ (FastAPI/Next.js/Postgres/Redis/MinIO)?** → OSS ฟรี, async, modern, scale ได้
- **ความปลอดภัย?** → JWT + RBAC 7 roles, device token แยก, audit log, SSRF guard, อนุมัติ content
- **IPTV ในบรีฟอยู่ตรงไหน?** → ระบบรองรับ content แบบ `stream` (RTSP/HLS) ผ่าน player เดียวกัน; ยังไม่ได้แยก IPTV เป็น subsystem เฉพาะ (จุดต่อยอด)
- **ทดสอบกับ TV จริงหรือยัง?** → ตอบตามข้อ 7 (emulator ก่อน, hardware เป็น future work)
- **รองรับกี่จอ?** → ออกแบบ ~10–20 จอ (POC) ขยายผ่าน player group ได้
- **ออฟไลน์ได้ไหม?** → player ดึง manifest มา cache + LRU + backoff → เน็ตหลุดยังเล่นต่อได้

---

## 9. หลังจบเดโม (เก็บของ)
```powershell
cd E:\Claude-WorkSpace\Project-intern
# ลบ demo device ที่สร้าง (ถ้าจำ DEVICE_ID ได้)
emulator\..\backend\.venv\Scripts\python.exe emulator\_webplayer_setup.py --cleanup <DEVICE_ID>
docker compose down        # หยุด stack (ข้อมูลใน Postgres คงอยู่)
```
