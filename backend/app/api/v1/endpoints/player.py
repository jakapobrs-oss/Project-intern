"""
Player endpoints — เรียกโดย player device (ไม่ใช่ user)
ใช้ device_token ที่ออกตอน pair (§26 แยก JWT)

- POST /player/pair          — claim pairing_code → ออก device_token
- GET  /player/me            — info ของ device ตัวเอง
- POST /player/heartbeat     — ping + telemetry
- GET  /player/manifest      — pull manifest (§35.2)
"""
from typing import Annotated
from fastapi import APIRouter, Depends, Header, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.media_link import public_media_base
from app.db import get_db
from app.models.device import Device
from app.models.audit import AuditOutcome
from app.schemas.device import (
    PairingClaimRequest, PairingClaimResponse,
    HeartbeatRequest, HeartbeatResponse, DeviceOut,
)
from app.schemas.manifest import Manifest
from app.services import audit_service, device_service, manifest_service
from app.services.device_service import DeviceServiceError


router = APIRouter()


async def get_player(
    db: AsyncSession = Depends(get_db),
    authorization: Annotated[str | None, Header()] = None,
) -> Device:
    """Auth สำหรับ player — Bearer <device_token>"""
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "ต้องระบุ Bearer token")
    token = authorization.split(" ", 1)[1].strip()
    device = await device_service.find_device_by_token(db, token)
    if device is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "device token ไม่ถูกต้อง")
    if not device.is_active:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "device ถูกปิดใช้งาน")
    return device


# ===== Pairing (ไม่ต้อง auth — ใช้ pairing_code) =====

