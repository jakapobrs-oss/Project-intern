# Signage Player — Web PWA

PWA สำหรับรันบน Raspberry Pi / mini PC + Chromium kiosk

## Run บน RPi (Ubuntu/Raspbian)
```bash
# 1. serve static files (nginx / python http.server / backend nginx)
python3 -m http.server 8080 --directory /path/to/player/web

# 2. start Chromium kiosk
chromium-browser --kiosk \
    --noerrdialogs --disable-infobars \
    --autoplay-policy=no-user-gesture-required \
    --enable-features=WebSerial \
    http://localhost:8080/index.html
```

หรือ deploy ผ่าน backend nginx → mount `player/web/` เป็น static dir

## Auto-start ตอน boot (systemd unit)
```ini
[Unit]
Description=Signage Player Kiosk
After=graphical.target

[Service]
ExecStart=/usr/bin/chromium-browser --kiosk --enable-features=WebSerial http://localhost:8080
Restart=always
User=pi

[Install]
WantedBy=graphical.target
```

## Web Serial API requirement
- Chromium/Chrome 89+ บน Linux
- ครั้งแรกที่ลอง send TV command → browser จะถามให้ user pick port (กดปุ่ม OK ครั้งเดียวก็พอ)
- แนะนำ run ในโหมด `--user-data-dir` พร้อม permission auto-grant (ดู Chromium policy)

## ไฟล์
| ไฟล์ | หน้าที่ |
|---|---|
| `index.html` | UI shell (pair + multi-zone stage + emergency overlay + crash screen) |
| `styles.css` | layout/theme (แยกออกจาก HTML — cache ได้) |
| `app.js` | logic ทั้งหมด (modular IIFE) — pair / heartbeat / manifest / renderer / carousel / backoff / Web Serial |
| `sw.js` | service worker — cache shell + media + LRU eviction |
| `manifest.json` | PWA manifest |

## ฟีเจอร์ (Phase 4 polish — Option F)
- ✅ **Zone-based renderer** — รองรับ layout templates (fullscreen / split_70_30 / main_ticker) พร้อม per-zone media (image/video/iframe/text ticker)
- ✅ **Plan carousel** — เล่นไล่ items ตาม `duration_sec` วนรอบ
- ✅ **Emergency overlay** — render fullscreen ทับเมื่อ `manifest.emergencies` มีข้อมูล (text/url/image, animated pulse)
- ✅ **Exponential backoff** — heartbeat/command loop ทบเวลาเมื่อ fail (jittered, cap 5 นาที)
- ✅ **Media LRU cache** — Cache Storage API + size cap 500 MB + FIFO eviction
- ✅ **Crash recovery** — uncaught error / unhandled rejection → crash screen + auto-reload 10s

## วิธีเปลี่ยน config
แก้ค่าใน [app.js](app.js) ส่วน Config:
```js
const HEARTBEAT_BASE_MS = 30_000;
const COMMAND_BASE_MS = 5_000;
const BACKOFF_MAX_MS = 5 * 60_000;
const MEDIA_CACHE_MAX_BYTES = 500 * 1024 * 1024;
const CRASH_RELOAD_SEC = 10;
```
เมื่อแก้ shell file → **ต้อง bump `SHELL_CACHE` version ใน `sw.js`** ไม่งั้น client เก่าได้ของเก่าจาก cache

## TODO (Phase 7 / รอ user environment)
- [ ] HDMI-CEC ผ่าน native helper (subprocess `cec-client`) — ต้องใช้ Electron wrapper หรือ native bridge
- [ ] Custom presentation layout (เลือก zone coords)
- [ ] Telemetry: ส่ง browser uptime / FPS / memory ใน heartbeat
