# 🔒 Security Policy

## รายงานช่องโหว่ (Vulnerability Reporting)

หากพบช่องโหว่ด้านความปลอดภัย **อย่าเปิด public issue** — ส่งรายละเอียดมาที่:
- Email: **security@your-org.example** (เปลี่ยนเป็นของจริงตอน deploy)
- ระบุ: ขั้นตอน reproduce, ผลกระทบ, เวอร์ชัน/commit

เราจะตอบรับภายใน **3 วันทำการ** และแจ้ง timeline การแก้ไข
ขอความร่วมมือ **responsible disclosure** — ให้เวลาแก้ก่อนเปิดเผยสาธารณะ

---

## มาตรการความปลอดภัยที่มีในระบบ

| ด้าน | สิ่งที่ทำ | อ้างอิง |
|---|---|---|
| Authentication | JWT (access 30นาที + refresh rotation), bcrypt cost≥12 | §26 |
| Authorization | RBAC 7 roles + `require_role` dependency ทุก endpoint | §21 |
| Account protection | lockout หลังผิด 5 ครั้ง/15 นาที | §26 |
| Device auth | device-token แยกจาก user JWT (scope แค่ `/player/*`) | §26 |
| File upload | magic-bytes validate, ไม่เชื่อ extension, random filename, ClamAV (env-gated) | §22 |
| SSRF | block private/loopback/metadata IP สำหรับ URL ที่ user ส่ง | §26 |
| Transport | HTTPS (nginx/Caddy + Let's Encrypt), HSTS | §26 |
| Headers | CSP, X-Frame-Options, X-Content-Type-Options, Referrer-Policy | §26 |
| Rate limit | per-route (login 10/นาที), memory/redis backend | §26 |
| CSRF | double-submit cookie (เปิดเมื่อใช้ httpOnly cookie mode) | §26 |
| Secrets | `.env` ไม่ commit (gitignore), inject ผ่าน env ตอน prod | §26 |
| Audit | append-only audit log ทุก write action สำคัญ | §31 |
| Error tracking | Sentry + PII scrubbing (before_send) | — |

---

## Hardening checklist ก่อนขึ้น production

- [ ] เปลี่ยน `JWT_SECRET_KEY` + `DEVICE_TOKEN_SECRET` เป็นค่าสุ่มยาว (≥ 32 bytes)
- [ ] เปลี่ยนรหัส admin เริ่มต้น (`admin/ChangeMe123!`) ทันทีหลัง seed
- [ ] เปลี่ยน MinIO credentials (`minioadmin/minioadmin`)
- [ ] ตั้ง `APP_ENV=production`, `APP_DEBUG=false`
- [ ] ตั้ง `NEXTAUTH_URL` / CORS origins เป็น domain จริง (ไม่ใช่ localhost)
- [ ] เปิด HTTPS + HSTS (nginx config มีให้ใน `nginx/`)
- [ ] เปิด `CLAMAV_ENABLED=true` + รัน clamd container
- [ ] `RATE_LIMIT_BACKEND=redis` ถ้ารัน backend หลาย instance
- [ ] ปิด port DB/Redis/MinIO ไม่ให้ออกเน็ต (internal เท่านั้น)
- [ ] ตั้ง backup + ทดสอบ restore (ดู [disaster-recovery.md](docs/disaster-recovery.md))
- [ ] rotate JWT secret ทุก 90 วัน (grace period 24 ชม.)
- [ ] รัน `pip-audit` / `npm audit` ก่อน release

ดูเพิ่ม: [docs/production-deployment.md](docs/production-deployment.md)

---

## สิ่งที่ห้ามทำเด็ดขาด (ตาม CLAUDE.md security rules)
- ❌ hardcode password / API key / secret ใน code
- ❌ log ข้อมูล sensitive (password, token)
- ❌ trust user input โดยไม่ validate (ใช้ Pydantic ทุก endpoint)
