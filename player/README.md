# Player

แอป player ที่รันบนจอประชาสัมพันธ์ — แยกเป็น 2 platform:

## `android/` — Android TV / Android player (Kotlin)
- USB-to-Serial bridge ส่ง raw TV command bytes จาก backend ผ่าน USB chip (§36)
- รองรับ TV brand: Samsung MDC / LG / Sony BRAVIA / Panasonic / Toshiba
- USB chip: FTDI / CP210x / CH340 / PL2303

## `web/` — PWA สำหรับ kiosk mode (เว็บใน Chromium full-screen)
- ใช้กับ Raspberry Pi / mini PC + Chrome `--kiosk`
- รับ manifest จาก backend → render ตาม schedule

## Pull manifest pattern (§35.2)
Player ไม่ query DB realtime — ดึง pre-computed JSON manifest ต่อ player จาก backend แทน:
```
GET /api/v1/player/{device_id}/manifest
→ { "items": [...], "schedule": [...], "version": "...", "checksum": "..." }
```

Phase 3 จะ implement ทั้ง 2 platform
