"""
Emergency Broadcast endpoints (Phase 5, §8.5 Top-5 optional)
- super_admin + operator + admin สร้าง/active/cancel
- editor/viewer ดูได้อย่างเดียว
- player API จะใช้ presigned manifest ดึง active broadcast (Phase 5 manifest-integration)
"""
from datetime import datetime, timezone
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.deps import get_current_user, require_role
from app.db import get_db
from app.models.user import User, Role
from app.models.emergency import EmergencyBroadcast, EmergencyStatus
from app.schemas.emergency import EmergencyCreate, EmergencyUpdate, EmergencyOut
from app.services import audit_service
from app.models.audit import AuditOutcome


router = APIRouter()


MUTATE_ROLES = (Role.SUPER_ADMIN, Role.ADMIN, Role.OPERATOR)


# ลงทะเบียนทั้ง "" และ "/" — กัน redirect chain ผ่าน Next proxy:
# /emergency (ไม่มี slash) เคยโดน FastAPI 307 ไป http://backend:8000/... ซึ่ง browser
# resolve ไม่ได้ (hostname ภายใน Docker) ส่วนฟอร์มมี slash ก็โดน Next ตัด slash (308) ก่อนถึง backend
@router.get("", response_model=list[EmergencyOut], include_in_schema=False)
@router.get("/", response_model=list[EmergencyOut])
async def list_broadcasts(
    status_filter: EmergencyStatus | None = None,
    _: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """list broadcasts (ทุก role ดูได้)"""
    stmt = select(EmergencyBroadcast).order_by(EmergencyBroadcast.created_at.desc())
    if status_filter is not None:
        stmt = stmt.where(EmergencyBroadcast.status == status_filter)
    rows = (await db.execute(stmt)).scalars().all()
    return rows


@router.post("", response_model=EmergencyOut, status_code=status.HTTP_201_CREATED, include_in_schema=False)
@router.post("/", response_model=EmergencyOut, status_code=status.HTTP_201_CREATED)
async def create_broadcast(
    body: EmergencyCreate,
    request: Request,
    user: User = Depends(require_role(*MUTATE_ROLES)),
    db: AsyncSession = Depends(get_db),
):
    row = EmergencyBroadcast(
        title=body.title,
        kind=body.kind,
        payload=body.payload,
        target=body.target.model_dump(mode="json"),
        priority=body.priority,
        starts_at=body.starts_at,
        ends_at=body.ends_at,
        requires_ack=body.requires_ack,
        notes=body.notes,
        created_by=user.id,
        status=EmergencyStatus.DRAFT,
    )
    db.add(row)
    await db.commit()
    await db.refresh(row)

    await audit_service.log_event(
        db,
        action="emergency.create",
        actor_id=str(user.id),
        actor_label=user.username,
        target_type="emergency",
        target_id=str(row.id),
        message=f"created emergency broadcast: {row.title}",
        **audit_service.extract_request_context(request),
    )
    return row


@router.patch("/{bid}", response_model=EmergencyOut)
async def update_broadcast(
    bid: UUID,
    body: EmergencyUpdate,
    request: Request,
    user: User = Depends(require_role(*MUTATE_ROLES)),
    db: AsyncSession = Depends(get_db),
):
    row = await db.get(EmergencyBroadcast, bid)
    if row is None:
        raise HTTPException(404, "broadcast ไม่พบ")
    if row.status not in (EmergencyStatus.DRAFT,):
        raise HTTPException(409, "แก้ไขได้เฉพาะ DRAFT — ใช้ /cancel แล้วสร้างใหม่")

    data = body.model_dump(exclude_unset=True)
    if "target" in data and data["target"] is not None:
        data["target"] = body.target.model_dump(mode="json")  # type: ignore[union-attr]
    for k, v in data.items():
        setattr(row, k, v)

    await db.commit()
    await db.refresh(row)
    await audit_service.log_action(
        db, request, user, "emergency.update",
        target_type="emergency", target_id=row.id,
        message=f"แก้ไขประกาศฉุกเฉิน {row.title} ฟิลด์ {', '.join(sorted(data))}",
        extra={"fields": sorted(data)},
    )
    return row


@router.post("/{bid}/activate", response_model=EmergencyOut)
async def activate_broadcast(
    bid: UUID,
    request: Request,
    user: User = Depends(require_role(*MUTATE_ROLES)),
    db: AsyncSession = Depends(get_db),
):
    """activate broadcast — เปลี่ยน status เป็น ACTIVE + set acknowledged_at"""
    row = await db.get(EmergencyBroadcast, bid)
    if row is None:
        raise HTTPException(404, "broadcast ไม่พบ")
    if row.status != EmergencyStatus.DRAFT:
        raise HTTPException(409, f"broadcast อยู่สถานะ {row.status.value} แล้ว")

    now = datetime.now(timezone.utc)
    row.status = EmergencyStatus.ACTIVE
    row.acknowledged_at = now
    if row.starts_at is None:
        row.starts_at = now

    await db.commit()
    await db.refresh(row)

    await audit_service.log_event(
        db,
        action="emergency.activate",
        actor_id=str(user.id),
        actor_label=user.username,
        target_type="emergency",
        target_id=str(row.id),
        message=f"activated emergency: {row.title}",
        extra={"priority": row.priority, "target": row.target},
        **audit_service.extract_request_context(request),
    )
    # Manifest integration: manifest version จะ auto-bump เพราะ _compute_version()
    # คำนวณจาก body (รวม emergencies) → heartbeat รอบถัดไป player จะเห็น outdated → fetch ใหม่
    # Worst-case latency = cache_seconds (default 60s) — เพียงพอกับ emergency broadcast
    return row


@router.post("/{bid}/cancel", response_model=EmergencyOut)
async def cancel_broadcast(
    bid: UUID,
    request: Request,
    user: User = Depends(require_role(*MUTATE_ROLES)),
    db: AsyncSession = Depends(get_db),
):
    row = await db.get(EmergencyBroadcast, bid)
    if row is None:
        raise HTTPException(404, "broadcast ไม่พบ")
    if row.status in (EmergencyStatus.EXPIRED, EmergencyStatus.CANCELLED):
        raise HTTPException(409, f"broadcast อยู่สถานะ {row.status.value} แล้ว")

    row.status = EmergencyStatus.CANCELLED
    row.ends_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(row)

    await audit_service.log_event(
        db,
        action="emergency.cancel",
        actor_id=str(user.id),
        actor_label=user.username,
        target_type="emergency",
        target_id=str(row.id),
        message=f"cancelled emergency: {row.title}",
        **audit_service.extract_request_context(request),
    )
    return row


@router.get("/{bid}", response_model=EmergencyOut)
async def get_broadcast(
    bid: UUID,
    _: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    row = await db.get(EmergencyBroadcast, bid)
    if row is None:
        raise HTTPException(404, "broadcast ไม่พบ")
    return row
