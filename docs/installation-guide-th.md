# 🛠️ คู่มือติดตั้งระบบ (ภาษาไทย)

> สำหรับช่างติดตั้ง / ผู้ดูแลระบบ — ติดตั้งระบบใหม่ตั้งแต่ศูนย์

---

## 1. สิ่งที่ต้องเตรียม

| รายการ | ขั้นต่ำ (1–20 จอ) | หมายเหตุ |
|---|---|---|
| Server | 2 core / 4GB RAM / 100GB SSD | Mini PC / VPS / RPi 4 |
| OS | Ubuntu 22.04 LTS | หรือ Linux ที่รัน Docker ได้ |
| Software | Docker + Docker Compose | ดูขั้นตอนติดตั้งด้านล่าง |
| Domain (ถ้าใช้ HTTPS) | เช่น signage.your-org.example | ชี้ DNS มาที่ server |
| Network | LAN switch + จอ/player | ดู PLAN §14 (VLAN topology) |

---

## 2. ติดตั้ง Docker (Ubuntu)

```bash
curl -fsSL https://get.docker.com | sudo sh
sudo usermod -aG docker $USER   # logout/login ใหม่หลังรัน
docker --version && docker compose version
```

---

## 3. ติดตั้งระบบ

```bash
# 1. ดึงโค้ด
git clone <repo-url> Project-intern
cd Project-intern

# 2. สร้าง .env จาก template แล้วแก้ค่าสำคัญ
cp .env.example .env
nano .env
```

**ค่าที่ต้องแก้ก่อน production** (ดู [SECURITY.md](../SECURITY.md)):
```
APP_ENV=production
APP_DEBUG=false
JWT_SECRET_KEY=<สุ่มยาว ≥32 ตัว>
DEVICE_TOKEN_SECRET=<สุ่มยาว ≥32 ตัว>
SEED_ADMIN_PASSWORD=<รหัสแข็งแรง>
S3_ACCESS_KEY=<ไม่ใช่ minioadmin>
S3_SECRET_KEY=<ไม่ใช่ minioadmin>
CORS_ORIGINS=https://signage.your-org.example
```

> สร้างคีย์สุ่ม: `openssl rand -hex 32`

```bash
# 3. เปิดระบบ (auto-migrate + auto-seed admin)
docker compose up -d --build

# 4. ตรวจว่าพร้อม
curl http://localhost:8000/api/v1/readiness    # → ok
docker compose ps                               # ทุก service = running/healthy
```

---

## 4. เข้าใช้งานครั้งแรก

| บริการ | URL | login |
|---|---|---|
| Admin UI | http://SERVER:3000 | admin / (รหัสที่ตั้งใน .env) |
| API docs | http://SERVER:8000/api/docs | — |
| MinIO console | http://SERVER:9001 | S3 key/secret ใน .env |

**สิ่งแรกที่ต้องทำ:** เปลี่ยนรหัส admin (ถ้ายังไม่ได้ตั้งใน .env)

### ใส่ข้อมูลตัวอย่าง (อยากเห็น flow เร็ว)
```bash
docker compose exec backend python -m app.scripts.seed_demo
# สร้าง device + content + plan + schedule + ผู้ใช้ทดสอบทุก role
```

---

## 5. เปิด HTTPS (production)

มี nginx config + systemd unit ให้แล้ว:
```bash
# ใช้ nginx TLS (config ที่ nginx/signage.conf)
sudo cp nginx/signage.conf /etc/nginx/sites-available/signage
sudo ln -s /etc/nginx/sites-available/signage /etc/nginx/sites-enabled/
sudo certbot --nginx -d signage.your-org.example   # ออก Let's Encrypt cert
sudo systemctl reload nginx
```
หรือใช้ `docker-compose.prod.yml` (multi-stage non-root images) — ดู [production-deployment.md](production-deployment.md)

---

## 6. เชื่อมต่อจอ (Player)

1. หน้า **Devices** → New → ตั้งชื่อ + ใส่เข้า group → ได้ **pairing code**
2. เปิด player (Android TV / RPi kiosk) → กรอก server URL + pairing code
3. รอ player online (ดู device list) — ดูรายละเอียดที่ [player-config.md](player-config.md)

---

## 7. เชื่อมต่อ TV / LED (ควบคุมฮาร์ดแวร์)

- **TV ผ่าน RS-232:** เสียบ USB-to-Serial ที่ player → ตั้ง `tv_brand`/`tv_model` ของ device
- **TV ผ่าน HDMI-CEC:** ต่อสาย HDMI → ใช้ได้กับ TV ที่รองรับ CEC
- **LED board:** ตั้ง `ip_address` ของ controller → ส่งข้อความจากหน้า TV Control
  (รองรับ protocol generic_tcp / huidu / xixun — เลือกตาม controller จริง)

---

## 8. ตั้ง Backup (สำคัญมาก)

```bash
sudo cp deploy/systemd/signage-backup.* /etc/systemd/system/
sudo systemctl enable --now signage-backup.timer
```
ดู [disaster-recovery.md](disaster-recovery.md) สำหรับ restore + ทดสอบ backup

---

## 9. ตรวจสอบหลังติดตั้งเสร็จ

- [ ] `/api/v1/readiness` = ok
- [ ] login admin + เปลี่ยนรหัสเริ่มต้นแล้ว
- [ ] อัปโหลด content ทดสอบ → มี thumbnail
- [ ] pair จอ 1 ตัว → online
- [ ] สร้าง schedule → จอแสดงเนื้อหา
- [ ] HTTPS ทำงาน (ถ้าตั้ง)
- [ ] backup timer ทำงาน (`systemctl list-timers`)
- [ ] ทำ hardening checklist ใน [SECURITY.md](../SECURITY.md)

> ติดปัญหา → [troubleshooting.md](troubleshooting.md)
