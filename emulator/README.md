# 🧪 Emulator — สาธิต "สิ่งที่ทำ" โดยไม่ต้องมี hardware

ชุด emulator นี้จำลอง **เครื่องเล่นสื่อ (player)** และ **จอโทรทัศน์ (TV)** แบบ software ล้วน
เพื่อสาธิต/ทดสอบ "สิ่งที่ทำ" ของบรีฟ โดยไม่ต้องมี Android box / TV / สาย Serial จริง

| สิ่งที่ทำ (บรีฟ) | emulator ครอบให้ |
|---|---|
| 1. player เชื่อมต่อผ่าน LAN ทั้งหมด | `emulated_player.py` pair + heartbeat + pull manifest ผ่าน HTTP |
| 2a. เครื่องเล่นแสดงผลข้อมูล | ดึง manifest มาแสดงรายการที่จะขึ้นจอ (+ web player ของจริงใน Demo E) |
| 2b. ควบคุม TV ผ่าน HDMI + Serial | `tv_emulator.py` decode raw bytes จาก backend → แสดงสถานะ TV / CEC stub |

> ⚠️ **ขอบเขต:** emulator พิสูจน์ว่า **โปรโตคอลและซอฟต์แวร์ถูกต้อง** (byte ที่ backend สร้าง = byte ที่จะยิงเข้า Serial Port จริง) — **ไม่ได้** พิสูจน์ว่า TV รุ่นจริงรับคำสั่งได้ ตอนเขียนเล่ม/รายงานให้ระบุชัดว่า "ทดสอบกับ virtual device (emulator)"

---

## ไฟล์

| ไฟล์ | หน้าที่ |
|---|---|
| `tv_emulator.py` | **Virtual TV** — decode byte (mirror `backend/app/services/tv_control/base.py`: Samsung MDC / LG / Sony / Panasonic / NEC / CEC) → แสดงสถานะ power/input/volume/mute |
| `emulated_player.py` | **จำลอง player** — login→สร้าง device→pair→ส่งคำสั่งผ่าน backend→ดึง command→ decode (in-process) หรือเขียนเข้า virtual COM (serial) + ดึง manifest |
| `cec_helper_stub.py` | จำลอง **HDMI-CEC helper** (API ชุดเดียวกับ `tv-control/cec_helper.py`) ที่ 127.0.0.1:7600 |

**ต้องมี:** stack รันอยู่ (`docker compose up -d`) + `pyserial` (ลงใน venv แล้ว: `backend\.venv\Scripts\python.exe -m pip install pyserial`)

ทุกคำสั่งรันด้วย venv python จากโฟลเดอร์ `emulator/`:
```powershell
$py = "..\backend\.venv\Scripts\python.exe"
cd emulator
```

---

## Demo A — in-process (ง่ายสุด, ไม่ต้องลงอะไรเพิ่ม) ✅ ทดสอบแล้ว

```powershell
& $py emulated_player.py --brand samsung
```
จะเห็น: ต่อ LAN → pair → ดึง manifest → ส่งคำสั่ง power_on/input/volume/mute/power_off
แต่ละคำสั่งโชว์ **raw byte จริงจาก backend** (เช่น `aa1100010113` = Samsung MDC power-on) → decode ขึ้น Virtual TV

## Demo B — หลายยี่ห้อ
```powershell
& $py emulated_player.py --brand lg          # LG RS-232C ASCII "ka 01 01"
& $py emulated_player.py --brand sony        # Sony SimpleIP "*SCPOWR...."
& $py emulated_player.py --brand panasonic   # Panasonic STX/ETX
& $py emulated_player.py --brand cec         # HDMI-CEC keyword
```

