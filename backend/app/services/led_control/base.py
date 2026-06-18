"""
LED board protocol builders (pure — ไม่มี I/O, test ได้)

จอ LED แต่ละยี่ห้อมี protocol ต่างกัน แต่ส่วนใหญ่ส่งผ่าน TCP/serial เป็น text + control code
ไฟล์นี้ scaffold 3 รูปแบบที่พบบ่อย — production เพิ่ม protocol ของยี่ห้อจริงตาม spec ที่ได้

หมายเหตุ: PLAN §12.3 ระบุ "LED board รอ spec" — โครงนี้รองรับการเสียบ protocol จริงภายหลัง
โดยเพิ่ม builder + ลงทะเบียนใน _BUILDERS
"""
from __future__ import annotations

import enum
from dataclasses import dataclass


class LedBrand(str, enum.Enum):
    GENERIC_TCP = "generic_tcp"   # STX + text + ETX (ใช้กับ controller ที่รับ text ตรงๆ)
    HUIDU = "huidu"               # frame: header + len + payload + checksum (Huidu HD-series)
    XIXUN = "xixun"               # line protocol (Xixun/Onbon รับ command ต่อบรรทัด)


class LedColor(str, enum.Enum):
    RED = "red"
    GREEN = "green"
    YELLOW = "yellow"
    WHITE = "white"


class LedEffect(str, enum.Enum):
    STATIC = "static"
    SCROLL_LEFT = "scroll_left"
    SCROLL_UP = "scroll_up"
    FLASH = "flash"


# map สี → code 1 byte (generic) — ปรับตาม controller จริง
_COLOR_CODE = {
    LedColor.RED: 0x01,
    LedColor.GREEN: 0x02,
    LedColor.YELLOW: 0x03,
    LedColor.WHITE: 0x07,
}

_EFFECT_CODE = {
    LedEffect.STATIC: 0x00,
    LedEffect.SCROLL_LEFT: 0x01,
    LedEffect.SCROLL_UP: 0x02,
    LedEffect.FLASH: 0x03,
}


@dataclass
class LedMessage:
    """ข้อความที่จะแสดงบนจอ LED"""
    text: str
    color: LedColor = LedColor.RED
    effect: LedEffect = LedEffect.SCROLL_LEFT
    speed: int = 5          # 1 (ช้า) - 10 (เร็ว)
    window: int = 0         # โซน/หน้าต่างบนจอ (0 = เต็มจอ)


def _checksum(data: bytes) -> int:
    return sum(data) & 0xFF


# ===== GENERIC_TCP =====
# Format: STX(0x02) [color] [effect] [speed] text... ETX(0x03)
def _build_generic(msg: LedMessage) -> bytes:
    color = _COLOR_CODE.get(msg.color, 0x07)
    effect = _EFFECT_CODE.get(msg.effect, 0x00)
    speed = max(1, min(10, msg.speed))
    header = bytes([0x02, color, effect, speed])
    return header + msg.text.encode("utf-8") + bytes([0x03])


# ===== HUIDU (HD-series, ย่อ) =====
# Format: [0xA5 header] [window] [len_hi len_lo] [payload utf-8] [checksum] [0xAE tail]
def _build_huidu(msg: LedMessage) -> bytes:
    payload = msg.text.encode("utf-8")
    length = len(payload)
    body = bytes([msg.window & 0xFF, (length >> 8) & 0xFF, length & 0xFF]) + payload
    return bytes([0xA5]) + body + bytes([_checksum(body)]) + bytes([0xAE])


# ===== XIXUN (line protocol) =====
# Format: "SEND <window> <color> <effect> <speed> <text>\n"
def _build_xixun(msg: LedMessage) -> bytes:
    speed = max(1, min(10, msg.speed))
    line = f"SEND {msg.window} {msg.color.value} {msg.effect.value} {speed} {msg.text}\n"
    return line.encode("utf-8")


_BUILDERS = {
    LedBrand.GENERIC_TCP: _build_generic,
    LedBrand.HUIDU: _build_huidu,
    LedBrand.XIXUN: _build_xixun,
}


def build_led_message(brand: LedBrand, msg: LedMessage) -> bytes:
    """Entry point — รับ brand + LedMessage → raw bytes ที่ส่งผ่าน TCP/serial"""
    builder = _BUILDERS.get(brand)
    if builder is None:
        raise ValueError(f"ไม่รองรับ LED brand: {brand}")
    if not msg.text:
        raise ValueError("ข้อความ LED ว่างไม่ได้")
    return builder(msg)
