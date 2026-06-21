# -*- coding: utf-8 -*-
# render เล่มตัวอย่าง (เดชธนา) เป็นรูปทุกหน้า + วิเคราะห์ขนาดฟอนต์/ฟอนต์/ตำแหน่งเลขหน้า
# เพื่อลอก format ให้ตรงเป๊ะ
import sys, os, glob, collections
sys.stdout.reconfigure(encoding="utf-8", errors="replace")  # กัน cp1252 crash ตอน print ไทย
import fitz

PREP = r"E:\Claude-WorkSpace\Project-intern"
OUT = r"E:\Claude-WorkSpace\Project-intern\project-book-prep\example-pages"
os.makedirs(OUT, exist_ok=True)

pdfs = glob.glob(os.path.join(PREP, "*.pdf"))
print("PDFs found:", [os.path.basename(p) for p in pdfs])
src = pdfs[0]
doc = fitz.open(src)
print("FILE:", os.path.basename(src))
print("PAGES:", doc.page_count)
r0 = doc[0].rect
print("PAGE_SIZE_pt:", round(r0.width, 1), "x", round(r0.height, 1), "(A4 = 595 x 842)")

# render ทุกหน้า 150dpi
zoom = 150 / 72.0
mat = fitz.Matrix(zoom, zoom)
for i, page in enumerate(doc, 1):
    page.get_pixmap(matrix=mat).save(os.path.join(OUT, f"page-{i:02d}.png"))
print("RENDERED", doc.page_count, "pages ->", OUT)

# ---- วิเคราะห์ขนาดฟอนต์ทั้งเล่ม ----
sizes = collections.Counter()
sample = {}
fonts = collections.Counter()
for page in doc:
    for b in page.get_text("dict").get("blocks", []):
        for ln in b.get("lines", []):
            for s in ln.get("spans", []):
                txt = s["text"].strip()
                sz = round(s["size"], 1)
                if txt:
                    sizes[sz] += len(txt)
                    fonts[s["font"]] += 1
                    if sz not in sample:
                        sample[sz] = txt[:32]
print("\n=== FONT SIZES (pt : จำนวนอักขระ : ตัวอย่าง) ===")
for sz in sorted(sizes, reverse=True):
    print(f"  {sz:>5} pt : {sizes[sz]:>6} : {sample.get(sz,'')}")
print("\n=== FONT NAMES (ชื่อฟอนต์ : ครั้ง) ===")
for fn, c in fonts.most_common(12):
    print(f"  {c:>6} : {fn}")

# ---- ตำแหน่งเลขหน้า: หา text สั้น (<=3 ตัว) ใกล้ขอบบน/ล่าง ----
print("\n=== PAGE NUMBER candidates (หน้า 1-14) ===")
for i, page in enumerate(doc, 1):
    if i > 14:
        break
    h, w = page.rect.height, page.rect.width
    found = []
    for b in page.get_text("dict").get("blocks", []):
        for ln in b.get("lines", []):
            for s in ln.get("spans", []):
                txt = s["text"].strip()
                if txt and len(txt) <= 3:
                    x0, y0, x1, y1 = s["bbox"]
                    xc = (x0 + x1) / 2
                    where = "BOTTOM" if y0 > h - 75 else ("TOP" if y1 < 75 else None)
                    if where:
                        align = "center" if abs(xc - w / 2) < 70 else ("right" if xc > w / 2 else "left")
                        found.append(f"{where}-{align}(x={round(xc)},y={round(y0)}) '{txt}'")
    print(f"  p{i:02d}: " + ("; ".join(found) if found else "-"))

# ---- ย่อหน้า: ดู x เริ่มต้นของบรรทัดแรกแต่ละ paragraph เทียบ margin ซ้าย (หน้าเนื้อหา) ----
print("\n=== INDENT check (หน้าที่มี prose เยอะ — ดู x ซ้ายของแต่ละบรรทัด) ===")
for target in [14, 16, 18]:  # หน้าเนื้อหากลางเล่ม
    if target <= doc.page_count:
        page = doc[target - 1]
        xs = []
        for b in page.get_text("dict").get("blocks", []):
            for ln in b.get("lines", []):
                if ln.get("spans"):
                    xs.append(round(ln["spans"][0]["bbox"][0]))
        uniq = sorted(set(xs))
        print(f"  p{target}: left-x ที่พบ = {uniq[:12]}")
