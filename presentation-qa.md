# ❓ Q&A เตรียมสอบ — Digital Signage (เรา=Backend, แฟน=Frontend)

> วิธีใช้ตอนสอบ: ถ้าถูกถามแล้วนึกตัวเลข/ไฟล์ไม่ออก → ค้นไฟล์นี้ (`presentation-qa.md`) หรือให้ Sonnet หาในโค้ดให้
> 🏷️ `(BE)` เราตอบ · `(FE)` แฟนตอบ · `(ทั้งคู่)` ช่วยกัน
> ⚠️ หลักการ: **ตอบตรง อย่าเดา ข้อจำกัดบอกตามจริง** (กรรมการเคารพคนที่รู้ขอบเขตงานตัวเอง)

---

## 🟢 ระดับง่าย (ตอบทันที)

**Q: ระบบนี้ทำอะไร?** (FE)
> ระบบจัดการจอประชาสัมพันธ์จากศูนย์กลาง — อัปโหลดสื่อ → จัดผัง/ตารางเวลา → ส่งขึ้นจอหลายเครื่องพร้อมกัน + คุมทีวีเปิด/ปิด/เปลี่ยนช่องผ่าน RS-232/CEC

**Q: ทำไมต้องมีระบบนี้ (ปัญหาเดิม)?** (FE)
> เดิมจัดการจอแยกทีละเครื่อง/ทำมือ ไม่มีศูนย์กลาง สั่งพร้อมกันไม่ได้ ไม่รู้ว่าจอไหนออนไลน์ — ระบบนี้รวมศูนย์ + เห็นสถานะ real-time

**Q: ใช้เทคโนโลยีอะไรบ้าง?** (BE server / FE client)
> Backend: FastAPI (Python async) + PostgreSQL + Redis + Arq worker + MinIO (เก็บไฟล์) + Docker
> Frontend: Next.js + Tailwind · Player: Android (Kotlin) + Web PWA

**Q: รองรับกี่จอ?** (BE)
> ออกแบบ POC 10–20 จอ แต่ pattern (pre-computed manifest + polling) scale ได้ถึงหลักร้อย-พัน

**Q: แบ่งงานกันยังไง?** (ทั้งคู่)
> เรา = backend/DB/TV control/Android · แฟน = Admin UI/Web player · เจอกันที่ API contract

---

## 🟡 ระดับกลาง (ต้องมีเหตุผลรองรับ)

**Q: ทำไมเลือก FastAPI ไม่ใช่ Django/Flask?** (BE)
> async native (จอหลายเครื่อง poll พร้อมกัน I/O เยอะ), type-safe ด้วย Pydantic, auto Swagger doc — เหมาะ API-first

**Q: "manifest pattern" คืออะไร ทำไมไม่ query realtime?** (BE) ⭐ ถามบ่อย
> backend คำนวณ **JSON ตารางเล่นต่อเครื่องไว้ล่วงหน้า** player แค่ดึงไปเล่น
> ข้อดี: (1) player ทำงานง่าย/เบา (2) **ทำงานต่อได้ตอนเน็ตหลุด** (cache ไว้) (3) ลดโหลด DB (ไม่ต้อง query ทุก request) — ยืมแนวจากระบบเดิม (Script Agent)

**Q: hierarchy 5 ชั้นคืออะไร?** (BE)
> Content → Presentation (จัด layout/zone) → Plan (playlist) → PlayerGroup → Player — ยืดหยุ่นกว่า playlist ตรงๆ เช่นแก้ presentation ครั้งเดียว มีผลทุกจอในกลุ่ม

**Q: player รู้ได้ไงว่ามีของใหม่?** (BE)
> heartbeat ทุก 30 วิ backend ตอบ `manifest_outdated` (เทียบ version = SHA-256 ของ payload) ถ้าเก่า → player ดึง manifest ใหม่

**Q: สั่งเปิด-ปิดทีวีทำงานยังไง?** (BE) ⭐
> backend **สร้าง raw byte ตาม protocol แต่ละยี่ห้อ** (Samsung MDC/LG/Sony/Panasonic/NEC/CEC) → เข้า Redis queue → player ดึงไปยิงออก serial (RS-232) → player แค่ส่งผ่าน ไม่ต้องรู้ protocol

