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
from app.services import audit_service, schedule_eval


router = APIRouter()

_can_edit = require_role(Role.SUPER_ADMIN, Role.ADMIN, Role.EDITOR)
_can_approve = require_role(Role.SUPER_ADMIN, Role.ADMIN, Role.APPROVER)
_can_view = require_role(Role.SUPER_ADMIN, Role.ADMIN, Role.EDITOR, Role.APPROVER, Role.VIEWER, Role.OPERATOR)


@router.get("", response_model=list[ScheduleOut])
async def list_schedules(db: AsyncSession = Depends(get_db), _: User = Depends(_can_view)):
    res = await db.execute(select(Schedule).order_by(Schedule.start_at.desc()))
    return res.scalars().all()


async def _detect_conflicts(db: AsyncSession, candidate: Schedule) -> list[Schedule]:
    """หา schedule ที่ชนกัน (group เดียวกัน + ช่วงเวลาซ้อน + priority เท่ากัน, §23)"""
    res = await db.execute(
        select(Schedule).where(
            Schedule.player_group_id == candidate.player_group_id,
            Schedule.status.in_([ScheduleStatus.ACTIVE, ScheduleStatus.PENDING_APPROVAL]),
            Schedule.is_active.is_(True),
        )
    )
    return schedule_eval.find_conflicts(candidate, list(res.scalars().all()))


@router.post("", response_model=ScheduleOut, status_code=201)
async def create_schedule(
    payload: ScheduleCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(_can_edit),
    force: bool = False,
):
    """
    Editor บันทึก → status = pending_approval (รอ approver)
    Admin บันทึก → status = active เลย
    (ดู §21)

    §23 conflict guard: ถ้ามี schedule บน group เดียวกัน ช่วงเวลาซ้อน + priority เท่ากัน
    → ปฏิเสธด้วย 409 (ยกเว้นส่ง ?force=true เพื่อยืนยันบันทึกทับ)
    """
    status = ScheduleStatus.ACTIVE if user.role in (Role.SUPER_ADMIN, Role.ADMIN) else ScheduleStatus.PENDING_APPROVAL
    sch = Schedule(
        **payload.model_dump(),
        status=status,
        created_by=user.id,
    )
    if not force:
        conflicts = await _detect_conflicts(db, sch)
        if conflicts:
            raise HTTPException(
                status_code=409,
                detail={
                    "code": "SCHEDULE_CONFLICT",
                    "message": "มี schedule ที่ priority เท่ากันและช่วงเวลาซ้อนกันบน group นี้ — ส่ง ?force=true เพื่อบันทึกทับ",
                    "conflicts": [{"id": str(c.id), "name": c.name, "priority": c.priority} for c in conflicts],
                },
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
