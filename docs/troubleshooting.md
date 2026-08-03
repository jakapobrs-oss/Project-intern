# 🔧 Troubleshooting Guide

> symptom → สาเหตุ → วิธีแก้ — สำหรับ ops/support
> เรียงตามความถี่ที่เจอจริง

---

## จอ / Player

### จอแสดง "Connecting..." ค้าง / ไม่เล่นอะไร
| สาเหตุ | ตรวจ | แก้ |
|---|---|---|
| Player ยัง pair ไม่สำเร็จ | ดู device list ว่า status = unpaired | สร้าง pairing code ใหม่ → กรอกที่ player |
| Server URL ผิด | ดู config บน player | แก้ server_url ให้ตรง (https + port) |
| Network จอออกเน็ตไม่ได้ | ping server จากจอ | เปิด egress 443 จาก VLAN signage |
| ยังไม่มี schedule active | `/api/v1/reports/devices` | สร้าง schedule + approve ให้ active |

### device แสดง offline ทั้งที่จอยังเล่นอยู่
- Player heartbeat ไม่ถึง server (เน็ตขาด/พอร์ตปิด) แต่จอเล่นจาก **cache local** ได้
- ตรวจ `last_heartbeat_at` ใน device report — ถ้าเก่า > 90 วิ ระบบตัดเป็น offline อัตโนมัติ (`heartbeat_aggregator`)
- แก้: เช็ค network ขาออกของ player; ดู log player

### เปลี่ยน content แล้วจอไม่อัปเดต
- Player poll manifest ตาม `cache_seconds` (default 60 วิ) — รอ 1-2 นาที
- ตรวจว่า schedule **active ตอนนี้จริง** — ระบบเช็ค RRULE + daily window (§23):
  schedule "จ-ศ 8:00-17:00" จะไม่เล่นวันเสาร์/นอกเวลา **ถูกต้องแล้ว**
- บังคับ refresh: ดู `last_manifest_version` ของ device เทียบกับ version ปัจจุบัน

---

## Content upload

| อาการ | สาเหตุ | แก้ |
|---|---|---|
| `UNSUPPORTED_TYPE` | magic bytes ไม่ตรง (ไฟล์เสีย/นามสกุลหลอก) | ใช้ไฟล์ JPG/PNG/WebP/GIF/MP4/WebM จริง |
| `FILE_TOO_LARGE` | เกิน 20MB (รูป) / 500MB (วิดีโอ) | ลดขนาด/บีบก่อน upload |
| `UNSAFE_URL` | URL ชี้ IP ภายใน (กัน SSRF §26) | ใช้ URL public เท่านั้น |
| `INFECTED` / `SCAN_UNAVAILABLE` | ClamAV เจอไวรัส / ต่อ clamd ไม่ได้ | ตรวจไฟล์; ถ้า clamd ล่ม ดู `CLAMAV_*` ใน .env |
| ไม่มี thumbnail preview | worker ยังไม่ประมวลผล / Redis ล่ม | ตรวจว่า `worker` container รัน + Redis ติด; thumbnail เป็น background job |

> วิดีโอ codec แปลก/ไฟล์ใหญ่ → worker `transcode_video` แปลงเป็น H.264/AAC ≤1080p อัตโนมัติ (เบื้องหลัง)

---

## TV Control (HDMI-CEC / RS-232)

| อาการ | สาเหตุ | แก้ |
|---|---|---|
| ส่ง power command แล้ว TV ไม่ตอบ | RS-232 ไม่ ack / สาย/baud ผิด | เช็คสาย null-modem, baud 9600 8N1, brand ตรงรุ่น |
| command ค้างใน queue | player ไม่ poll `/player/commands` | เช็ค PlayerService รันอยู่; ดู Redis queue |
| CEC ไม่ทำงานบางจอ | TV ไม่รองรับ CEC | ใช้ RS-232 หรือ smart plug fallback (PLAN §17) |
| สั่งติดกันเร็ว TV รับไม่ทัน | ไม่มี inter-command delay | queue serialize + delay อยู่แล้ว; เพิ่ม cooldown ถ้าจำเป็น |

---

## LED Board

| อาการ | สาเหตุ | แก้ |
|---|---|---|
| `LED_SEND_FAILED` | ต่อ TCP ไป controller ไม่ได้ | เช็ค `ip_address` ของ device + port (default 5200) + ping ได้ไหม |
| ข้อความเพี้ยน/ไม่ขึ้น | protocol/brand ไม่ตรง controller | เลือก `brand` ให้ตรง (generic_tcp/huidu/xixun) ตาม spec จริง |
| ภาษาไทยเพี้ยน | controller ไม่รองรับ UTF-8 | ตรวจ encoding ที่ controller ต้องการ |

