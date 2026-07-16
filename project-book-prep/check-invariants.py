# -*- coding: utf-8 -*-
"""ตรวจ invariant เล่มรายงานสหกิจ Project-intern (ทั้ง 2 เล่มรายคน)

รันหลัง build ทุกครั้งที่แก้เนื้อหา:
    cd E:\\Claude-WorkSpace\\web-demos
    PERSON=1 node build-report-pdf.mjs && PERSON=2 node build-report-pdf.mjs
    python E:\\Claude-WorkSpace\\Project-intern\\project-book-prep\\check-invariants.py

ตรวจ 2 ชั้น:
  ชั้น 1 (ต้นฉบับ md)  — ลำดับเลขรูป/ตาราง, ไฟล์รูปมีจริง, การอ้างอิงในเนื้อความ, ของชั่วคราวตกค้าง
  ชั้น 2 (PDF ที่ build) — เลขหน้าประทับ, สารบัญชี้หน้าถูก, caption ครบ, ไม่มี placeholder,
                          ไม่มีคำเคลมเกินจริงย้อนกลับมา, ชื่อผู้จัดทำไม่ปนเล่ม

เทคนิคที่ต้องระวัง (บทเรียนจากเล่มนี้ + เล่มปริญญานิพนธ์):
  - ภาษาไทยใน PDF ตัดบรรทัดกลางวลี → ต้องลบช่องว่างทั้งหมดก่อนเทียบข้อความเสมอ
  - marker mkrNNNmkr เป็นตัวอักษรขาว 0.75pt ที่ยังอยู่ใน text layer → ต้องถอดออกก่อนเทียบ
"""
import sys, os, re
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
import fitz

BASE = os.path.dirname(os.path.abspath(__file__))
BOOKS = {
    "jakapob (จักรภพ · Backend)":    ("digital-signage-report-jakapob-preview.pdf", "จักรภพ", "พรชนก"),
    "phornchanok (พรชนก · Frontend)": ("digital-signage-report-phornchanok-preview.pdf", "พรชนก", "จักรภพ"),
}
CHAPTERS = ["ch1-intro.md", "ch2-theory.md", "ch3-design.md", "ch4-results.md", "ch5-conclusion.md"]
FIRST_THAI, BODY_START = 3, 11   # ปก=1 ใบรับรอง=2 → ก เริ่มหน้า 3 · เนื้อหาหน้า 1 เริ่ม pdf 11
THAI = list("กขคงจฉชซฌญฎฏฐฑฒณดตถทธนบปผฝพฟภมยรลวศษสหฬอฮ")

MKR = re.compile(r"mkr\d+mkr")
sq = lambda s: re.sub(r"\s+", "", MKR.sub("", s))   # ลบ marker + ช่องว่างทั้งหมด
FAIL, WARN, INFO = [], [], []

# ============ ชั้น 1: ต้นฉบับ markdown ============
FIG_RE = re.compile(r"^\[\[FIG\|([^|]*)\|([^|]*)\|([^|\]]*)(?:\|([^\]]*))?\]\]$")
TBL_RE = re.compile(r"^\[\[TBL\|([^|]*)\|([^|\]]*)(?:\|([^\]]*))?\]\]$")

