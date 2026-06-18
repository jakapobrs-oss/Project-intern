"""
LED transport — ส่ง raw bytes ไปยังจอ LED ผ่าน TCP

LED board ส่วนใหญ่เป็น network controller (รับ TCP ตรงจาก server)
ต่างจาก TV ที่ส่งผ่าน player (serial) — LED จึงยิงตรงจาก backend ได้
"""
from __future__ import annotations

import asyncio


async def send_tcp(ip: str, port: int, data: bytes, timeout: float = 5.0) -> bytes:
    """
    เปิด TCP → ส่ง data → อ่าน response (best-effort)
    raise asyncio.TimeoutError / OSError ถ้าต่อไม่ได้ — caller จัดการ
    """
    reader, writer = await asyncio.wait_for(asyncio.open_connection(ip, port), timeout=timeout)
    try:
        writer.write(data)
        await asyncio.wait_for(writer.drain(), timeout=timeout)
        try:
            resp = await asyncio.wait_for(reader.read(256), timeout=timeout)
        except asyncio.TimeoutError:
            resp = b""  # หลาย controller ไม่ตอบกลับ — ไม่ถือว่า error
        return resp
    finally:
        writer.close()
        try:
            await asyncio.wait_for(writer.wait_closed(), timeout=2.0)
        except (asyncio.TimeoutError, OSError):
            pass