---

## Auth / Login

| อาการ | สาเหตุ | แก้ |
|---|---|---|
| login ไม่ได้ "ACCOUNT_LOCKED" | ใส่รหัสผิด 5 ครั้ง | รอ 15 นาที หรือ admin ปลดล็อก (`is_locked=false`) |
| token หมดอายุบ่อย | access token 30 นาที | frontend ใช้ refresh token auto; ตรวจ refresh flow |
| 403 ทำบางอย่างไม่ได้ | role ไม่พอ (RBAC §21) | ตรวจ role matrix — เช่น แค่ admin สั่ง device command |

---

## Infra / Deploy

```bash
# ระบบไม่ healthy
curl http://localhost:8000/api/v1/readiness     # บอกว่า DB ต่อได้ไหม
docker compose ps                                # service ไหนไม่ขึ้น
docker compose logs backend --tail=100           # error ล่าสุด

# migration ค้าง / schema ผิด
docker compose exec backend alembic current      # อยู่ revision ไหน
docker compose exec backend alembic upgrade head # apply ที่ค้าง

# Redis / queue มีปัญหา
docker compose exec redis redis-cli ping         # ต้อง PONG

# MinIO upload fail
curl http://localhost:9001                        # console ขึ้นไหม
```

| อาการ | แก้ |
|---|---|
| `relation ... does not exist` | ยังไม่ migrate → `alembic upgrade head` |
| `column users.locked_until does not exist` (หรือคอลัมน์อื่นที่เพิ่งเพิ่ม) | โค้ดใหม่แต่ DB ยังเก่า → ดู §โค้ดใหม่ + DB เก่า ด้านล่าง |
| backend ขึ้นไม่ได้ตอน start | ดู logs; มัก env ผิด (.env) หรือ DB ยังไม่พร้อม |
| รัน test ไม่ได้ | `pip install -r requirements.txt` ก่อน แล้ว `pytest -v` |

---

## ⚠️ กับดักตอนพัฒนาบน Docker (เจอจริง เสียเวลาเยอะ)

### แก้โค้ด admin-ui แล้วหน้าเว็บไม่เปลี่ยน

`docker-compose.yml` รัน admin-ui ด้วย `npm run dev` และ mount `./admin-ui:/app` ไว้แล้วก็จริง
แต่ **Next.js ในคอนเทนเนอร์ไม่ได้รับสัญญาณว่าไฟล์เปลี่ยน** เพราะ inotify ของ Linux ไม่ข้ามมาจาก
ไฟล์ระบบฝั่ง Windows (และ macOS ก็มีอาการคล้ายกัน) → มันเสิร์ฟหน้าที่คอมไพล์ค้างไว้เดิมตลอด

**อาการหลอก:** แก้โค้ดแล้ว "ไม่มีอะไรเกิดขึ้น" หรือทดสอบแล้วไม่ผ่านทั้งชุด ทั้งที่โค้ดถูกแล้ว

```bash
docker restart signage_admin_ui     # แล้วรอ ~10-15 วิ ให้ Next คอมไพล์ใหม่
```

> ฝั่ง backend ไม่มีปัญหานี้ เพราะ uvicorn `--reload` ใช้การ poll ไฟล์แทน inotify

### โค้ดใหม่ + DB เก่า = ทุก request ที่แตะตารางนั้นพัง 500

คอนเทนเนอร์ backend โหลดโค้ดใหม่จากดิสก์เองอัตโนมัติ **แต่ migration ไม่ได้รันตาม**
พอดึงโค้ดที่มี migration ใหม่มาแล้วยังไม่ migrate จะได้ `column ... does not exist`
ทุก request ที่แตะตารางนั้น เช่นล็อกอินพังทั้งระบบ

```bash
docker exec signage_backend alembic upgrade head
```

**ลำดับที่ถูกต้องตอน deploy คือ migrate ก่อน แล้วค่อยให้โค้ดใหม่รับ traffic** — ดู
[deployment.md §ลำดับการอัปเดตเวอร์ชัน](deployment.md)

---

## ขอความช่วยเหลือเพิ่ม
- log รวม: `docker compose logs -f`
- error tracking: Sentry (ถ้าตั้ง `SENTRY_DSN`)
- ดู [disaster-recovery.md](disaster-recovery.md) ถ้าต้องกู้ระบบ
