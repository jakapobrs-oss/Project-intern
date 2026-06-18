# 🖥️ Player Configuration Guide

> วิธีตั้งค่าเครื่องเล่น (player) ทั้ง Android TV และ Web/RPi kiosk
> สำหรับ ops / ช่างติดตั้ง

---

## ภาพรวม

Player 1 ตัว = 1 จอ ทำหน้าที่:
1. **Pair** กับ server ครั้งแรก (ด้วย pairing code 6 หลัก) → ได้ `device_token`
2. **Heartbeat** ทุก 30 วิ (บอกสถานะ + รับว่า manifest outdated ไหม)
3. **Pull manifest** → ดาวน์โหลด content → cache local → เล่น loop
4. **Poll TV commands** ทุก 5 วิ → ส่งผ่าน serial/CEC
5. **Report playback** (สำหรับ play-count report §28)

> ทุกอย่างเป็น **outbound HTTPS** จาก player ไป server — ไม่ต้องเปิด inbound port ที่จอ

---

## A. Android TV Player

### ตั้งค่าครั้งแรก
1. ติดตั้ง APK (`player/android` → build ด้วย Android Studio → `app-release.apk`)
2. เปิดแอป → กรอก **Server URL** เช่น `https://signage.your-org.example`
3. แอปโชว์/กรอก **pairing code** ที่ admin สร้างจากหน้า Devices
4. pair สำเร็จ → แอปเก็บ `device_token` ใน SharedPreferences

### USB-Serial (ควบคุม TV ผ่าน RS-232)
- รองรับ chip: **FTDI / CP210x / CH340 / PL2303** (ดู `res/xml/device_filter.xml`)
- เสียบ USB-to-Serial → Android ขอ permission ครั้งแรก → อนุญาต
- backend ส่ง `raw_bytes_hex` มา → แอปแค่ส่งผ่าน serial (logic อยู่ฝั่ง server)

### Auto-start + kiosk
- ตั้งแอปเป็น **LEANBACK launcher** (Android TV home) หรือใช้ kiosk/pinning mode
- ปิด screen-saver + sleep ใน Settings ของ Android TV
- เปิด "stay awake while charging" (Developer options)

---

## B. Web Player (RPi / Mini PC kiosk)

### ตั้งค่า
1. serve `player/web/` ผ่าน nginx หรือเปิดตรงจาก URL ของ server
2. เปิด Chromium kiosk mode ชี้ไปที่หน้า player
3. กรอก server URL + pairing code (เก็บใน localStorage)

### Chromium kiosk (systemd)
```ini
# /etc/systemd/system/signage-kiosk.service
[Unit]
Description=Signage Kiosk
After=graphical.target

[Service]
User=pi
Environment=DISPLAY=:0
ExecStart=/usr/bin/chromium-browser --kiosk --noerrdialogs \
  --disable-infobars --incognito --autoplay-policy=no-user-gesture-required \
  https://signage.your-org.example/player/
Restart=always
RestartSec=5

[Install]
WantedBy=graphical.target
```

### ปิดจอดับ (RPi)
```bash
# ใน autostart / .xprofile
xset s off
xset -dpms
xset s noblank
# /boot/config.txt
hdmi_blanking=0
```

### Web Serial (ควบคุม TV จาก browser)
- ต้องใช้ **Chromium 89+** + HTTPS (Web Serial API ต้อง secure context)
- ผู้ใช้ต้องอนุญาต serial port ครั้งแรก (browser prompt)

---

## C. การตั้งค่าฝั่ง server (ต่อ device)

ตั้งใน admin UI หน้า **Device detail**:
| ค่า | ความหมาย |
|---|---|
| `location` | ตำแหน่งจอ (เช่น "ลานหน้าตึก OPD") |
| `tv_brand` / `tv_model` | ยี่ห้อ/รุ่น TV (สำหรับ RS-232 protocol) |
| `ip_address` | IP ของจอ/LED (สำหรับ LED ส่ง TCP ตรง) |
| platform | android_tv / rpi_kiosk / ... |
| group membership | ใส่ device เข้า player group → schedule ผูกกับ group |

---

## D. Boot sequence ที่ควรเห็น (debug)
```
1. splash "Connecting..."
2. NTP sync (เวลาตรง = scheduler ทำงานถูก)
3. โหลด config + device_token จาก storage
4. heartbeat → server เห็น online
5. pull manifest → ดาวน์โหลด content ที่ขาด
6. เริ่ม playlist loop
```
ถ้าค้างขั้นไหน → ดู [troubleshooting.md](troubleshooting.md) หมวด "จอ / Player"