**Q: จัดการสิทธิ์ผู้ใช้ยังไง?** (BE)
> JWT + RBAC 7 role (super_admin/admin/editor/approver/viewer/operator/device) เช่น editor สร้าง schedule ได้แต่ต้องรอ approver อนุมัติ

**Q: ทำไมแยก Android กับ Web player?** (FE/BE)
> Android TV = native เสถียร เล่นวิดีโอลื่น (ExoPlayer) + ต่อ USB-serial ได้ · Web PWA = ลงเร็วบน RPi/จอที่มี browser ไม่ต้อง build

**Q: ทำไม Next.js?** (FE)
> React-based, routing/SSR พร้อม, ecosystem ใหญ่, dev เร็ว, มี dark mode + i18n th/en

**Q: ทดสอบยังไง?** (BE)
> **142 unit test ผ่าน** + **smoke E2E 10 ขั้นผ่านบน Postgres จริง** (auth→pair→approve→schedule→manifest→TV command→audit) + ทดสอบ upload→MinIO→worker สร้าง thumbnail จริง

---

## 🔴 ระดับยาก (เชิงลึก / edge case)

**Q: ถ้า 2 คนกด approve/แก้ schedule พร้อมกัน (race condition)?** (BE)
> ใช้ DB transaction + ตรวจ conflict ตอนสร้าง schedule (กลุ่ม+เวลาทับ+priority เท่ากัน → 409, มี `?force=true` ถ้าตั้งใจ)

**Q: scheduler เลือกอันไหนเล่นตอนเวลาทับกัน?** (BE)
> priority stack — emergency override สูงสุด, แล้ว eval RRULE + daily time-window + timezone (`schedule_eval.py`) ถ้า rule พังให้ fail-open

**Q: เน็ตหลุดกลางคัน player ทำไง?** (BE)
> เล่นจาก cache เดิมต่อ (LRU eviction) + exponential backoff ตอน reconnect + heartbeat กลับมาเช็ค version ใหม่

**Q: security ทำอะไรบ้าง?** (BE) ⭐
> bcrypt + account lockout, JWT แยก user/device, magic-bytes validate ไฟล์อัปโหลด (กันปลอมนามสกุล), **SSRF guard** (กัน url ภายใน/metadata), rate limit, CSRF (cookie mode), ClamAV hook, Sentry **scrub PII** (mask email/phone)

**Q: ทำไม Redis ไม่ใช่ตัวอื่น / license?** (BE)
> ใช้สำหรับ queue (Arq) + command queue + rate limit · ถ้า production แนะนำ **Valkey** (fork BSD-3 ของ Linux Foundation) เพราะ Redis เปลี่ยนเป็น SSPL/RSAL ปี 2024 ไม่ open-source จริง — drop-in แทนกันได้

**Q: scale ไป 500+ จอทำยังไง?** (BE)
> manifest pre-computed อยู่แล้ว (อ่านอย่างเดียว) → cache/CDN ได้, แยก worker เพิ่ม, DB read-replica, MinIO/R2 เสิร์ฟไฟล์แยกจาก API

**Q: ถ้าไฟล์วิดีโอใหญ่/format แปลก?** (BE)
> จำกัด image 20MB / video 500MB, worker ใช้ ffprobe เช็ค → transcode ถ้าจำเป็น, dedupe ด้วย SHA-256 (ไฟล์ซ้ำไม่เก็บซ้ำ)

**Q: data flow เต็มๆ จากกดในเว็บถึงขึ้นจอ?** (ทั้งคู่) ⭐⭐ ถามชัวร์
> FE กด push → BE สร้าง manifest + version → player heartbeat เจอ outdated → ดึง manifest → render ตาม zone → (ถ้าสั่งทีวี) byte RS-232 ผ่าน queue → serial → จอ

---

## ⚫ Worst case (คำถามหิน — เตรียมใจ)

