# 📐 รูปแบบเล่ม + วิธีสร้าง PDF (เก็บไว้ใช้ซ้ำ)

เล่มรายงานสหกิจ/ปริญญานิพนธ์ภาษาไทย — format ลอกจากเล่มตัวอย่างเดชธนา (ม.รังสิต)
เนื้อหาปัจจุบัน: ระบบ Digital Signage (Project-intern)

## วิธีสร้าง/อัปเดต PDF
```bash
cd /e/Claude-WorkSpace/web-demos
node build-report-pdf.mjs
# ได้ -> project-book-prep/preview/digital-signage-report-preview.pdf
```
ต้องมี: Node + puppeteer-core + Chrome (ใน web-demos), Python + PyMuPDF, อินเทอร์เน็ต (โหลดโลโก้ ไม่มีก็ขึ้น placeholder)

## ไฟล์ในชุดนี้
| ไฟล์ | หน้าที่ |
|---|---|
| `web-demos/build-report-pdf.mjs` | ตัวสร้างหลัก (md → HTML → Chrome PDF → stamp เลขหน้า) |
| `web-demos/toc_pages.py` | หาเลขหน้าหัวข้อ (marker) เพื่อทำสารบัญ |
| `web-demos/stamp_pages.py` | ประทับเลขหน้า (เว้นปก/ใบรับรอง → ก ข ค → 1 2 3) |
| `front-matter.md` | ปก/ใบรับรอง/บทคัดย่อ ไทย-อังกฤษ/กิตติกรรม (แก้ข้อมูลหน้าปกที่ object `COVER` ใน build script) |
| `ch1-intro.md` .. `ch5-conclusion.md` | เนื้อหา 5 บท (ch2 ใส่รูปด้วย `[[FIG\|num\|slug\|name]]`) |
| `report-skeleton-5ch.md` | โครงเล่ม + ตารางข้อเท็จจริง refresh |
| `internship-book-materials.md` / `tools-list.md` / `data-dictionary.md` / `assets/er-diagram.*` | วัตถุดิบเนื้อหา |
| `render_example.py` + `example-pages/` | render เล่มตัวอย่าง + ดึงขนาดฟอนต์ (ไว้เทียบ format) |

## สเปกรูปแบบ (วัดจากเล่มจริง)
- A4 · ขอบ ซ้าย 3.81cm / อื่น 2.54cm · ฟอนต์ **Angsana New**
- body 16pt · ชื่อบท 18pt หนา กึ่งกลาง (ขึ้นหน้าใหม่ทุกบท) · หัวข้อย่อย 16pt หนา ชิดซ้าย
- ย่อหน้าแรกเยื้อง 1.27cm · justify · line-height 1.5
- เลขหน้ามุมขวาบน: ปก/ใบรับรอง = เว้น · บทคัดย่อ→สารบัญ = ก ข ค ง จ · เนื้อหา = 1,2,3
- รูป: กึ่งกลาง + "รูปที่ X.Y ชื่อ" ใต้รูป · สารบัญ: จุดไข่ปลา + เลขหน้าจริง (2-pass marker)

## ยังต้องเติม
ข้อมูลหน้าปกจริง (ชื่อ-รหัส/อาจารย์/สถาบัน/ปี) · screenshot บท 4 · Gantt บท 3 · สารบัญตาราง/รูปภาพ
