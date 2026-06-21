# 🔥 ซ้อมยิงคำถามโหด — Mock Defense Grilling

> **เก็บไว้ซ้อมทีหลัง** (เรา=Backend) · โหดกว่า `presentation-qa.md` — เน้น follow-up ไล่ต่อ + กับดัก

## วิธีใช้ตอนจะซ้อมจริง
- ให้แฟน/เพื่อน หรือ **Sonnet สวมบทกรรมการดุที่สุด** ยิงทีละข้อ ไม่เปิดเฉลยก่อน:
  > "สวมบทกรรมการสอบสหกิจที่โหดสุด ยิงคำถามจาก `presentation-grill.md` ทีละข้อ ถ้าตอบอ่อน/เลี่ยง ให้ไล่ต่อจนมุม"
- ตอบออกเสียงจริง จับเวลา → ตอบเสร็จค่อยเทียบ "ทิศคำตอบ"
- ผ่านเกณฑ์ = **ไม่สะดุด + ไม่โม้ + มี follow-up รองรับ**

## กติกาเอาตัวรอด 3 ข้อ
1. **ไม่รู้ = "ส่วนนั้นยังไม่ได้วัด/ยังไม่ได้ทำ"** ดีกว่าเดา (เดาผิด = โดนไล่ยับ)
2. โดนถามส่วนแฟน = อธิบายภาพรวมได้ + โยน detail ("ส่วนนี้แฟนดูแล ภาพรวมคือ…")
3. โดนต้อนให้ขัดแย้งตัวเอง = ยอมรับ nuance **อย่าดันทุรัง**

---

## รอบ 1 — เจาะ "รู้จริงมั้ย"

**G1.** "ผมแก้ content ตอนนี้ อีกกี่วินาทีจอเปลี่ยน? ทำไมต้องรอ?"
- ทิศ: heartbeat 30 วิ → worst ~30 วิ + โหลด · รอเพราะ pull-based (player ถาม ไม่ใช่ server push)
- 🪤 ไล่ต่อ: "30 วิ ช้าไป emergency ล่ะ?" → emergency มี priority override + ลด interval ได้
- ❌ ห้ามพูด "เปลี่ยนทันที" (ขัด architecture ตัวเอง)

**G2.** "version ใช้ SHA-256 ตัด 16 ตัว — ชนกัน (collision) ได้มั้ย?"
- ทิศ: โอกาสต่ำมาก (64-bit), ใช้เช็คแค่ "เปลี่ยนรึยัง" ไม่ใช่ security; ชน = ไม่อัปเดต เสี่ยงต่ำ รับได้
- 🪤 "ถ้าซีเรียส?" → เก็บ updated_at/counter ควบ

**G3.** "ไล่ code path ตั้งแต่ heartbeat จนได้ manifest ผ่านฟังก์ชันอะไรบ้าง"
- ทิศ: `/player/heartbeat` → verify device_token → update telemetry → เทียบ version → outdated → `/player/manifest` → `manifest_service` build (device→schedule→plan→presentation→zone→content→presigned URL)
- 🪤 "ทำไม selectinload?" → กัน N+1 query

## รอบ 2 — ท้าทุกการตัดสินใจ

**G4.** "ทำไมไม่ใช้ WebSocket/MQTT push? polling เปลืองเปล่า"
- ทิศ: trade-off — polling ง่าย/firewall-friendly/player ทน, 10-20 จอ overhead ต่ำ; MQTT เพิ่ม broker+ซับซ้อน; ระบบ RAMA เดิมก็ poll
- 🪤 "พันจอล่ะ?" → ค่อยใส่ MQTT (roadmap), manifest pre-computed รองรับ push ได้ไม่ต้องรื้อ

**G5.** "ทำไม Postgres ไม่ใช่ MySQL ที่ รพ.อาจมีอยู่แล้ว?"
- ทิศ: JSON support, asyncpg ดี, constraint แข็ง; ถ้าต้อง MySQL ก็ port ได้ (SQLAlchemy abstraction)

**G6.** "byte RS-232 gen ฝั่ง server ทำไม ไม่ให้ player gen? ส่งผ่านเน็ตเปลือง"
- ทิศ: player บาง/ทน, แก้ protocol ที่เดียวมีผลทุกจอ, byte สั้นมากไม่เปลือง; ของเดิม player gen → แก้ทีต้องอัป player ทุกตัว

## รอบ 3 — กับดักขัดแย้ง

**G7.** "บอก offline-friendly แต่ก็เห็นสถานะ real-time — ขัดกันนะ ออฟไลน์แล้ว real-time ได้ไง?"
- ทิศ: คนละเรื่อง — *การเล่น* offline ได้ (cache), *การรายงานสถานะ* ต้องออนไลน์; หาย heartbeat >90 วิ = mark OFFLINE → ก็ยัง "เห็นสถานะจริง" คือเห็นว่ามันออฟ
- ❌ อย่าดันว่าได้ทั้งคู่พร้อมกัน

