"""
หา IP ของผู้ใช้จริงจาก request — ใช้กับ audit log (§31)

ทำไมต้องมีไฟล์นี้: header `X-Forwarded-For` เป็นข้อมูลที่ "ใครส่งมาก็ได้" ถ้าเชื่อดื้อ ๆ
คนที่อยากปกปิดตัวก็แค่แนบ `X-Forwarded-For: 1.2.3.4` มาเอง แล้ว audit จะบันทึก IP ปลอม
ซึ่งทำให้ log ที่เก็บไว้เพื่อสืบสวนใช้ไม่ได้เลย

หลักที่ใช้: เชื่อ header นี้เฉพาะเมื่อ **เครื่องที่ต่อเข้ามาโดยตรง** เป็น proxy ที่เราตั้งไว้ว่า
เชื่อถือได้ (TRUSTED_PROXIES) เท่านั้น ถ้าไม่ใช่ = ใช้ IP ที่ต่อเข้ามาตรง ๆ ไม่สนใจ header

หมายเหตุสำหรับ dev: รันผ่าน `docker compose` แล้วเปิดเว็บที่ localhost จะเห็น IP เป็น
172.x.x.x เสมอ เพราะ Docker เปลี่ยน IP ต้นทางตอน forward พอร์ตให้ — ไม่ใช่บั๊กของโค้ด
ของจริงที่มี nginx คั่น (ดู nginx/signage.conf ตั้ง X-Forwarded-For ให้แล้ว) จะได้ IP จริง
เมื่อตั้ง TRUSTED_PROXIES ให้ครอบคลุมวง IP ของ nginx
"""
from __future__ import annotations

import ipaddress
from functools import lru_cache

from app.config import settings


@lru_cache(maxsize=8)
def _parse_networks(raw: str) -> tuple[ipaddress.IPv4Network | ipaddress.IPv6Network, ...]:
    """แปลงค่า config เป็นรายการ network — ข้ามค่าที่พิมพ์ผิดแทนการทำให้แอปพัง"""
    nets = []
    for part in (raw or "").split(","):
        part = part.strip()
        if not part:
            continue
        try:
            nets.append(ipaddress.ip_network(part, strict=False))
        except ValueError:
            # ค่าเสียใน config ไม่ควรทำให้ระบบล่ม — แค่ไม่เชื่อ proxy ตัวนั้น
            continue
    return tuple(nets)


def is_trusted_proxy(ip: str | None) -> bool:
    """IP นี้เป็น proxy ที่เราตั้งไว้ว่าเชื่อถือได้หรือไม่"""
    nets = _parse_networks(settings.trusted_proxies)
    if not nets or not ip:
        return False
    try:
        addr = ipaddress.ip_address(ip)
    except ValueError:
        return False
    return any(addr in net for net in nets)


def client_ip(request) -> str | None:
    """
    IP ของผู้ใช้จริง

    - ผู้ที่ต่อเข้ามาไม่ใช่ proxy ที่เชื่อถือ → ใช้ IP นั้นเลย (ไม่สนใจ X-Forwarded-For
      เพราะเป็นค่าที่ตัวผู้ใช้เองแนบมาได้)
    - เป็น proxy ที่เชื่อถือ → ไล่ดู X-Forwarded-For จากขวาไปซ้าย ข้าม proxy ที่เชื่อถือ
      ทั้งหมด ตัวแรกที่ไม่ใช่ proxy ของเรา = ผู้ใช้จริง (กันคนแนบค่าปลอมไว้ข้างหน้า)
    """
    if request is None or request.client is None:
        return None
    peer = request.client.host
    if not is_trusted_proxy(peer):
        return peer

    forwarded = request.headers.get("x-forwarded-for") or ""
    hops = [h.strip() for h in forwarded.split(",") if h.strip()]
    for hop in reversed(hops):
        if not is_trusted_proxy(hop):
            return hop
    # ทุก hop เป็น proxy ของเราเอง (หรือไม่มี header) → ดีที่สุดที่มีคือตัวซ้ายสุด
    return hops[0] if hops else peer
