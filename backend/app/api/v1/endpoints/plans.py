"""
Plan endpoints (= playlist)
"""
import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.v1.deps import require_role
from app.db import get_db
from app.models.plan import Plan, PlanItem
from app.models.user import Role, User
from app.schemas.plan import PlanCreate, PlanOut, PlanUpdate

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
    db: AsyncSession = Depends(get_db),
    user: User = Depends(_can_edit),
):
    plan = Plan(name=payload.name, description=payload.description, created_by=user.id)
    plan.items = [PlanItem(**it.model_dump()) for it in payload.items]
    db.add(plan)
    await db.commit()
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
    db: AsyncSession = Depends(get_db),
    _: User = Depends(_can_edit),
):
    plan = await _load_with_items(db, plan_id)
    if plan is None:
        raise HTTPException(404, "ไม่พบ plan")
    data = payload.model_dump(exclude_unset=True)
    if "items" in data:
        plan.items = [PlanItem(**it) for it in data.pop("items")]
    for k, v in data.items():
        setattr(plan, k, v)
    await db.commit()
    return await _load_with_items(db, plan_id)


@router.delete("/{plan_id}", status_code=204)
async def delete_plan(plan_id: uuid.UUID, db: AsyncSession = Depends(get_db), _: User = Depends(_can_edit)):
    plan = await db.get(Plan, plan_id)
    if plan is None:
        raise HTTPException(404, "ไม่พบ plan")
    await db.delete(plan)
    await db.commit()
