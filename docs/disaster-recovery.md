# 🛟 Disaster Recovery Runbook

> เอกสารสำหรับ **ops** — ทำตามได้โดยไม่ต้องถาม dev
> ครอบคลุม: backup, restore, RPO/RTO, การกู้ระบบเมื่อ server เจ๊ง

---

## 1. สรุปกลยุทธ์ (ต้องรู้ก่อน)

| สิ่งที่ต้อง backup | เครื่องมือ | ความถี่ | เก็บไว้ |
|---|---|---|---|
| **PostgreSQL** (data หลัก) | `pg_dump` → `scripts/backup.sh` | ทุกวัน 02:00 | 7 วัน / 4 สัปดาห์ / 6 เดือน |
| **MinIO** (รูป/วิดีโอ) | `mc mirror` / restic | ทุกวัน | off-site (Backblaze B2) |
| **Secrets** (`.env`) | คัดลอกเข้า password manager | ทุกครั้งที่เปลี่ยน | offline |

- **RPO** (ยอมเสียข้อมูลได้สูงสุด): **24 ชม.** (backup รายวัน)
- **RTO** (เวลากู้คืนที่ตั้งเป้า): **< 2 ชม.** บน hardware สำรอง

> ⚠️ Player แต่ละตัว cache content ไว้ local อยู่แล้ว — server ล่มชั่วคราว **จอยังเล่นต่อได้** จาก cache
> สิ่งที่หายคือความสามารถ "เปลี่ยน/สั่งงาน" ไม่ใช่ "จอดับทันที"

---

## 2. Backup (อัตโนมัติ)

ติดตั้งผ่าน systemd timer (มีใน `deploy/systemd/`):

```bash
sudo cp deploy/systemd/signage-backup.* /etc/systemd/system/
sudo systemctl enable --now signage-backup.timer
systemctl list-timers signage-backup.timer   # ดูรอบถัดไป
```

ตรวจว่า backup ล่าสุดสำเร็จ:
```bash
ls -lh /var/backups/signage/           # ต้องมีไฟล์ของวันนี้
restic -r "$RESTIC_REPOSITORY" snapshots | tail   # ถ้าใช้ off-site
```

**ทดสอบ backup เดือนละครั้ง** (สำคัญ — backup ที่ restore ไม่ได้ = ไม่มี backup):
```bash
bash scripts/backup.sh           # รันมือ ดู exit code = 0
```

---

## 3. Restore (กู้คืน)

### 3.1 กู้ PostgreSQL

```bash
# 1. หยุด backend + worker (กัน write ระหว่าง restore)
docker compose stop backend worker

# 2. drop + recreate DB (ระวัง! ลบ data ปัจจุบัน — ยืนยันก่อน)
docker compose exec postgres psql -U signage -c "DROP DATABASE IF EXISTS signage;"
docker compose exec postgres psql -U signage -c "CREATE DATABASE signage;"

# 3. restore จาก dump (เลือกไฟล์วันที่ต้องการ)
gunzip -c /var/backups/signage/db-YYYYMMDD.sql.gz | \
  docker compose exec -T postgres psql -U signage signage

# 4. start กลับ
docker compose start backend worker
curl http://localhost:8000/api/v1/readiness    # ต้อง ok
```

### 3.2 กู้ MinIO (media)

```bash
# restore bucket จาก off-site
mc mirror b2/signage-backup/media local/signage-media
# หรือจาก restic
restic -r "$RESTIC_REPOSITORY" restore latest --target /tmp/restore
```

### 3.3 กู้ทั้งระบบบน hardware ใหม่

```bash
1. ติดตั้ง Docker + Docker Compose (ดู docs/installation-guide-th.md)
2. git clone <repo> && cd Project-intern
3. คัดลอก .env จาก password manager มาวาง
4. docker compose up -d postgres redis minio   # infra ก่อน
5. restore DB (3.1) + MinIO (3.2)
6. docker compose up -d                          # ที่เหลือ
7. ตรวจ /api/v1/readiness + login admin + ดู device list
8. Player จะ reconnect เองภายใน 1 รอบ heartbeat (~30 วิ)
```

---

## 4. Checklist หลัง restore

- [ ] `/api/v1/readiness` ตอบ `ok`
- [ ] login admin ได้
- [ ] device list แสดงครบ + กลับมา online ภายใน 1-2 นาที
- [ ] เปิด content ที่มีรูป → preview/URL โหลดได้ (MinIO ok)
- [ ] สร้าง schedule ทดสอบ → manifest อัปเดต
- [ ] ส่ง emergency broadcast ทดสอบ → ยกเลิก
- [ ] **rotate secrets** ถ้าสงสัยว่า server เก่าถูก compromise (ดู docs/production-deployment.md)

---

## 5. Failover (ขั้นสูง — optional)

ระบบ POC เป็น single-node ถ้าต้อง HA:
- PostgreSQL streaming replication (primary + standby) → promote standby เมื่อ primary ตาย
- MinIO distributed mode (4+ node)
- backend หลาย instance หลัง nginx/Caddy load balancer + `RATE_LIMIT_BACKEND=redis`

ดู PLAN §27 (Reliability) + §16 (Server spec ตามจำนวนจอ)