## Demo C — HDMI-CEC ผ่าน helper stub
```powershell
# หน้าต่าง 1
& $py cec_helper_stub.py
# หน้าต่าง 2 — ยิงเหมือน player/web (sendViaCecHelper) หรือ curl
curl.exe -X POST 127.0.0.1:7600/cec/named -H "Content-Type: application/json" -d "{\"name\":\"power_on\"}"
curl.exe -X POST 127.0.0.1:7600/cec/named -H "Content-Type: application/json" -d "{\"name\":\"mute\"}"
```

---

## Demo D — Virtual Serial ผ่าน com0com (เต็มสูบ — byte วิ่งผ่าน COM port จริง)

โหมดนี้ byte ที่ backend สร้างจะถูก **เขียนเข้า virtual COM port จริง** แล้ว Virtual TV อ่านจากปลายอีกด้าน
(เหมือน player ต่อสาย RS-232 เข้า TV) — ต่างจาก in-process ตรงที่ผ่านชั้น OS serial จริง

### 1) ติดตั้ง com0com (ทำครั้งเดียว, ต้องสิทธิ์ Administrator)
1. ดาวน์โหลดตัว **signed**: <https://sourceforge.net/projects/com0com/files/com0com/3.0.0.0/> → `com0com-3.0.0.0-i386-and-x64-signed.zip`
2. แตก zip แล้วรัน `Setup_com0com_*.exe` **คลิกขวา → Run as administrator** (ยอมรับการติดตั้ง driver)
3. เปิด **"com0com - setup command prompt"** (as admin) แล้วสร้างคู่พอร์ตชื่อ COM10/COM11:
   ```
   setupc install PortName=COM10 PortName=COM11
   ```
4. ตรวจว่ามีพอร์ตแล้ว (PowerShell ปกติ):
   ```powershell
   [System.IO.Ports.SerialPort]::GetPortNames()   # ควรเห็น COM10, COM11
   ```

### 2) รันเดโม (2 หน้าต่าง)
```powershell
# หน้าต่าง 1 — Virtual TV ฟังปลายสาย COM11
& $py tv_emulator.py --port COM11 --brand samsung

# หน้าต่าง 2 — player เขียน raw byte เข้า COM10
& $py emulated_player.py --brand samsung --serial-out COM10
```
หน้าต่าง 1 จะอัปเดตจอ TV ตามคำสั่งที่วิ่งผ่าน virtual serial จริง

> ✅ ชั้น serial (write→read→decode) ทดสอบผ่าน pyserial `loop://` แล้ว — com0com แค่เปลี่ยน loopback เป็นพอร์ตข้าม process
> หมายเหตุ: ปลายทาง backend ใช้ baud 9600 (ปรับใน `tv_emulator.py`/`emulated_player.py` ได้ถ้า TV จริงใช้ค่าอื่น)

---

## Demo E — Web player ของจริง (เห็นเนื้อหาขึ้นจอ, optional)

`player/web` เป็น PWA player จริง รันบนเบราว์เซอร์ได้เลย (ครอบ สิ่งที่ทำ 2a เต็มรูปแบบ — zone renderer + carousel)
ต้องเพิ่ม CORS origin ของ player แล้ว restart backend:
1. ใน `.env` เพิ่ม origin ของ player ใน `CORS_ORIGINS` (เช่น `,http://localhost:8080`) → `docker compose up -d backend`
2. เสิร์ฟ player: `& $py -m http.server 8080 --directory ..\player\web`
3. เปิด `http://localhost:8080` → กรอก server `http://localhost:8000` + pairing code (สร้าง device ใน Admin UI เพื่อเอา code) → จอจะ render เนื้อหาตาม schedule

(บอกได้ถ้าอยากให้ผม wire + ถ่าย screenshot ส่วนนี้ให้อัตโนมัติเหมือนที่ทำกับ Admin UI)

---

## ยี่ห้อ TV ที่ decode ได้ (ตรงกับ `tv_control/base.py`)
Samsung (MDC RS-232/RJ45) · LG (RS-232C ASCII) · Sony (SimpleIP) · Panasonic (STX/ETX) · NEC (power) · HDMI-CEC · Toshiba (→CEC)