fig_defs, tbl_defs, prose_fig, prose_tbl = [], [], [], []
for f in CHAPTERS:
    for ln, raw in enumerate(open(os.path.join(BASE, f), encoding="utf-8").read().splitlines(), 1):
        t = raw.strip()
        if t.startswith(">"):           # blockquote = โน้ตถึงผู้เขียน ไม่ขึ้นในเล่ม
            continue
        m = FIG_RE.match(t)
        if m:
            fig_defs.append(dict(num=m[1].strip(), src=m[2].strip(), name=m[3].strip(), file=f, ln=ln)); continue
        m = TBL_RE.match(t)
        if m:
            tbl_defs.append(dict(num=m[1].strip(), name=m[2].strip(), file=f, ln=ln)); continue
        # รองรับทั้งอ้างเดี่ยว "รูปที่ 4.1" และอ้างเป็นช่วง "รูปที่ 4.4–4.6" (ขยายเป็น 4.4, 4.5, 4.6)
        def collect(word, bucket):
            for rm in re.finditer(word + r"\s*(\d+)\.(\d+)\s*(?:[–\-]\s*(?:(\d+)\.)?(\d+))?", t):
                ch, a, ch2, b = rm[1], int(rm[2]), rm[3], rm[4]
                if b is None or (ch2 and ch2 != ch):
                    bucket.append((f"{ch}.{a}", f, ln)); continue
                for i in range(a, int(b) + 1):
                    bucket.append((f"{ch}.{i}", f, ln))
        collect("รูปที่", prose_fig)
        collect("ตารางที่", prose_tbl)

# 1a) เลขรูป/ตารางในแต่ละบทต้องเรียง 1,2,3 ไม่ข้ามไม่ซ้ำ
def check_seq(defs, kind):
    groups = {}
    for d in defs:
        groups.setdefault(d["num"].rsplit(".", 1)[0], []).append(d)
    for pre, items in groups.items():
        for idx, d in enumerate(items, 1):
            if d["num"] != f"{pre}.{idx}":
                FAIL.append(f"[ลำดับ{kind}] {d['file']}:{d['ln']} พบ {kind}ที่ {d['num']} ตรงตำแหน่งที่ควรเป็น {pre}.{idx}")
                break
    return groups
fg = check_seq(fig_defs, "รูป"); tg = check_seq(tbl_defs, "ตาราง")
INFO.append("รูปต่อบท: " + ", ".join(f"บท{k}={len(v)}" for k, v in sorted(fg.items())) + f" (รวม {len(fig_defs)})")
INFO.append("ตารางต่อบท: " + ", ".join(f"บท{k}={len(v)}" for k, v in sorted(tg.items())) + f" (รวม {len(tbl_defs)})")

# 1b) ไฟล์รูปที่อ้างด้วย file: ต้องมีจริง
for d in fig_defs:
    if d["src"].startswith("file:") and not os.path.exists(os.path.join(BASE, d["src"][5:])):
        FAIL.append(f"[ไฟล์รูป] {d['file']}:{d['ln']} ไม่พบไฟล์ {d['src'][5:]} (รูปที่ {d['num']})")

# 1c) อ้างรูป/ตารางที่ไม่มีจริง
fig_nums = {d["num"] for d in fig_defs}
tbl_nums = {d["num"] for d in tbl_defs}
for num, f, ln in prose_fig:
    if num not in fig_nums: FAIL.append(f"[อ้างรูป] {f}:{ln} อ้าง 'รูปที่ {num}' แต่ไม่มีรูปนี้ในเล่ม")
for num, f, ln in prose_tbl:
    if num not in tbl_nums: FAIL.append(f"[อ้างตาราง] {f}:{ln} อ้าง 'ตารางที่ {num}' แต่ไม่มีตารางนี้ในเล่ม")

# 1d) รูป/ตารางที่ไม่ถูกอ้างถึงในเนื้อความเลย (ระเบียบเล่มไทย) — เตือนอย่างเดียว
#     หมายเหตุ: โลโก้เทคโนโลยีในบทที่ 2 เล่มตัวอย่างเดชธนาก็ไม่อ้างในเนื้อความ → ยอมรับได้
ref_f = {n for n, _, _ in prose_fig}; ref_t = {n for n, _, _ in prose_tbl}
unref = [d["num"] for d in fig_defs if d["num"] not in ref_f]
if unref: WARN.append(f"[ไม่ถูกอ้าง] รูปที่ไม่ถูกอ้างในเนื้อความ: {', '.join(unref)} (บท 2 = โลโก้ ยอมรับได้ตามเล่มตัวอย่าง)")
for d in tbl_defs:
    if d["num"] not in ref_t: FAIL.append(f"[ไม่ถูกอ้าง] ตารางที่ {d['num']} ({d['file']}) ไม่ถูกอ้างในเนื้อความ")

