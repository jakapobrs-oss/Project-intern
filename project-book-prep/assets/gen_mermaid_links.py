"""
สร้าง mermaid.live preview link (pako-encoded) จากไฟล์ .mmd
- ใช้ encoding แบบเดียวกับ mermaid-live-editor: pako.deflate(JSON state) -> URL-safe base64
- ได้ลิงก์ที่คลิกเปิดได้ทันที (แก้ไข/export PNG/SVG ใน browser) ฟรี ไม่ต้องลงอะไร
- มี round-trip decode test เพื่อยืนยันว่า encode ถูกต้องก่อนเขียนลงไฟล์

วิธีรัน:  python gen_mermaid_links.py
"""
import json
import zlib
import base64
from pathlib import Path

ASSETS_DIR = Path(__file__).parent


def mermaid_live_link(code: str, kind: str = "edit") -> str:
    """
    เข้ารหัส Mermaid diagram เป็นลิงก์ mermaid.live

    รูปแบบ state ตรงกับ mermaid-live-editor:
        pako.deflate(JSON.stringify(state), {level: 9}) -> base64url (ไม่มี padding)
    Python zlib.compress() ให้ zlib stream เหมือน pako.deflate() ทุกประการ
    """
    state = {
        "code": code,
        "mermaid": json.dumps({"theme": "default"}),
        "autoSync": True,
        "updateDiagram": True,
    }
    raw = json.dumps(state, ensure_ascii=False).encode("utf-8")
    # level 9 = บีบอัดสูงสุด (ตรงกับ live editor)
    deflated = zlib.compress(raw, 9)
    encoded = base64.urlsafe_b64encode(deflated).decode("ascii").rstrip("=")
    return f"https://mermaid.live/{kind}#pako:{encoded}"


def _verify_roundtrip(link: str, original_code: str) -> bool:
    """ถอดรหัสลิงก์กลับมา แล้วเทียบกับ code ต้นทาง — กัน encode เพี้ยน"""
    payload = link.split("#pako:", 1)[1]
    # เติม padding กลับให้ครบก่อน decode
    payload += "=" * (-len(payload) % 4)
    inflated = zlib.decompress(base64.urlsafe_b64decode(payload))
    state = json.loads(inflated)
    return state["code"] == original_code


# diagram ทั้งหมดที่จะสร้างลิงก์ (key -> ไฟล์ .mmd หรือ inline code)
DIAGRAMS = {
    "full": ASSETS_DIR / "er-full.mmd",
}

# subgraph 5-tier (inline — ตรงกับ er-diagram.md section 3)
TIER5_CODE = """erDiagram
    contents {
        uuid id PK
        enum type
        string storage_key
        string url
    }
    presentation_zones {
        uuid id PK
        uuid presentation_id FK
        uuid content_id FK
        string zone_key
        int order_index
    }
    presentations {
        uuid id PK
        json layout_json
        int duration_sec
    }
    plan_items {
        uuid id PK
        uuid plan_id FK
        uuid presentation_id FK
        int order_index
        int duration_sec_override
    }
    plans {
        uuid id PK
        string name UK
    }
    schedules {
        uuid id PK
        uuid plan_id FK
        uuid player_group_id FK
        int priority
        datetime start_at
        datetime end_at
    }

    contents      ||--o{ presentation_zones : "1 -> N (reuse)"
    presentations ||--o{ presentation_zones : "1 -> N"
    presentations ||--o{ plan_items         : "1 -> N"
    plans         ||--o{ plan_items         : "1 -> N"
    plans         ||--o{ schedules          : "1 -> N"
"""


def main() -> None:
    results: dict[str, str] = {}

    # 1) full ER จากไฟล์
    full_code = (ASSETS_DIR / "er-full.mmd").read_text(encoding="utf-8").strip()
    link = mermaid_live_link(full_code)
    assert _verify_roundtrip(link, full_code), "round-trip ล้มเหลว (full)"
    results["full"] = link

    # 2) subgraph 5-tier
    tier_code = TIER5_CODE.strip()
    link = mermaid_live_link(tier_code)
    assert _verify_roundtrip(link, tier_code), "round-trip ล้มเหลว (5-tier)"
    results["tier5"] = link

    # เขียนผลลัพธ์ลงไฟล์ + พิมพ์ออกจอ
    out = ASSETS_DIR / "mermaid-live-links.txt"
    lines = [f"{k}\t{v}" for k, v in results.items()]
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")

    print("[OK] สร้างลิงก์สำเร็จ (ผ่าน round-trip decode ทุกอัน):")
    for k, v in results.items():
        print(f"  - {k}: {v}")
    print(f"\nบันทึกที่: {out}")


if __name__ == "__main__":
    main()
