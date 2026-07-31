"""
Plan endpoints (= playlist)
"""
import uuid
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.deps import require_role
from app.db import get_db
from app.models.plan import Plan, PlanItem
from app.models.user import User, Role
from app.schemas.plan import PlanCreate, PlanUpdate, PlanOut
from app.services import audit_service


router = APIRouter()


_can_edit = require_role(Role.SUPER_ADMIN, Role.ADMIN, Role.EDITOR)
_can_view = require_role(Role.SUPER_ADMIN, Role.ADMIN, Role.EDITOR, Role.APPROVER, Role.VIEWER, Role.OPERATOR)


async def _load_with_items(db: AsyncSession, plan_id: uuid.UUID) -> Plan | None:
    res = await db.execute(
        select(Plan).where(Plan.id == plan_id).options(selectinload(Plan.items))
    )
    return res.scalar_one_or_none()


@router.get("", response_model=list[PlanOut])
async def list_plans(db: AsyncSession = Depends(get_db), _: User = Depends(_can_view)):
    res = await db.execute(select(Plan).order_by(Plan.name).options(selectinload(Plan.items)))
    return res.scalars().all()


@router.post("", response_model=PlanOut, status_code=201)
async def create_plan(
    payload: PlanCreate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(_can_edit),
):
    plan = Plan(name=payload.name, description=payload.description, created_by=user.id)
    plan.items = [PlanItem(**it.model_dump()) for it in payload.items]
    db.add(plan)
    await db.commit()
    await audit_service.log_action(
        db, request, user, "plan.create",
        target_type="plan", target_id=plan.id,
        message=f"สร้างผังเล่นสื่อ {plan.name} ({len(payload.items)} รายการ)",
    )
    return await _load_with_items(db, plan.id)


@router.get("/{plan_id}", response_model=PlanOut)
async def get_plan(plan_id: uuid.UUID, db: AsyncSession = Depends(get_db), _: User = Depends(_can_view)):
    plan = await _load_with_items(db, plan_id)
    if plan is None:
        raise HTTPException(404, "ไม่พบ plan")
    return plan


@router.patch("/{plan_id}", response_model=PlanOut)
async def update_plan(
    plan_id: uuid.UUID,
    payload: PlanUpdate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(_can_edit),
):
    plan = await _load_with_items(db, plan_id)
    if plan is None:
        raise HTTPException(404, "ไม่พบ plan")
    data = payload.model_dump(exclude_unset=True)
    changed_fields = sorted(data)
    plan_name = plan.name
    if "items" in data:
        plan.items = [PlanItem(**it) for it in data.pop("items")]
    for k, v in data.items():
        setattr(plan, k, v)
    await db.commit()
    await audit_service.log_action(
        db, request, user, "plan.update",
        target_type="plan", target_id=plan_id,
        message=f"แก้ไขผังเล่นสื่อ {plan_name} ฟิลด์ {', '.join(changed_fields)}",
        extra={"fields": changed_fields},
    )
    return await _load_with_items(db, plan_id)


@router.delete("/{plan_id}", status_code=204)
async def delete_plan(
    plan_id: uuid.UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(_can_edit),
):
    plan = await db.get(Plan, plan_id)
    if plan is None:
        raise HTTPException(404, "ไม่พบ plan")
    deleted_name = plan.name
    await db.delete(plan)
    await db.commit()
    await audit_service.log_action(
        db, request, user, "plan.delete",
        target_type="plan", target_id=plan_id,
        message=f"ลบผังเล่นสื่อ {deleted_name}",
    )
