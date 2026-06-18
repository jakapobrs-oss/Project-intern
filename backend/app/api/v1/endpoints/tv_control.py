"""
TV Control endpoints — admin sends commands + player pulls queue
"""
import uuid

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.deps import require_role
from app.db import get_db
from app.models.device import Device
from app.models.user import Role, User
from app.schemas.tv_control import (
    TVCommandRequest,
    TVCommandResponse,
    TVCommandStatus,
)
from app.services import audit_service
from app.services.tv_control import TVBrand, TVCommand, build_command
from app.services.tv_control import queue as tv_queue

router = APIRouter()


# admin / operator สามารถสั่งได้ (§21)
_can_command = require_role(Role.SUPER_ADMIN, Role.ADMIN, Role.OPERATOR)


@router.post("/devices/{device_id}/commands", response_model=TVCommandResponse, status_code=202)
async def send_command(
    device_id: uuid.UUID,
    payload: TVCommandRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(_can_command),
):
    """
    Admin/operator สั่ง command → enqueue ให้ player ดึงไปทำ
    202 Accepted (async — ใช้ /commands/{cmd_id}/status เช็คผล)
    """
    device = await db.get(Device, device_id)
    if device is None:
        raise HTTPException(404, "ไม่พบ device")

    # ตัดสินใจ brand
    brand_str = (payload.brand_override.value if payload.brand_override else (device.tv_brand or "cec"))
    try:
        brand = TVBrand(brand_str.lower())
    except ValueError:
        raise HTTPException(400, f"TV brand '{brand_str}' ไม่รองรับ") from None

    # สร้าง raw bytes
    cmd = TVCommand(brand=brand, command_type=payload.command_type, payload=payload.payload, set_id=payload.set_id)
    try:
        raw = build_command(cmd)
    except ValueError as e:
        raise HTTPException(400, str(e)) from e

    # enqueue
    cmd_id = await tv_queue.enqueue_command(
        device_id,
        {
            "brand": brand.value,
            "command_type": payload.command_type.value,
            "payload": payload.payload or {},
            "set_id": payload.set_id,
            "raw_bytes_hex": raw.hex(),
        },
    )

    # audit (Phase 5 rest — tv.command_sent)
    await audit_service.log_event(
        db,
        action="tv.command_sent",
        actor_id=str(user.id),
        actor_label=user.username,
        target_type="device",
        target_id=str(device_id),
        message=f"queued {brand.value} {payload.command_type.value} → {device.name}",
        extra={"cmd_id": cmd_id, "brand": brand.value, "command_type": payload.command_type.value, "set_id": payload.set_id},
        **audit_service.extract_request_context(request),
    )
    return TVCommandResponse(cmd_id=cmd_id, device_id=device_id)


@router.get("/commands/{cmd_id}/status", response_model=TVCommandStatus)
async def command_status(
    cmd_id: str,
    _: User = Depends(_can_command),
):
    rec = await tv_queue.get_command_status(cmd_id)
    if rec is None:
        raise HTTPException(404, "ไม่พบ command")
    return TVCommandStatus(
        cmd_id=rec.get("cmd_id", cmd_id),
        device_id=uuid.UUID(rec["device_id"]),
        status=rec.get("status", "unknown"),
        attempts=int(rec.get("attempts", 0)),
        error=rec.get("error"),
    )
