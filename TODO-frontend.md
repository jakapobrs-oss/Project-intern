# ✅ TODO — Frontend (แฟน)

> เจ้าของ: **แฟน** · ขอบเขต: Admin UI (Next.js) + Web player (PWA) + เล่มรายงาน (ประกอบ) + เดโม
> สถานะโค้ด: เสร็จแล้ว (Admin UI browser E2E + web player render ผ่านเมื่อ 2026-06-16) — งานที่เหลือคือ "ยืนยัน + เล่ม + เดโม"

---

## A. ยืนยัน UI ยังทำงาน
- [ ] รัน `admin-ui`: `npm install` แล้ว `npm run dev` → เปิดทุกหน้า เช็คโหลดได้ + คุย backend ได้
  - ⚠️ gotcha: `NEXT_PUBLIC_API_URL` ต้องชี้ backend ที่ถูก (เคยมีบั๊ก bake เป็น IP ผิด → UI โหลดได้แต่ดึงข้อมูลไม่ได้)
- [ ] เช็ค web player (`player/web/`): pair + render หน้าเว็บเต็มจอ (เคยผ่าน puppeteer)
- [ ] เช็ค dark mode toggle + i18n th/en ใน topbar

## B. เล่มรายงาน (งานหลักของฝั่งแฟน — ดู project-book-prep/FORMAT-README.md)
- [ ] **หน้าปกจริง** — เติมชื่อ-รหัสนักศึกษา / อาจารย์ที่ปรึกษา / สถาบัน / ปี (แก้ที่ object `COVER` ใน `web-demos/build-report-pdf.mjs` + `front-matter.md`)
- [ ] **ch4 screenshot** — แคปทุกหน้า Admin UI (login/dashboard/devices/contents/schedules/tv/emergency/audit/users) + web player
- [ ] **ch3** — Gantt chart (timeline งาน) + ผังหน้าจอ / user flow (UI)
- [ ] **สารบัญรูปภาพ + สารบัญตาราง** (ยังขาด)
- [ ] build PDF: `cd web-demos; node build-report-pdf.mjs` → ตรวจ format (Angsana 16/18pt, เลขหน้า ก ข ค → 1,2,3) ที่ `project-book-prep/preview/`

## C. เดโม (สำคัญตอนสอบ — แฟนเป็นคนขับจอ)
- [ ] เตรียมข้อมูลเดโม: `backend\.venv\Scripts\python.exe -m app.scripts.seed_demo` (มี seed_demo อยู่แล้ว)
- [ ] ซ้อมเดินเดโม flow: login → อนุมัติ content → สร้าง schedule → push → ดู player render + สั่งเปิดทีวี
- [ ] **อัดวิดีโอ demo สำรอง** เผื่อ hardware/เน็ตมีปัญหาตอนสอบ (กันพลาด)

## D. UI polish + เล่มส่วน FE
- [ ] เก็บสี dark-mode ที่ตกหล่นในบางหน้า (hard-coded `text-slate-500` ฯลฯ)
- [ ] ch2: tech stack ฝั่ง client (Next.js / Tailwind / PWA / Web Serial)
- [ ] ch1 + ch5: เขียนร่วมกับเรา (ภาพรวม + สรุป)

---
**ต้องคุยกับ backend (contract ที่สองคนต้องตรงกัน):** manifest schema · `/player/*` API · auth mode (`NEXT_PUBLIC_AUTH_MODE` bearer/cookie) · CORS — เช็คผ่าน Swagger `http://localhost:8000/api/docs`
