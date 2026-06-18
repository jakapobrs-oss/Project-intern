"""
ClamAV virus scan hook (§22) — env-gated

upload ไฟล์ → ถ้า CLAMAV_ENABLED=true → stream ไป clamd (INSTREAM) เพื่อสแกน
ใช้ raw socket protocol ของ clamd ตรงๆ (ไม่ต้องเพิ่ม dependency)

ปิดโดย default (dev ไม่มี clamd daemon) — เปิดใน production ที่รัน clamav container
fail-closed: ถ้าเปิดแล้วต่อ clamd ไม่ได้ → reject upload (ปลอดภัยกว่า) เว้นแต่ตั้ง fail_closed=false
"""
from __future__ import annotations

import socket
import struct
from typing import BinaryIO

from loguru import logger

from app.config import settings


class VirusFoundError(Exception):
    def __init__(self, signature: str):
        self.signature = signature
        super().__init__(f"พบไวรัส: {signature}")


class ScanUnavailableError(Exception):
    """ต่อ clamd ไม่ได้ (ใช้ตอน fail-closed)"""


_CHUNK = 64 * 1024


def _scan_stream_via_clamd(file: BinaryIO, host: str, port: int, timeout: float = 30.0) -> None:
    """ส่งไฟล์ไป clamd ผ่าน INSTREAM — raise VirusFoundError ถ้าเจอ"""
    with socket.create_connection((host, port), timeout=timeout) as sock:
        sock.sendall(b"zINSTREAM\x00")
        while True:
            chunk = file.read(_CHUNK)
            if not chunk:
                break
            sock.sendall(struct.pack("!L", len(chunk)) + chunk)
        sock.sendall(struct.pack("!L", 0))  # zero-length = จบ stream

        resp = b""
        while b"\x00" not in resp:
            data = sock.recv(4096)
            if not data:
                break
            resp += data

    text = resp.decode(errors="replace").strip("\x00").strip()
    # clamd ตอบ "stream: OK" หรือ "stream: Eicar-Test-Signature FOUND"
    if text.endswith("FOUND"):
        signature = text.split(":", 1)[-1].replace("FOUND", "").strip()
        raise VirusFoundError(signature)
    if "ERROR" in text:
        raise ScanUnavailableError(f"clamd error: {text}")


def scan_fileobj(file: BinaryIO) -> None:
    """
    สแกนไฟล์ — no-op ถ้า CLAMAV_ENABLED=false
    raise VirusFoundError ถ้าเจอไวรัส
    raise ScanUnavailableError ถ้าต่อ clamd ไม่ได้ + fail_closed
    หมายเหตุ: caller ต้อง file.seek(0) ต่อเองหลังเรียก
    """
    if not getattr(settings, "clamav_enabled", False):
        return
    host = getattr(settings, "clamav_host", "clamav")
    port = int(getattr(settings, "clamav_port", 3310))
    fail_closed = getattr(settings, "clamav_fail_closed", True)
    try:
        file.seek(0)
        _scan_stream_via_clamd(file, host, port)
    except VirusFoundError:
        raise
    except (OSError, ScanUnavailableError) as e:
        logger.warning(f"clamav scan ติดต่อ daemon ไม่ได้: {e}")
        if fail_closed:
            raise ScanUnavailableError("สแกนไวรัสไม่สำเร็จ (clamd ติดต่อไม่ได้) — ปฏิเสธ upload") from e