# 1e) ของชั่วคราว/ตัวเลขเก่าใน source
SRC = CHAPTERS + ["report-data.mjs", "bibliography.md"]
for f in SRC:
    p = os.path.join(BASE, f)
    if not os.path.exists(p): continue
    for ln, line in enumerate(open(p, encoding="utf-8").read().splitlines(), 1):
        if line.strip().startswith(">") or line.strip().startswith("//"): continue
        for pat, why in [(r"TODO|FIXME|XXX\b|lorem", "ข้อความชั่วคราวตกค้าง"),
                         (r"\[ชื่อ|\[รหัส|\[สาขา|\[คณะ|\[อาจารย์", "ช่องว่างรอกรอกข้อมูล")]:
            m = re.search(pat, line)
            if m: WARN.append(f"[source] {f}:{ln} พบ '{m.group(0)}' ({why}) — {line.strip()[:70]}")

# ============ ชั้น 2: PDF ============
def stamp_expected(p):
    if p < FIRST_THAI: return None
    if p < BODY_START:
        k = p - FIRST_THAI
        return THAI[k] if k < len(THAI) else str(k + 1)
    return str(p - BODY_START + 1)

# คำที่เคยเคลมเกินจริง — ห้ามย้อนกลับเข้าเล่ม (ดูผลตรวจ 2026-07-16)
BANNED = ["ฮาร์ดแวร์จริง", "อุปกรณ์ทดสอบการแสดงผล: Android TV", "จอจริง"]

