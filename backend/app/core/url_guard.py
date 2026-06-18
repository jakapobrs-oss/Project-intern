"""
SSRF protection (§26) — กัน URL ที่ user ส่งมา (web/stream/RSS) ชี้เข้า network ภายใน

ภัย: ถ้ารับ URL อิสระแล้ว server/player ไป fetch → อาจโดนหลอกให้เข้าถึง
     169.254.169.254 (cloud metadata), 127.0.0.1, 10.x/192.168.x (intranet)

ป้องกัน: parse → resolve hostname → ตรวจทุก IP ว่าไม่ใช่ private/loopback/
         link-local/reserved/multicast — block ถ้าเจอ
"""
from __future__ import annotations

import ipaddress
import socket
from urllib.parse import urlparse


class UnsafeUrlError(Exception):
    def __init__(self, message: str):
        self.message = message
        super().__init__(message)


# scheme ที่อนุญาต — http(s) สำหรับ web, rtsp/rtmp/hls สำหรับ stream
ALLOWED_SCHEMES = {"http", "https", "rtsp", "rtmp", "rtmps", "hls"}


def is_blocked_ip(ip_str: str) -> bool:
    """IP นี้อยู่ใน range ที่ห้ามเข้าถึงไหม (pure — test ง่าย)"""
    try:
        ip = ipaddress.ip_address(ip_str)
    except ValueError:
        return True  # parse ไม่ได้ → block ไว้ก่อน
    return (
        ip.is_private
        or ip.is_loopback
        or ip.is_link_local      # ครอบคลุม 169.254.0.0/16 (cloud metadata)
        or ip.is_reserved
        or ip.is_multicast
        or ip.is_unspecified
    )


def _resolve_ips(host: str) -> list[str]:
    """resolve hostname → list ของ IP (ทั้ง v4/v6) — raise ถ้า resolve ไม่ได้"""
    try:
        infos = socket.getaddrinfo(host, None)
    except socket.gaierror as e:
        raise UnsafeUrlError(f"resolve hostname ไม่ได้: {host}") from e
    return list({info[4][0] for info in infos})


def validate_public_url(url: str) -> None:
    """
    ตรวจ URL — raise UnsafeUrlError ถ้าไม่ปลอดภัย
    (scheme ไม่อนุญาต / ไม่มี host / resolve ไป IP ภายใน)
    """
    parsed = urlparse(url)
    if parsed.scheme.lower() not in ALLOWED_SCHEMES:
        raise UnsafeUrlError(f"scheme '{parsed.scheme}' ไม่อนุญาต (รับเฉพาะ {sorted(ALLOWED_SCHEMES)})")
    host = parsed.hostname
    if not host:
        raise UnsafeUrlError("URL ไม่มี host")

    # ถ้า host เป็น IP literal → เช็คตรงๆ
    try:
        ipaddress.ip_address(host)
        if is_blocked_ip(host):
            raise UnsafeUrlError(f"IP {host} เป็น address ภายใน — ไม่อนุญาต (กัน SSRF)")
        return
    except ValueError:
        pass  # ไม่ใช่ IP literal → resolve ต่อ

    for ip in _resolve_ips(host):
        if is_blocked_ip(ip):
            raise UnsafeUrlError(f"host {host} resolve ไปยัง IP ภายใน {ip} — ไม่อนุญาต (กัน SSRF)")
