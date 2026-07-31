# 🚀 Production Deployment Guide

คู่มือ deploy ระบบบน production server (Ubuntu 22.04+ หรือ Debian 12+)

> สำหรับ dev → ดู [RUNBOOK.md](../RUNBOOK.md)
> ที่นี่เน้น: production hardening, TLS, systemd, monitoring, backup, secret management

---

## 🏗️ Architecture สำหรับ production

```
                   ┌─────────────────┐
   Internet ──TLS──┤ Cloudflare/ALB  │── (optional WAF layer)
                   └────────┬────────┘
                            │
                   ┌────────▼────────┐
                   │  nginx (Docker) │  ← TLS termination + reverse proxy
                   │  port 80,443    │
                   └────────┬────────┘
                            │
        ┌───────────────────┼───────────────────┐
        │                   │                   │
   ┌────▼────┐         ┌────▼────┐         ┌────▼────┐
   │ backend │         │ admin-ui│         │  worker │
   │ FastAPI │         │ Next.js │         │   Arq   │
   └────┬────┘         └─────────┘         └────┬────┘
        │                                       │
        └───────────┬───────────┬──────────────┘
                    │           │
              ┌─────▼─────┐ ┌──▼────┐
              │ postgres  │ │ redis │
              │  + minio  │ │       │
              └───────────┘ └───────┘
              (private docker network — ไม่ expose ports)
```

---

## 📋 Pre-deployment checklist

ก่อน deploy ทุกครั้ง:

