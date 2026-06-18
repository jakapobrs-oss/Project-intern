"""
Presentation endpoints (§35.1 — layer ใหม่ระหว่าง content กับ plan)
"""
import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.v1.deps import require_role
from app.db import get_db
from app.models.presentation import Presentation, PresentationZone
from app.models.user import Role, User
from app.schemas.presentation import (
    PresentationCreate,
    PresentationOut,
    PresentationUpdate,
)

router = APIRouter()


_can_edit = require_role(Role.SUPER_ADMIN, Role.ADMIN, Role.EDITOR)
_can_view = require_role(Role.SUPER_ADMIN, Role.ADMIN, Role.EDITOR, Role.APPROVER, Role.VIEWER, Role.OPERATOR)


async def _load_with_zones(db: AsyncSession, pid: uuid.UUID) -> Presentation | None:
    res = await db.execute(
        select(Presentation).where(Presentation.id == pid).options(selectinload(Presentation.zones))
    )
    return res.scalar_one_or_none()


@router.get("", response_model=list[PresentationOut])
async def list_presentations(db: AsyncSession = Depends(get_db), _: User = Depends(_can_view)):
    res = await db.execute(
        select(Presentation).order_by(Presentation.name).options(selectinload(Presentation.zones))
    )
    return res.scalars().all()


@router.post("", response_model=PresentationOut, status_code=201)
async def create_presentation(
    payload: PresentationCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(_can_edit),
):
    p = Presentation(
        name=payload.name,
        description=payload.description,
        layout_json=payload.layout_json,
        duration_sec=payload.duration_sec,
        created_by=user.id,
    )
    p.zones = [
        PresentationZone(
            zone_key=z.zone_key,
            content_id=z.content_id,
            params_json=z.params_json,
            order_index=z.order_index,
        )
        for z in payload.zones
    ]
    db.add(p)
    await db.commit()
    return await _load_with_zones(db, p.id)


@router.get("/{presentation_id}", response_model=PresentationOut)
async def get_presentation(
    presentation_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(_can_view),
):
    p = await _load_with_zones(db, presentation_id)
    if p is None:
        raise HTTPException(404, "ไม่พบ presentation")
    return p


@router.patch("/{presentation_id}", response_model=PresentationOut)
async def update_presentation(
    presentation_id: uuid.UUID,
    payload: PresentationUpdate,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(_can_edit),
):
    p = await _load_with_zones(db, presentation_id)
    if p is None:
        raise HTTPException(404, "ไม่พบ presentation")

    data = payload.model_dump(exclude_unset=True)
    if "zones" in data:
        # ลบ zones เก่าทั้งหมด → สร้างใหม่ (relationship มี cascade delete-orphan)
        p.zones = [
            PresentationZone(**z) for z in data.pop("zones")
        ]
    for k, v in data.items():
        setattr(p, k, v)
    await db.commit()
    return await _load_with_zones(db, p.id)


@router.delete("/{presentation_id}", status_code=204)
async def delete_presentation(
    presentation_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(_can_edit),
):
    p = await db.get(Presentation, presentation_id)
    if p is None:
        raise HTTPException(404, "ไม่พบ presentation")
    await db.delete(p)
    await db.commit()
