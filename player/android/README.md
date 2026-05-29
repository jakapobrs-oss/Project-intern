# Signage Player — Android

Kotlin app สำหรับ Android TV / Android tablet — รัน kiosk mode + รับ raw TV command bytes จาก backend ส่งผ่าน USB-to-Serial

## USB-Serial bridge (§36)
- **ใช้:** USB chip enum (FTDI/CP210x/CH340/PL2303), library `usb-serial-for-android`, baud rate ต่อ brand
- **หลักการ:** backend คำนวณ raw bytes มาให้แล้ว (key field `raw_bytes_hex`) → player แค่ open serial + write

## โครงสร้าง
```
android/
├── settings.gradle.kts
├── build.gradle.kts                    ← root (AGP 8.7.2 + Kotlin 2.0.21)
└── app/
    ├── build.gradle.kts                ← dependencies: usb-serial-for-android, okhttp, kotlinx.serialization
    └── src/main/
        ├── AndroidManifest.xml         ← LEANBACK_LAUNCHER + USB host + foreground service
        ├── res/xml/device_filter.xml   ← vendor IDs ของ 4 chip
        └── java/com/signage/player/
            ├── MainActivity.kt          ← pairing UI + WebView player placeholder
            ├── PlayerService.kt         ← foreground: heartbeat loop (30s) + command poll loop (5s)
            ├── api/ApiClient.kt         ← OkHttp + DTOs (pair/heartbeat/manifest/commands/ack)
            └── tv/TvSerialBridge.kt     ← USB-Serial write (FTDI/CP210x/CH340/PL2303)
```

## Build (ต้องมี Android Studio Iguana+ / Gradle 8.10+)
```bash
cd android
./gradlew assembleDebug
# APK อยู่ที่: app/build/outputs/apk/debug/app-debug.apk

# ติดตั้งเข้า Android TV ผ่าน ADB
adb connect <android-tv-ip>:5555
adb install app/build/outputs/apk/debug/app-debug.apk
```

## Flow ตอน boot ครั้งแรก
1. เปิดแอป → ถ้ายังไม่มี `device_token` ใน SharedPreferences → แสดงหน้า pairing
2. admin สร้าง device ใน admin-ui → ได้ 6-digit pairing code
3. กรอก server URL + pairing code → `POST /api/v1/player/pair` → ได้ device_token
4. เก็บ token ใน SharedPreferences → เปิด WebView + start `PlayerService`
5. `PlayerService`:
   - heartbeat ทุก 30s → ถ้า `manifest_outdated=true` → refresh manifest
   - poll `GET /api/v1/player/commands` ทุก 5s → ถ้ามี → `tv.sendBytes(raw_bytes_hex, brand)` → ack

## TODO (Phase ถัดไป)
- [ ] Manifest renderer จริง (ตอนนี้แค่ WebView placeholder) — parse zones + layout → render
- [ ] Cache offline (Room DB + media file download)
- [ ] LRU eviction (§25)
- [ ] Exponential backoff ตอน network fail
- [ ] Crash recovery + auto-restart
- [ ] HDMI-CEC support (cec opcode mapping)
- [ ] Boot sequence ตาม §25 (boot splash → fetch manifest → start playback)

## ⚠️ ข้อจำกัดของ Phase 4 scaffold นี้
- ยังไม่ได้ build/test APK จริง — รอ user มี Android Studio + Android TV จริงตอนทดสอบ
- ยังไม่มี layout XML — Phase ถัดไปทำ
- baud rate ต่อ brand hard-code ใน `TvSerialBridge.kt` — Phase ถัดไปให้ backend ส่งใน command response