for label, (fname, me, partner) in BOOKS.items():
    path = os.path.join(BASE, "preview", fname)
    if not os.path.exists(path):
        FAIL.append(f"[ไฟล์] ไม่พบ {fname} — build ก่อน"); continue
    doc = fitz.open(path); W = doc[0].rect.width; n = doc.page_count
    raws = [p.get_text() for p in doc]
    lines_pp = []
    for p in range(n):
        ls = []
        for b in doc[p].get_text("dict")["blocks"]:
            for l in b.get("lines", []):
                ls.append("".join(s["text"] for s in l["spans"]))
        lines_pp.append(ls)
    book = sq(" ".join(raws))
    INFO.append(f"{label}: {n} หน้า")

    # 2a) เลขหน้าประทับมุมขวาบนถูกทุกหน้า
    bad = 0
    for p in range(1, n + 1):
        got = re.sub(r"\s+", "", doc[p-1].get_text(clip=fitz.Rect(W-170, 18, W-38, 62)))
        exp = stamp_expected(p)
        if exp is None and got:
            FAIL.append(f"[เลขหน้า·{me}] pdf {p}: ปก/ใบรับรองไม่ควรมีเลข แต่พบ '{got}'"); bad += 1
        elif exp is not None and got != exp:
            FAIL.append(f"[เลขหน้า·{me}] pdf {p}: คาด '{exp}' พบ '{got}'"); bad += 1
    if not bad:
        INFO.append(f"  เลขหน้า·{me}: ถูกทุกหน้า (ปก+ใบรับรองไม่มีเลข → ก-{stamp_expected(BODY_START-1)} → 1-{n-BODY_START+1})")

    # 2b) caption ของทุกรูป/ตาราง ต้องปรากฏจริงในเล่ม + หาเลขหน้าไว้เทียบสารบัญ
    def page_of(text, pmin=BODY_START):
        t = sq(text)
        for p in range(pmin, n + 1):
            if t in sq(raws[p-1]): return p
        return None
    miss = 0
    for d in fig_defs:
        if not page_of("รูปที่" + d["num"] + d["name"][:12]):
            FAIL.append(f"[caption·{me}] รูปที่ {d['num']} ไม่ปรากฏในเล่ม"); miss += 1
    for d in tbl_defs:
        if not page_of("ตารางที่" + d["num"] + d["name"][:12]):
            FAIL.append(f"[caption·{me}] ตารางที่ {d['num']} ไม่ปรากฏในเล่ม"); miss += 1
    if not miss:
        INFO.append(f"  caption·{me}: ครบ (รูป {len(fig_defs)} + ตาราง {len(tbl_defs)})")

    # 2c) ทุกบทต้องขึ้นหน้าใหม่
    for c in range(1, 6):
        hits = [p for p in range(BODY_START, n+1) if any(sq(l) == sq(f"บทที่ {c}") for l in lines_pp[p-1])]
        if not hits: FAIL.append(f"[ขึ้นบท·{me}] ไม่พบหน้าเปิด 'บทที่ {c}'")

    # 2d) สารบัญ: ทุกหัวข้อ ## / ### ต้องมีแถวในสารบัญ และเลขหน้าต้องตรงหน้าจริง
    toc_txt = sq(" ".join(raws[FIRST_THAI+2 : BODY_START-1]))   # ช่วงหน้าสารบัญ (หลัง บทคัดย่อ/abstract/กิตติกรรม)
    for f in CHAPTERS:
        for line in open(os.path.join(BASE, f), encoding="utf-8").read().splitlines():
            t = line.strip()
            if not re.match(r"^#{2,3} \d", t): continue
            head = t.lstrip("# ").strip()
            real = page_of(head)
            if real is None:
                FAIL.append(f"[สารบัญ·{me}] ไม่พบหัวข้อ '{head[:40]}' ในเนื้อเล่ม"); continue
            want = sq(head + stamp_expected(real))
            if want not in toc_txt:
                FAIL.append(f"[สารบัญ·{me}] '{head[:40]}' อยู่หน้า {stamp_expected(real)} จริง "
                            f"แต่สารบัญไม่มีแถวนี้/เลขหน้าไม่ตรง")

    # 2e) placeholder / คำเคลมเกินจริง / ชื่อปนเล่ม
    for p in range(1, n + 1):
        if re.search(r"\[\s*ภาพประกอบ|ไม่พบไฟล์รูป", raws[p-1]):
            FAIL.append(f"[placeholder·{me}] pdf {p}: มีช่องรูปที่ resolve ไม่ได้")
    for ph in re.findall(r"\[[^\]\n]{2,60}\]", " ".join(raws)):
        if not re.match(r"^\[\d+\]$", ph):
            FAIL.append(f"[placeholder·{me}] เหลือช่องว่าง '{ph}' ในเล่ม")
    for b in BANNED:
        if sq(b) in book:
            FAIL.append(f"[เคลมเกินจริง·{me}] คำว่า '{b}' กลับเข้ามาในเล่มอีก — ดูผลตรวจ 2026-07-16")
    if sq(partner) in sq(raws[0]):
        FAIL.append(f"[ปกผิดคน·{me}] ปกเล่ม {me} มีชื่อ {partner}")
    if sq(me) not in sq(raws[0]):
        FAIL.append(f"[ปกผิดคน·{me}] ปกไม่มีชื่อ {me}")
    doc.close()

# ============ สรุป ============
print("=" * 74)
print("ผลตรวจ invariant — เล่มรายงานสหกิจ Project-intern (2 เล่มรายคน)")
print("=" * 74)
print(f"\n--- FAIL ({len(FAIL)}) ---")
for m in FAIL: print("  x", m)
print(f"\n--- WARN ({len(WARN)}) ---")
for m in WARN: print("  !", m)
print(f"\n--- INFO ({len(INFO)}) ---")
for m in INFO: print("  -", m)
print(f"\nสรุป: {'ผ่านทั้งหมด' if not FAIL else str(len(FAIL)) + ' จุดต้องแก้'}"
      f" · เตือน {len(WARN)} จุด")
sys.exit(1 if FAIL else 0)
