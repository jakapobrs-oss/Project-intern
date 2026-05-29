# TV Control

> **สถานะ Phase 4 + 7:** Protocol command builders + queue (backend, Phase 4) + **HDMI-CEC helper** (Phase 7) ✅
> Hardware execution (RS-232 / HDMI-CEC) อยู่ฝั่ง **player** เพราะ player คือเครื่องที่ต่อ TV

## Architecture

```
admin (UI)                          backend (FastAPI)                  redis             player (Android/RPi)         TV
   │                                       │                              │                       │                  │
   │ POST /api/v1/tv/devices/{id}/commands │                              │                       │                  │
   │ ─────────────────────────────────────▶│ build_command() → raw bytes  │                       │                  │
   │                                       │ enqueue (cmd_id)             │                       │                  │
   │                                       │ ───────────────────────────▶ │                       │                  │
   │ ◀──────────── 202 + cmd_id ────────── │                              │                       │                  │
   │                                       │                              │ ◀──── GET /api/v1/player/commands ─────  │
   │                                       │                              │ ─── pending cmds (raw_bytes_hex) ──────▶ │
   │                                       │                              │                       │   pyserial.write │
   │                                       │                              │                       │ ───────────────▶ │
   │                                       │                              │ ◀── POST /commands/{id}/ack {success}─── │
```

## โปรโตคอลที่รองรับ (`backend/app/services/tv_control/base.py`)

| Brand | Protocol | Command type ที่รองรับ |
|---|---|---|
| Samsung (MDC) | RS-232 / RJ45 0xAA header | power, volume (0-100), mute, HDMI1-3, set_id chain |
| LG | RS-232C ASCII `kk <id> <data>\r` | power, volume, mute, HDMI1-3 |
| Sony BRAVIA | SimpleIP TCP `*SC<CMD><16-digit>` | power, volume, mute, HDMI1-3 |
| Panasonic | RS-232 STX+payload+ETX | power, volume, mute, HDMI1-3 |
| NEC | External Control Codes | power on/off (เพิ่มเติม Phase ถัดไป) |
| Toshiba | (fallback → CEC) | ทุก CEC command |
| **HDMI-CEC** | keyword สำหรับ libcec ฝั่ง player | power, volume, mute |

## โครงสร้าง (Phase ถัดไปสำหรับ player-side)

```
player/
├── android/    ← Kotlin — USB-Serial bridge ส่ง raw_bytes_hex (§36)
│                └── รับ raw_bytes_hex → ส่งผ่าน FTDI/CP210x/CH340/PL2303
└── web/        ← PWA + native helper สำหรับ libcec บน RPi
```

## Reference docs (free, public)
- Samsung MDC Protocol PDF (Google: "Samsung MDC Protocol")
- LG RS-232C Commands PDF
- Sony BRAVIA Professional Display SDK
- Panasonic Display Control Protocol
- NEC monitor External Control Codes manual
- `libcec` (Pulse-Eight) — open source, ~95% consumer TV หลัง 2010

## Test
```bash
docker compose exec backend pytest tests/test_tv_control.py -v
```

---

## 🆕 Phase 7 — HDMI-CEC native helper

ไฟล์ใหม่:
| ไฟล์ | หน้าที่ |
|---|---|
| [`cec_helper.py`](cec_helper.py) | Python wrapper ของ `cec-client` (Pulse-Eight libcec) |
| [`cec-helper.service`](cec-helper.service) | systemd unit สำหรับ auto-start |

### ติดตั้งบน Raspberry Pi
```bash
# 1. apt install
sudo apt-get install cec-utils python3
sudo usermod -aG video pi && newgrp video

# 2. ตรวจว่า CEC bus ใช้ได้
echo scan | cec-client -s -d 1
# ควรเห็น "device #0: TV ... vendor: Samsung/LG/..."

# 3. รันแบบ standalone
python3 tv-control/cec_helper.py power on
python3 tv-control/cec_helper.py volume up
python3 tv-control/cec_helper.py scan

# 4. รันเป็น service ให้ Web PWA เรียก
sudo cp tv-control/cec-helper.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now cec-helper
curl http://127.0.0.1:7600/health   # → {"status":"ok","cec_available":true}
```

### Web PWA integration
[`player/web/app.js`](../player/web/app.js) มี `sendViaCecHelper()` ที่:
- ตรวจ `127.0.0.1:7600/health` ตอน boot
- ถ้า available + `cmd.brand == "cec"` → ส่งคำสั่ง CEC ผ่าน HTTP
- ถ้าไม่ available หรือ brand เป็น samsung/lg/... → fallback Web Serial (RS-232)

### CLI usage
```bash
python3 cec_helper.py power on              # เปิดทีวี
python3 cec_helper.py power off             # ปิด (standby)
python3 cec_helper.py volume up             # เพิ่มเสียง
python3 cec_helper.py mute                  # ปิดเสียง
python3 cec_helper.py raw "10:36"           # raw hex (10=TV, 36=standby)
python3 cec_helper.py scan                  # หา CEC devices
python3 cec_helper.py serve --port 7600     # HTTP service mode
```

### HTTP API
| Method | Path | Body | คืน |
|---|---|---|---|
| GET | `/health` | — | `{"status":"ok","cec_available":bool}` |
| GET | `/scan` | — | `{"ok":bool,"output":string}` |
| POST | `/cec/power` | `{"on":true/false}` | `{"ok":bool,"output":string}` |
| POST | `/cec/volume` | `{"direction":"up"/"down"}` | `{"ok":bool,"output":string}` |
| POST | `/cec/mute` | — | `{"ok":bool,"output":string}` |
| POST | `/cec/named` | `{"name":"power_on"\|...}` | `{"ok":bool,"output":string}` |
| POST | `/cec/raw` | `{"hex":"10:36"}` | `{"ok":bool,"output":string}` |

⚠ Bind **127.0.0.1 เท่านั้น** (ไม่มี auth) — ห้าม expose ออก network
