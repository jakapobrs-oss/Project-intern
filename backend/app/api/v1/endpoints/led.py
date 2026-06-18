"""
LED board endpoints — ส่งข้อความขึ้นจอ LED (§6.C, scope บรีฟข้อ 2)

POST /led/devices/{id}/message — admin/operator ส่งข้อความ
LED controller ต่อ TCP ตรงจาก backend (ต่างจาก TV ที่ผ่าน player serial)
"""
import asyncio
import uuid

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.deps import require_role
from app.db import get_db
from app.models.device import Device
from app.models.user import User, Role
from app.services import audit_service
from app.services.led_control.base import (
    LedBrand, LedColor, LedEffect, LedMessage, build_led_message,
)
from app.services.led_control.transport import send_tcp


router = APIRouter()

_can_send = require_role(Role.SUPER_ADMIN, Role.ADMIN, Role.OPERATOR)

DEFAULT_LED_PORT = 5200  # พอร์ตยอดนิยมของ LED controller (override ได้ต่อ request)


class LedMessageIn(BaseModel):
    text: str = Field(..., min_length=1, max_length=1024)
    color: LedColor = LedColor.RED
    effect: LedEffect = LedEffect.SCROLL_LEFT
    speed: int = Field(5, ge=1, le=10)
    window: int = Field(0, ge=0, le=15)
    brand: LedBrand = LedBrand.GENERIC_TCP
    port: int = Field(DEFAULT_LED_PORT, ge=1, le=65535)


@router.post("/devices/{device_id}/message")
async def send_led_message(
    device_id: uuid.UUID,
    payload: LedMessageIn,
    request: Request,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(_can_send),
):
    """สร้าง raw bytes ตาม protocol ของ brand → ส่ง TCP ไปจอ LED"""
    device = await db.get(Device, device_id)
    if device is None:
        raise HTTPException(404, "ไม่พบ device")
    if not device.ip_address:
        raise HTTPException(400, "device นี้ยังไม่มี ip_address — ตั้งค่า IP ของจอ LED ก่อน")

    msg = LedMessage(
        text=payload.text,
        color=payload.color,
        effect=payload.effect,
        speed=payload.speed,
        window=payload.window,
    )
    raw = build_led_message(payload.brand, msg)

    sent = False
    response_hex = None
    error = None
    try:
        resp = await send_tcp(device.ip_address, payload.port, raw)
        sent = True
        response_hex = resp.hex()
    except (asyncio.TimeoutError, OSError) as e:
        error = f"ส่งไป LED ไม่สำเร็จ: {e}"

    await audit_service.log_event(
        db,
        action="led.message",
        actor_id=str(user.id),
        actor_label=user.username,
        target_type="device",
        target_id=str(device.id),
        message=f"LED message → {device.name}: {payload.text[:50]!r} (sent={sent})",
        extra={"brand": payload.brand.value, "bytes_hex": raw.hex(), "error": error},
        **audit_service.extract_request_context(request),
    )

    if not sent:
        raise HTTPException(502, detail={"code": "LED_SEND_FAILED", "message": error, "bytes_hex": raw.hex()})
    return {"sent": True, "bytes_hex": raw.hex(), "response_hex": response_hex}