- [ ] โดเมน + DNS A record → server IP
- [ ] firewall เปิด port 80, 443 (และ 22 สำหรับ SSH)
- [ ] Docker Compose v2+ + Docker engine 24+
- [ ] HTTPS cert (Let's Encrypt หรือ commercial)
- [ ] `.env` มี secrets ทั้งหมด **ไม่ใช้ค่า default**
- [ ] `TRUSTED_PROXIES` ตั้งเป็นวง IP ของ nginx (เช่น `172.16.0.0/12` สำหรับ docker network) — ไม่ตั้ง = audit log จะบันทึก IP ของ nginx แทน IP ผู้ใช้จริง
- [ ] Off-site backup destination (B2, S3, restic repo) เตรียมไว้
- [ ] Monitoring endpoint (Prometheus / healthchecks.io) เตรียม
- [ ] Sentry DSN (optional แต่แนะนำ)

---

## 🔐 Step 1 — Generate production secrets

```bash
# JWT secrets
echo "JWT_SECRET_KEY=$(openssl rand -hex 32)"          >> /opt/signage/.env
echo "DEVICE_TOKEN_SECRET=$(openssl rand -hex 32)"     >> /opt/signage/.env

# DB password (ต้อง match กับ POSTGRES_PASSWORD)
PG_PASS=$(openssl rand -base64 24 | tr -d /=+)
echo "POSTGRES_PASSWORD=$PG_PASS"                       >> /opt/signage/.env
echo "DATABASE_URL=postgresql+asyncpg://signage:$PG_PASS@postgres:5432/signage" >> /opt/signage/.env

# MinIO credentials
echo "S3_ACCESS_KEY=$(openssl rand -hex 16)"            >> /opt/signage/.env
echo "S3_SECRET_KEY=$(openssl rand -hex 32)"            >> /opt/signage/.env

# Seed admin password (ใช้ครั้งแรกเท่านั้น — เปลี่ยนทันทีหลัง login)
echo "SEED_ADMIN_PASSWORD=$(openssl rand -base64 16)"   >> /opt/signage/.env

# App environment
echo "APP_ENV=production"                               >> /opt/signage/.env
echo "APP_DEBUG=false"                                  >> /opt/signage/.env
echo "LOG_LEVEL=WARNING"                                >> /opt/signage/.env

# CORS — เปลี่ยน domain ตามจริง
echo "CORS_ORIGINS=https://signage.example.com"         >> /opt/signage/.env

# จำกัด permission .env (เฉพาะ owner อ่านได้)
chmod 600 /opt/signage/.env
```

⚠ **เก็บ secrets ที่ generate ลงใน password manager** (1Password / Bitwarden / Vault)
ไม่อย่างนั้น recover ลำบาก

---

## 🌐 Step 2 — TLS certificate

### Option A: Let's Encrypt (free, recommended)
```bash
# Install certbot
sudo apt-get install certbot

# Generate cert (standalone — หยุด nginx ก่อน ครั้งแรก)
sudo certbot certonly --standalone -d signage.example.com \
    --agree-tos --email admin@example.com

# cert จะอยู่ที่ /etc/letsencrypt/live/signage.example.com/
# auto-renew (อยู่ใน cron แล้ว) — ตรวจ:
sudo systemctl status certbot.timer
```

แก้ `nginx/signage.conf`:
```nginx
ssl_certificate     /etc/letsencrypt/live/signage.example.com/fullchain.pem;
ssl_certificate_key /etc/letsencrypt/live/signage.example.com/privkey.pem;
```

แก้ docker-compose.prod.yml mount:
```yaml
nginx:
  volumes:
    - /etc/letsencrypt:/etc/letsencrypt:ro
```

### Option B: self-signed (internal LAN)
```bash
cd /opt/signage/nginx
mkdir -p letsencrypt
openssl req -x509 -newkey rsa:2048 -nodes -days 365 \
    -keyout letsencrypt/privkey.pem \
    -out letsencrypt/fullchain.pem \
    -subj "/CN=signage.local"
```

---

## 🐳 Step 3 — Deploy stack

```bash
# Clone repo + checkout production tag
sudo mkdir -p /opt/signage && sudo chown signage:signage /opt/signage
cd /opt/signage
git clone https://github.com/yourorg/signage.git .
git checkout v1.0.0

# Build + start (multi-stage prod images)
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d --build

# ตรวจ services
docker compose ps
docker compose logs -f --tail 50
```

ครั้งแรก:
- migration จะรันอัตโนมัติ (backend command มี `alembic upgrade head`)
- seed admin จะสร้าง user `admin` (อ่าน password จาก `SEED_ADMIN_PASSWORD`)

---

## ⚙️ Step 4 — systemd auto-start

```bash
sudo cp deploy/systemd/signage.service /etc/systemd/system/
sudo cp deploy/systemd/signage-backup.{service,timer} /etc/systemd/system/
sudo systemctl daemon-reload

# Stack auto-restart on host reboot
sudo systemctl enable --now signage.service

# Daily backup ทุก 02:00
sudo systemctl enable --now signage-backup.timer
sudo systemctl list-timers | grep signage
```

ดู logs:
```bash
journalctl -u signage -f
journalctl -u signage-backup -n 50
```

---

## 📊 Step 5 — Monitoring

### Prometheus + Grafana (recommended)
```yaml
# /etc/prometheus/prometheus.yml
scrape_configs:
  - job_name: signage
    metrics_path: /api/v1/metrics
    static_configs:
      - targets: ['signage_backend:8000']
```

Metrics ที่ scrape ได้:
- `signage_devices_total{status="..."}`
- `signage_emergency_active`
- `signage_contents_total{approval_status="..."}`
- `signage_schedules_active`

### Sentry (error tracking)
แก้ `.env`:
```
SENTRY_DSN=https://<key>@<org>.ingest.sentry.io/<project>
SENTRY_TRACES_SAMPLE_RATE=0.05      # 5% performance traces
SENTRY_ENVIRONMENT=production
```
`docker compose restart backend worker`

### Uptime monitoring (external)
```bash
# Add ใน backup.sh ตอน success
curl -fsS --retry 3 https://hc-ping.com/<uuid>
```

---

## 🔄 Step 6 — Backup verification

ทดสอบ restore ทุก 3 เดือน:
```bash
# Create test DB
docker compose exec postgres createdb -U signage signage_test_restore

# Restore latest backup
LATEST=$(ls -t /var/backups/signage/signage-*.sql.gz | head -1)
gunzip -c "$LATEST" | docker compose exec -T postgres psql -U signage signage_test_restore

# Verify (count rows)
docker compose exec postgres psql -U signage signage_test_restore -c "SELECT count(*) FROM users;"

# Cleanup
docker compose exec postgres dropdb -U signage signage_test_restore
```

---

## 🍪 Enable httpOnly cookie auth (Phase 7 hardening)

Default มาคือ **bearer mode** (JWT in localStorage) — เปลี่ยนเป็น cookie mode สำหรับ production:

### ทำไมต้องเปลี่ยน?
- **XSS-immune**: JS อ่าน httpOnly cookie ไม่ได้ → token รั่วจาก XSS ไม่ได้
- ต้องคู่กับ CSRF protection (double-submit cookie pattern)
- ต้องการ **same-origin** หรือ **strict CORS** + HTTPS

### Step-by-step

```bash
# 1. แก้ .env ของ backend
sed -i "s/^CSRF_ENABLED=.*/CSRF_ENABLED=true/" /opt/signage/.env
sed -i "s/^NEXT_PUBLIC_AUTH_MODE=.*/NEXT_PUBLIC_AUTH_MODE=cookie/" /opt/signage/.env

# 2. ตรวจ APP_ENV=production (ทำให้ Secure flag ของ cookie เปิด)
grep APP_ENV /opt/signage/.env       # → APP_ENV=production

# 3. rebuild admin-ui (Next.js bake env เข้า client bundle)
docker compose -f docker-compose.yml -f docker-compose.prod.yml \
    up -d --build admin-ui

# 4. restart backend (เปิด CsrfMiddleware)
docker compose restart backend

# 5. test
# - login จาก admin UI → cookies signage_access_token + csrf_token ต้องถูก set
# - ตรวจ devtools: cookies มี HttpOnly + Secure + SameSite=Lax
# - mutation request ต้องมี X-CSRF-Token header
```

### Verify
```bash
# Login + ดู Set-Cookie
curl -i -X POST https://signage.example.com/api/v1/auth/login \
    -d "username=admin&password=$ADMIN_PASS"
# ต้องมี: Set-Cookie: signage_access_token=...; HttpOnly; Secure; SameSite=Lax

# /me ผ่าน cookie (no header)
curl -i https://signage.example.com/api/v1/auth/me \
    -H "Cookie: signage_access_token=<jwt>"
# → 200 + user JSON
```

### Rollback
ถ้า cookie mode มีปัญหา (cross-domain, CORS):
```bash
sed -i "s/^CSRF_ENABLED=.*/CSRF_ENABLED=false/" /opt/signage/.env
sed -i "s/^NEXT_PUBLIC_AUTH_MODE=.*/NEXT_PUBLIC_AUTH_MODE=bearer/" /opt/signage/.env
docker compose -f docker-compose.yml -f docker-compose.prod.yml \
    up -d --build admin-ui
docker compose restart backend
# user ต้อง re-login (token เก่าใน localStorage ใช้ได้แต่ cookie ไม่อยู่แล้ว)
```

---

## 🔁 Secret rotation

### JWT secret rotation (logs out everyone — plan for off-hours)
```bash
# 1. Generate ใหม่
NEW=$(openssl rand -hex 32)

# 2. แก้ .env
sed -i "s|^JWT_SECRET_KEY=.*|JWT_SECRET_KEY=$NEW|" /opt/signage/.env

# 3. Restart backend
docker compose restart backend

# 4. ทุก session ถูก invalidate — user ต้อง login ใหม่
```

### Device token rotation (player ต้อง re-pair)
```bash
# Single device:
# admin UI → /devices/<id> → "รีเซ็ต pairing" → ออก code ใหม่
# Player ต้องใส่ code ใหม่อีกครั้ง

# Mass rotation (ทุก device):
docker compose exec backend python -c "
from app.db import SessionLocal
from app.models.device import Device
import asyncio
async def go():
    async with SessionLocal() as db:
        from sqlalchemy import update
        await db.execute(update(Device).values(device_token_hash=None, paired_at=None, status='unpaired'))
        await db.commit()
asyncio.run(go())
"
# จากนั้น regenerate pairing code ผ่าน UI ทีละ device
```

### Database password rotation
```bash
# 1. New password
NEW=$(openssl rand -base64 24 | tr -d /=+)

# 2. Update Postgres
docker compose exec postgres psql -U signage -c "ALTER USER signage WITH PASSWORD '$NEW';"

# 3. แก้ .env (POSTGRES_PASSWORD + DATABASE_URL)
sed -i "s|^POSTGRES_PASSWORD=.*|POSTGRES_PASSWORD=$NEW|" /opt/signage/.env
sed -i "s|asyncpg://signage:[^@]*@|asyncpg://signage:$NEW@|" /opt/signage/.env

# 4. Restart backend + worker
docker compose restart backend worker
```

---

## 🆘 Troubleshooting

### `nginx: SSL certificate not found`
```bash
# ตรวจ mount path
docker compose -f docker-compose.yml -f docker-compose.prod.yml exec nginx ls -la /etc/letsencrypt/
# ถ้าว่าง → แก้ docker-compose.prod.yml volumes
```

### `backend: alembic upgrade head failed`
```bash
docker compose logs backend | tail -50
# มักเป็น DB connection — ตรวจ DATABASE_URL ใน .env

# Manual:
docker compose exec backend alembic upgrade head
docker compose exec backend alembic current
```

### audit log บันทึก IP เป็น 172.x ไม่ใช่ IP ผู้ใช้

ไล่ตามลำดับนี้:

1. **รันแบบ dev (ไม่มี nginx) เห็น 172.x = ปกติ ไม่ใช่บั๊ก** — Docker เปลี่ยน IP ต้นทาง
   ตอน forward พอร์ตให้ ไม่มีทางรู้ IP จริงได้จากฝั่งแอป
2. **รันจริงหลัง nginx แล้วยังเป็น 172.x** → ยังไม่ได้ตั้ง `TRUSTED_PROXIES`
   ระบบจึงไม่เชื่อ `X-Forwarded-For` แล้วใช้ IP ของ nginx แทน:
   ```bash
   # หา IP/subnet ของ nginx ใน docker network
   docker compose exec backend getent hosts nginx
   # ตั้งใน .env แล้ว restart backend
   TRUSTED_PROXIES=172.16.0.0/12
   ```
3. ตรวจว่า nginx ส่ง header จริง — `nginx/signage.conf` ต้องมี
   `proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;` (มีให้แล้ว)

> ทำไมไม่เชื่อ header ไปเลย: `X-Forwarded-For` เป็นค่าที่ผู้ใช้แนบมาเองได้
> ถ้าเชื่อทุกกรณี ใครก็ทำให้ audit บันทึก IP ผิดคนได้ — log ที่เก็บไว้สืบสวนจะใช้ไม่ได้

### `admin-ui: Application error`
```bash
# Next.js standalone ต้องการ NODE_ENV=production
docker compose -f docker-compose.yml -f docker-compose.prod.yml exec admin-ui printenv NODE_ENV
# ถ้าไม่ใช่ production → rebuild image
```

### Rate limit ทำงานผิด (block admin)
```bash
# เพิ่ม limit ชั่วคราว
echo "RATE_LIMIT_MAX_REQUESTS=100" >> .env
docker compose restart backend
```

### `429 Too Many Requests` ตอน load test
ใช้ Redis-backed rate limit แทน (Phase 8 — ยังไม่ implement) หรือปิด rate limit สำหรับ IP ของ admin (whitelist ใน nginx)

---

## 📚 References

- [RUNBOOK.md](../RUNBOOK.md) — dev setup
- [docs/er-diagram.md](er-diagram.md) — DB schema
- [docs/architecture.md](architecture.md) — system architecture
- [docs/api.md](api.md) — API reference
