"""
Test LED board protocol builders (§6.C) — pure bytes, ไม่แตะ network
"""
import pytest

from app.services.led_control.base import (
    LedBrand, LedColor, LedEffect, LedMessage, build_led_message,
)


def test_generic_tcp_frame():
    msg = LedMessage(text="HI", color=LedColor.RED, effect=LedEffect.STATIC, speed=5)
    raw = build_led_message(LedBrand.GENERIC_TCP, msg)
    assert raw[0] == 0x02          # STX
    assert raw[-1] == 0x03         # ETX
    assert b"HI" in raw
    assert raw[1] == 0x01          # red color code


def test_generic_speed_clamped():
    msg = LedMessage(text="x", speed=999)
    raw = build_led_message(LedBrand.GENERIC_TCP, msg)
    assert raw[3] == 10            # clamp ที่ 10


def test_huidu_frame_header_tail():
    msg = LedMessage(text="ทดสอบ")
    raw = build_led_message(LedBrand.HUIDU, msg)
    assert raw[0] == 0xA5          # header
    assert raw[-1] == 0xAE         # tail
    # length field ตรงกับ utf-8 byte length
    payload_len = len("ทดสอบ".encode("utf-8"))
    assert raw[2] == (payload_len >> 8) & 0xFF
    assert raw[3] == payload_len & 0xFF


def test_xixun_line_protocol():
    msg = LedMessage(text="Hello", color=LedColor.GREEN, effect=LedEffect.SCROLL_LEFT, speed=7, window=2)
    raw = build_led_message(LedBrand.XIXUN, msg)
    text = raw.decode("utf-8")
    assert text.startswith("SEND 2 green scroll_left 7 Hello")
    assert text.endswith("\n")


def test_empty_text_rejected():
    with pytest.raises(ValueError):
        build_led_message(LedBrand.GENERIC_TCP, LedMessage(text=""))


def test_utf8_thai_roundtrip():
    msg = LedMessage(text="โรงพยาบาล")
    raw = build_led_message(LedBrand.GENERIC_TCP, msg)
    # ข้อความไทยอยู่ในเฟรม (utf-8)
    assert "โรงพยาบาล".encode("utf-8") in raw
