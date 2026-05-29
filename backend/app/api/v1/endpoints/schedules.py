"""
Schedule endpoints — editor บันทึก, approver กด active (§21, §23)
"""
import uuid
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.deps import require_role
from app.db import get_db
from app.models.schedule import Schedule, ScheduleStatus
from app.models.user import User, Role
from app.schemas.plan import ScheduleCreate, ScheduleUpdate, ScheduleOut
from app.services import audit_service


router = APIRouter()

_can_edit = require_role(Role.SUPER_ADMIN, Role.ADMIN, Role.EDITOR)
_can_approve = require_role(Role.SUPER_ADMIN, Role.ADMIN, Role.APPROVER)
_can_view = require_role(Role.SUPER_ADMIN, Role.ADMIN, Role.EDITOR, Role.APPROVER, Role.VIEWER, Role.OPERATOR)


@router.get("", response_model=list[ScheduleOut])
async def list_schedules(db: AsyncSession = Depends(get_db), _: User = Depends(_can_view)):
    res = await db.execute(select(Schedule).order_by(Schedule.start_at.desc()))
    return res.scalars().all()


@router.post("", response_model=ScheduleOut, status_code=201)
async def create_schedule(
    payload: ScheduleCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(_can_edit),
):
    """
    Editor บันทึก → status = pending_approval (รอ approver)
    Admin บันทึก → status = active เลย
    (ดู §21)
    """
    status = ScheduleStatus.ACTIVE if user.role in (Role.SUPER_ADMIN, Role.ADMIN) else ScheduleStatus.PENDING_APPROVAL
    sch = Schedule(
        **payload.model_dump(),
        status=status,
        created_by=user.id,
    )
    if status == ScheduleStatus.ACTIVE:
        sch.approved_by = user.id
        sch.approved_at = datetime.now(timezone.utc)
    db.add(sch)
    await db.commit()
    await db.refresh(sch)
    return sch


@router.get("/{schedule_id}", response_model=ScheduleOut)
async def get_schedule(schedule_id: uuid.UUID, db: AsyncSession = Depends(get_db), _: User = Depends(_can_view)):
    sch = await db.get(Schedule, schedule_id)
    if sch is None:
        raise HTTPException(404, "ไม่พบ schedule")
    return sch


@router.patch("/{schedule_id}", response_model=ScheduleOut)
async def update_schedule(
    schedule_id: uuid.UUID,
    payload: ScheduleUpdate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(_can_edit),
):
    sch = await db.get(Schedule, schedule_id)
    if sch is None:
        raise HTTPException(404, "ไม่พบ schedule")
    for k, v in payload.model_dump(exclude_unset=True).items():
        setattr(sch, k, v)
    await db.commit()
    await db.refresh(sch)
    return sch


@router.delete("/{schedule_id}", status_code=204)
async def delete_schedule(
    schedule_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(_can_edit),
):
    sch = await db.get(Schedule, schedule_id)
    if sch is None:
        raise HTTPException(404, "ไม่พบ schedule")
    await db.delete(sch)
    await db.commit()


@router.post("/{schedule_id}/approve", response_model=ScheduleOut)
async def approve_schedule(
    schedule_id: uuid.UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(_can_approve),
):
    """Approve → ACTIVE"""
    sch = await db.get(Schedule, schedule_id)
    if sch is None:
        raise HTTPException(404, "ไม่พบ schedule")
    if sch.status not in (ScheduleStatus.PENDING_APPROVAL, ScheduleStatus.DRAFT):
        raise HTTPException(400, f"สถานะปัจจุบัน {sch.status.value} approve ไม่ได้")
    sch.status = ScheduleStatus.ACTIVE
    sch.approved_by = user.id
    sch.approved_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(sch)

    # audit (Phase 5 rest)
    await audit_service.log_event(
        db,
        action="schedule.activate",
        actor_id=str(user.id),
        actor_label=user.username,
        target_type="schedule",
        target_id=str(sch.id),
        message=f"activated schedule: {sch.name}",
        extra={"plan_id": str(sch.plan_id), "player_group_id": str(sch.player_group_id), "priority": sch.priority},
        **audit_service.extract_request_context(request),
    )
    return sch


@router.post("/{schedule_id}/pause", response_model=ScheduleOut)
async def pause_schedule(
    schedule_id: uuid.UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(_can_edit),
):
    sch = await db.get(Schedule, schedule_id)
    if sch is None:
        raise HTTPException(404, "ไม่พบ schedule")
    sch.status = ScheduleStatus.PAUSED
    await db.commit()
    await db.refresh(sch)

    await audit_service.log_event(
        db,
        action="schedule.pause",
        actor_id=str(user.id),
        actor_label=user.username,
        target_type="schedule",
        target_id=str(sch.id),
        message=f"paused schedule: {sch.name}",
        **audit_service.extract_request_context(request),
    )
    return sch
