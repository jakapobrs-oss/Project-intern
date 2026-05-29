# Scripts

| ไฟล์ | ใช้ทำอะไร | OS |
|---|---|---|
| `verify.ps1` | Static + integration verify (ตรวจไฟล์ + syntax + docker stack + smoke) | Windows |
| `verify.sh` | เหมือนกัน เวอร์ชัน bash | Linux/macOS |
| `smoke_e2e.py` | E2E flow test — ต้อง stack run อยู่ + seed admin แล้ว | ทั้งคู่ |

## Workflow แนะนำ

### ครั้งแรก
```powershell
# 1. ตรวจ structure ก่อน (ไม่ต้องมี docker)
.\scripts\verify.ps1

# 2. ถ้า structure OK + มี docker → ขั้น 4 จะรัน stack อัตโนมัติ
# ถ้าไม่มี docker จะข้ามแล้วยังถือว่า pass

# 3. ถ้า verify pass + stack ขึ้น + seed แล้ว → e2e test
docker compose exec backend python -m app.scripts.seed   # ถ้ายังไม่ seed
python scripts/smoke_e2e.py
```

### หลังจาก commit ใหม่
```bash
bash scripts/verify.sh && python scripts/smoke_e2e.py
```

## ออก exit code
- `0` = ผ่านหมด
- `1` = มี failure (รายละเอียดใน output)

## ขอบเขต `verify.*`
✅ ตรวจไฟล์สำคัญครบ
✅ Python syntax (parse AST)
✅ Docker stack up + healthcheck
✅ Migration apply
✅ Seed admin
✅ pytest tests/
✅ Login + /auth/me smoke

❌ ยังไม่ทำ:
- TypeScript/Kotlin syntax check (ต้องใช้ tsc/gradle)
- Build admin-ui production
- Build Android APK
- Integration test ที่ใช้ TV จริง

## smoke_e2e.py ทดสอบอะไร
1. `/healthz` → 200
2. Login → access_token
3. `/auth/me` ตรง username
4. POST `/devices` → ได้ pairing_code 6 ตัว
5. POST `/player/pair` → ได้ device_token
6. POST `/player/heartbeat` → server time + manifest version
7. GET `/player/manifest` → device_id ตรง
8. POST `/tv/devices/{id}/commands` (power_on) → 202
9. GET `/player/commands` → ได้ command ที่มี raw_bytes_hex + brand=samsung
10. POST `/player/commands/{id}/ack` → 204
11. GET `/tv/commands/{cmd_id}/status` → success
12. DELETE device cleanup