@router.post("/pair", response_model=PairingClaimResponse)
async def pair(
    payload: PairingClaimRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """Player ส่ง pairing_code ที่ admin สร้างให้ → รับ device_token กลับ"""
    ctx = audit_service.extract_request_context(request)
    try:
        device, token = await device_service.claim_pairing(
            db,
            pairing_code=payload.pairing_code,
            platform=payload.platform,
            mac_address=payload.mac_address,
            serial_number=payload.serial_number,
            app_version=payload.app_version,
        )
    except DeviceServiceError as e:
        # audit pair failure — ใช้ pairing_code (snippet) เป็น label เพื่อ trace ความพยายาม
        await audit_service.log_event(
            db,
            action="device.pair",
            actor_type="device",
            actor_id=None,
            actor_label=f"code:{payload.pairing_code[:4]}***",
            outcome=AuditOutcome.FAIL,
            message=f"pair failed: {e.code} — {e.message}",
            **ctx,
        )
        code_to_status = {"INVALID_CODE": 404, "CODE_EXPIRED": 410}
        raise HTTPException(
            code_to_status.get(e.code, 400),
            detail={"code": e.code, "message": e.message},
        )

    # audit success (Phase 5 rest)
    await audit_service.log_event(
        db,
        action="device.pair",
        actor_type="device",
        actor_id=str(device.id),
        actor_label=device.name,
        target_type="device",
        target_id=str(device.id),
        message=f"device paired: {device.name} (platform={device.platform.value})",
        extra={"mac": device.mac_address, "serial": device.serial_number, "app_version": device.app_version},
        **ctx,
    )

    from datetime import datetime, timezone
    return PairingClaimResponse(
        device_id=device.id,
        device_token=token,
        server_time=datetime.now(timezone.utc),
    )


# ===== Authenticated player endpoints =====

@router.get("/me", response_model=DeviceOut)
async def player_me(device: Device = Depends(get_player)):
    return device


@router.post("/heartbeat", response_model=HeartbeatResponse)
async def heartbeat(
    payload: HeartbeatRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    device: Device = Depends(get_player),
):
    """Player ping เพื่อบอกสถานะ + รับว่า manifest outdated มั้ย"""
    await device_service.apply_heartbeat(
        db,
        device,
        status=payload.status,
        app_version=payload.app_version,
        ip_address=payload.ip_address,
        cpu_percent=payload.cpu_percent,
        temperature_c=payload.temperature_c,
        uptime_sec=payload.uptime_sec,
        current_manifest_version=payload.current_manifest_version,
    )
    # build manifest แบบเบาๆ (เอาเฉพาะ version) เทียบกับที่ player ส่งมา
    # ต้องส่ง media_base เดียวกับตอน GET /manifest ไม่งั้น version ที่เทียบจะคนละก้อน
    manifest = await manifest_service.build_manifest(db, device, public_media_base(request))
    outdated = (payload.current_manifest_version or "") != manifest.version

    from datetime import datetime, timezone
    return HeartbeatResponse(
        server_time=datetime.now(timezone.utc),
        manifest_outdated=outdated,
        latest_manifest_version=manifest.version,
    )


@router.get("/manifest", response_model=Manifest)
async def get_manifest(
    request: Request,
    db: AsyncSession = Depends(get_db),
    device: Device = Depends(get_player),
):
    """Manifest pre-computed สำหรับ player นี้ (§35.2)"""
    # ลิงก์สื่อประกอบจาก host ที่เครื่องเล่นใช้ยิงเข้ามา → เรียกกลับได้แน่นอน
    manifest = await manifest_service.build_manifest(db, device, public_media_base(request))
    # อัปเดต device.last_manifest_version เพื่อ track
    device.last_manifest_version = manifest.version
    await db.commit()
    return manifest


# ===== TV Command queue — player polls + acks (§24) =====

from app.schemas.tv_control import TVCommandInQueue, TVCommandAck  # noqa: E402
from app.services.tv_control import queue as tv_queue  # noqa: E402


@router.get("/commands", response_model=list[TVCommandInQueue])
async def player_pull_commands(
    device: Device = Depends(get_player),
):
    """Player pull pending TV commands จาก queue"""
    records = await tv_queue.pop_pending(device.id, max_count=5)
    return [
        TVCommandInQueue(
            cmd_id=r["cmd_id"],
            brand=r["brand"],
            command_type=r["command_type"],
            raw_bytes_hex=r["raw_bytes_hex"],
            payload=r.get("payload") if isinstance(r.get("payload"), dict) else None,
            set_id=int(r.get("set_id", 0)),
            attempts=int(r.get("attempts", 1)),
        )
        for r in records
    ]


@router.post("/commands/{cmd_id}/ack", status_code=204)
async def player_ack_command(
    cmd_id: str,
    payload: TVCommandAck,
    device: Device = Depends(get_player),
):
    """Player report ผลลัพธ์ของ command"""
    ok = await tv_queue.ack_command(device.id, cmd_id, payload.success, payload.error)
    if not ok:
        raise HTTPException(404, "ไม่พบ command นี้ใน inflight ของ device นี้")


# ===== Playback logging (§28 reporting) =====

from datetime import datetime, timezone  # noqa: E402
import uuid as _uuid  # noqa: E402
from pydantic import BaseModel  # noqa: E402
from app.models.playback import PlaybackLog  # noqa: E402


class PlaybackEventIn(BaseModel):
    content_id: _uuid.UUID | None = None
    presentation_id: _uuid.UUID | None = None
    played_at: datetime | None = None      # player ส่งเวลาจริง; ถ้าไม่ส่งใช้เวลา server
    duration_sec: float | None = None


class PlaybackBatchIn(BaseModel):
    events: list[PlaybackEventIn]


@router.post("/playback", status_code=204)
async def player_report_playback(
    payload: PlaybackBatchIn,
    db: AsyncSession = Depends(get_db),
    device: Device = Depends(get_player),
):
    """
    Player รายงาน batch ของ playback events (content ไหนเล่นเมื่อไหร่)
    → INSERT playback_logs สำหรับทำ play-count report (§28)
    """
    now = datetime.now(timezone.utc)
    for ev in payload.events:
        db.add(PlaybackLog(
            device_id=device.id,
            content_id=ev.content_id,
            presentation_id=ev.presentation_id,
            played_at=ev.played_at or now,
            duration_sec=ev.duration_sec,
        ))
    await db.commit()