**Q: ทดสอบกับ TV/hardware จริงมั้ย?** ⭐ ต้องตอบตามจริง
> ตอบตรง: "โค้ด + protocol byte ทดสอบครบทุกยี่ห้อด้วย **emulator** (จำลอง decode byte กลับมา ตรงทุกคำสั่ง) และทดสอบ serial loopback จริง · ส่วนจอจริงทดสอบได้บางรุ่น (LG) · การทดสอบกับจอครบทุกยี่ห้อเป็น **future work** เพราะข้อจำกัดด้านอุปกรณ์" — **อย่าโม้ว่าเทสครบ** กรรมการมักจับโป๊ะตรงนี้

**Q: ใช้ AI/เครื่องมือช่วยเขียนโค้ดมั้ย?** ⭐ ตอบอย่างมั่นใจ
> ตอบตรงไปตรงมา: "ใช้เครื่องมือช่วย implement บางส่วน แต่ **สถาปัตยกรรม การตัดสินใจเลือก pattern การทดสอบ และการ debug เราทำเองและเข้าใจทุกส่วน**" แล้วพิสูจน์ด้วยการตอบคำถามเชิงลึกได้ (นั่นคือเหตุผลที่ต้องอ่านไฟล์นี้ + รู้จริง) — ความเข้าใจสำคัญกว่าใครพิมพ์

**Q: ความใหม่/สิ่งที่ทำเองคืออะไร (ไม่ใช่แค่ลอก)?** (BE)
> modernize ระบบเดิม (C#/.NET/Windows-only) → **stack ใหม่ Python/FastAPI/Docker ข้าม OS**, รวม TV control หลายยี่ห้อเป็น API เดียว, manifest pattern + 5-tier hierarchy, ออกแบบ security ครบ (PDPA/SSRF/RBAC)

**Q: ทำไมไม่ใช้ของสำเร็จรูป (Xibo/Yodeck)?** (ทั้งคู่)
> (1) เรียนรู้ทำเอง = วัตถุประสงค์ฝึกงาน (2) customize ให้เข้ากับระบบ รพ. ได้ (3) ไม่มีค่า license/ผูก vendor (4) คุม data on-premise (PDPA ผู้ป่วย)

**Q: ระบบล่ม/DB ตาย ทำไง?** (BE)
> player เล่น cache ต่อได้ (ไม่ดับจอ), rate limit fail-open (ไม่ block ตอน Redis ตาย), worker retry + backoff, มี backup script (pg_dump) + DR doc

**Q: ถ้ามี requirement เพิ่มกลางทาง รับมือยังไง?** (ทั้งคู่)
> โครงสร้างแยกชั้นชัด (model/service/endpoint) + มี test กันพัง + migration (Alembic) แก้ schema ได้ปลอดภัย — เพิ่ม feature ไม่กระทบของเดิม

**Q: จุดอ่อนของระบบคืออะไร? (กรรมการชอบถามให้ยอมรับ)** (ทั้งคู่)
> ตอบตรง: ยังไม่ได้ทดสอบ hardware ครบทุกยี่ห้อ · ยังไม่ load-test จริงระดับพันจอ · LED protocol ยัง generic ต้องปรับตามบอร์ดจริง — **รู้ข้อจำกัด = จุดแข็ง ไม่ใช่จุดอ่อน**

---

## 📌 Cheat sheet (ตัวเลขที่ต้องจำ)

| รายการ | ค่า |
|---|---|
| Unit tests | 142 ผ่าน |
| Smoke E2E | 10/10 บน Postgres จริง |
| Models / Migrations | 8 ตารางหลัก / 5 migration |
| RBAC roles | 7 |
| TV ยี่ห้อ | Samsung MDC, LG, Sony, Panasonic, NEC, CEC (+Toshiba→CEC) |
| Heartbeat / command poll | 30 วิ / 5 วิ |
| Pairing code | 6 หลัก, หมดอายุ 15 นาที |
| Limit ไฟล์ | รูป 20MB / วิดีโอ 500MB |
| Manifest version | SHA-256 ตัด 16 ตัว |
| Architecture | 3-tier: CMS(FastAPI) → worker(Arq) → player |