**G8.** "test 142 ผ่านหมด แปลว่าไม่มีบั๊กเลยสิ?"
- ทิศ: test ครอบ logic หลัก ไม่ใช่ proof ว่าไม่มีบั๊ก; *ตอนรัน test เจอ latent bug 4 จุด* (UUID type, naive/aware datetime) — เพราะรันถึงเจอ = นั่นคือคุณค่าของ test
- 🪤 เล่าบั๊กที่เจอ+แก้ได้ = โชว์เข้าใจจริง (บวกแต้ม)

## รอบ 4 — failure chain (ไล่ยาวไม่หยุด)

**G9.** "Redis ตายตอนนี้ เกิดอะไร?" → "worker ที่ค้างใน queue?" → "rate limit?" → "TV command ที่ยังไม่ส่งหายมั้ย?"
- ทิศ: rate limit **fail-open** (ไม่ block login), manifest ยังเสิร์ฟ (อยู่ Postgres), command in-flight หายแต่ออกแบบ idempotent + retry/re-enqueue
- ❌ ห้ามตอบ "Redis ไม่ตายหรอก"

**G10.** "ผมถอดสาย LAN จอตอนเล่นวิดีโอ แล้วเสียบกลับใน 5 นาที — เล่าทีละ step"
- ทิศ: เล่นต่อจาก cache → heartbeat fail → backoff → เสียบกลับ → heartbeat สำเร็จ → เช็ค version → ถ้าเปลี่ยนระหว่างนั้นดึง manifest ใหม่ → resume

## รอบ 5 — ownership (จับว่าทำเองมั้ย)

**G11.** (ถามเรา) "ส่วน UI แฟนทำ — token เก็บที่ไหน state จัดการไง?"
- ทิศ: ตอบภาพรวมได้ (bearer/httpOnly cookie 2 mode, `NEXT_PUBLIC_AUTH_MODE`) + โยน detail ลึกให้แฟน
- ❌ อย่าทำเป็นไม่รู้เลย (= ทีมไม่คุยกัน)

**G12.** "โค้ดส่วนไหนที่ *คุณเขียนเอง* ภูมิใจสุด อธิบายบรรทัดต่อบรรทัด"
- ⭐ เตรียม **1 ส่วนเล่าได้ลึกจริงทุกบรรทัด** (แนะนำ `tv_control/base.py` การประกอบ byte Samsung MDC checksum หรือ `manifest_service`)

## รอบ 6 — production & contribution

**G13.** "นี่แค่ POC เอา production ไม่ได้จริงหรอก?"
- ทิศ: ยอมรับต้อง harden เพิ่ม (load test, hardware ครบ) แต่ชี้ว่ามี security/migration/backup/CI/docker-prod พร้อม — ไม่ใช่แค่ demo

**G14.** "Xibo/Yodeck ฟรีและดีกว่า reinvent the wheel ทำไม?"
- ทิศ: วัตถุประสงค์ฝึกงาน=เรียนรู้, customize เข้าระบบ รพ., คุม data on-prem (PDPA ผู้ป่วย), ไม่ผูก vendor — ไม่ใช่แข่ง feature

**G15. (worst)** "ตอบตรงๆ ใช้ AI เขียนทั้งหมดใช่มั้ย เขียนเองได้กี่ %?"
- ทิศ: **นิ่ง มั่นใจ** — ใช้ช่วย implement แต่ออกแบบ/เลือก pattern/debug/test เข้าใจเองทุกส่วน → "ถามเชิงลึกส่วนไหนก็ได้ครับ" (แล้วต้องตอบได้จริง = เหตุผลที่ซ้อม)
- ❌ อย่าโกหกว่าไม่ใช้, อย่าตื่น

---

## 🎯 5 ข้อ "ตอบไม่ได้ = จบ" (ต้องเป๊ะก่อนเข้าห้องสอบ)
1. **data flow กดเว็บ → ขึ้นจอ** (ทุกคำถามโยงมานี่)
2. **manifest pattern** ทำไม + ช้ากี่วิ
3. **ทดสอบ hardware แค่ไหน** (ตอบตามจริง: emulator + LG, ครบทุกยี่ห้อ = future work)
4. **1 ส่วนที่เขียนเอง** อธิบายลึกได้
5. **ระบบล่มแล้วไง** (fail-open / cache / retry)

> 💡 ระดับโหดสุด: ตอบ G1 เสร็จ ให้คนยิงถาม "แล้วถ้า…" ต่อ 3 ชั้น ทุกข้อ — ซ้อมจน follow-up ชั้น 3 ยังไม่สะดุด
