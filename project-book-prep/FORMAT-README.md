# 📐 รูปแบบเล่ม + วิธีสร้าง PDF (เก็บไว้ใช้ซ้ำ)

เล่มรายงานสหกิจ/ปริญญานิพนธ์ภาษาไทย — format ลอกจากเล่มตัวอย่างเดชธนา (ม.รังสิต)
เนื้อหาปัจจุบัน: ระบบ Digital Signage (Project-intern)

## วิธีสร้าง/อัปเดต (เล่มแยกรายคน — ส่งแยกกันคนละเล่ม)
เลือกคนด้วย env `PERSON`: `1` = จักรภพ (Backend, ค่าเริ่มต้น) · `2` = พรชนก (Frontend)
```bash
cd /e/Claude-WorkSpace/web-demos
PERSON=1 node build-report-pdf.mjs   # -> preview/digital-signage-report-jakapob-preview.pdf
PERSON=2 node build-report-pdf.mjs   # -> preview/digital-signage-report-phornchanok-preview.pdf
PERSON=1 node build-report-docx.mjs  # -> digital-signage-report-jakapob.docx
PERSON=2 node build-report-docx.mjs  # -> digital-signage-report-phornchanok.docx
```
ต้องมี: Node + puppeteer-core + Chrome (ใน web-demos), Python + PyMuPDF, อินเทอร์เน็ต (โหลดโลโก้ ไม่มีก็ขึ้น placeholder)

**เนื้อหาที่ต่างกันรายคน** อยู่ 2 ที่:
- `report-data.mjs` — ปก/บทคัดย่อ (ท่อนงานที่ได้รับมอบหมาย)/กิตติกรรมประกาศ สร้างจาก `PERSONS[]` ตาม env อัตโนมัติ
- ใน `ch*.md` — บล็อก `[[P1]] ... [[/P1]]` = เฉพาะเล่มจักรภพ, `[[P2]] ... [[/P2]]` = เฉพาะเล่มพรชนก
  (นอกบล็อก = เนื้อหาร่วม ปรากฏทั้งสองเล่ม — ใช้อยู่ใน ch1 §1.5, ch3 §3.4, ch5 §5.4)

## ไฟล์ในชุดนี้
| ไฟล์ | หน้าที่ |
|---|---|
| `web-demos/build-report-pdf.mjs` | ตัวสร้างหลัก (md → HTML → Chrome PDF → stamp เลขหน้า) |
| `web-demos/toc_pages.py` | หาเลขหน้าหัวข้อ (marker) เพื่อทำสารบัญ |
| `web-demos/stamp_pages.py` | ประทับเลขหน้า (เว้นปก/ใบรับรอง → ก ข ค → 1 2 3) |
| `report-data.mjs` | ⭐ ข้อมูลเล่มทั้งหมด (ผู้จัดทำ 2 คน/ปก/บทคัดย่อ/กิตติกรรม) — แก้ที่นี่ที่เดียว ได้ทั้ง PDF+Word |
| `front-matter.md` | ร่างเก่าของส่วนหน้า (ปัจจุบันข้อมูลจริงย้ายไป `report-data.mjs` แล้ว — เก็บไว้อ้างอิงโครง) |
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
ผู้จัดทำทวนกิตติกรรมประกาศ/ตารางแบ่งหน้าที่ (ch1 ตารางที่ 1.1)/ท่อน duty ในบทคัดย่อ
~~ข้อมูลหน้าปกจริง~~ ✅ ครบ (2026-07-06) · ~~screenshot บท 4~~ ✅ ครบ 12 รูป (2026-07-03) · ~~โลโก้ ม.รังสิต~~ ✅ `assets/rsu-logo.png` (ตราทางการจากหน้าดาวน์โหลดโลโก้ ม.รังสิต, 2026-07-06)

## หมายเหตุ layout (2026-07-06)
- **ใบรับรอง (หน้า 2)** ทำตามเล่มตัวอย่างแล้ว: เรื่อง/โดย = label ชิดซ้าย · บล็อกหัวหน้าสาขา+วันที่เยื้องขวา อยู่ก่อนคณะกรรมการ · กรรมการ 2 คนชิดซ้าย ชื่อวงเล็บเยื้องใต้ (วงเล็บติดชื่อ ไม่เว้นวรรค)
- **ฝั่ง Word ระวังหน้าล้น**: Angsana ใน Word บรรทัดเปล่าสูง ~1.3cm (สูงกว่าที่คิดจาก 16pt×1.5) — ปก/ใบรับรองจึงใช้ blank น้อยกว่าฝั่ง PDF; ถ้าแก้แล้วสงสัยล้น ตรวจด้วย Word COM export เป็น PDF (`preview/docx-check-*.pdf`) แล้วเช็คว่าหน้า 2 ขึ้น "ใบรับรอง" และหน้า 3 ขึ้น "ก หัวข้อปริญญานิพนธ์"
