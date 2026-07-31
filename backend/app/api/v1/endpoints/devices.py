"""
Device + PlayerGroup endpoints
ดู §13 ใน PLAN.md
"""
import uuid
from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.deps import get_current_user, require_role
from app.db import get_db
from app.models.device import Device, PlayerGroup, DeviceStatus
from app.models.user import User, Role
from app.schemas.device import (
    DeviceCreate, DeviceUpdate, DeviceOut,
    PlayerGroupCreate, PlayerGroupUpdate, PlayerGroupOut,
)
from app.services import audit_service, device_service


router = APIRouter()


_can_manage = require_role(Role.SUPER_ADMIN, Role.ADMIN)
_can_view = require_role(Role.SUPER_ADMIN, Role.ADMIN, Role.VIEWER, Role.OPERATOR, Role.EDITOR, Role.APPROVER)


# ===== Devices =====

@router.get("", response_model=list[DeviceOut])
async def list_devices(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(_can_view),
):
    res = await db.execute(select(Device).order_by(Device.name))
    return res.scalars().all()


@router.post("", response_model=DeviceOut, status_code=201)
async def create_device(
    payload: DeviceCreate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    actor: User = Depends(_can_manage),
):
    """สร้าง device + ออก pairing code อัตโนมัติ"""
    device = Device(**payload.model_dump())
    device_service.issue_pairing_code(device)
    device.status = DeviceStatus.UNPAIRED
    db.add(device)
    await db.commit()
    await db.refresh(device)
    await audit_service.log_action(
        db, request, actor, "device.create",
        target_type="device", target_id=device.id,
        message=f"สร้างจอ {device.name}",
    )
    return device


@router.get("/{device_id}", response_model=DeviceOut)
async def get_device(
    device_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(_can_view),
):
    device = await db.get(Device, device_id)
    if device is None:
        raise HTTPException(404, "ไม่พบ device")
    return device


@router.patch("/{device_id}", response_model=DeviceOut)
async def update_device(
    device_id: uuid.UUID,
    payload: DeviceUpdate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    actor: User = Depends(_can_manage),
):
    device = await db.get(Device, device_id)
    if device is None:
        raise HTTPException(404, "ไม่พบ device")
    data = payload.model_dump(exclude_unset=True)
    for k, v in data.items():
        setattr(device, k, v)
    await db.commit()
    await db.refresh(device)
    await audit_service.log_action(
        db, request, actor, "device.update",
        target_type="device", target_id=device.id,
        message=f"แก้ไขจอ {device.name} ฟิลด์ {', '.join(sorted(data))}",
        extra={"fields": sorted(data)},
    )
    return device


@router.delete("/{device_id}", status_code=204)
async def delete_device(
    device_id: uuid.UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
    actor: User = Depends(_can_manage),
):
    device = await db.get(Device, device_id)
    if device is None:
        raise HTTPException(404, "ไม่พบ device")
    deleted_name = device.name
    await db.delete(device)
    await db.commit()
    await audit_service.log_action(
        db, request, actor, "device.delete",
        target_type="device", target_id=device_id,
        message=f"ลบจอ {deleted_name}",
    )


@router.post("/{device_id}/regenerate-pairing", response_model=DeviceOut)
async def regenerate_pairing(
    device_id: uuid.UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
    actor: User = Depends(_can_manage),
):
    """รีเซ็ต pairing code (ถ้ายังไม่ได้ pair หรือต้องการ re-pair)"""
    device = await db.get(Device, device_id)
    if device is None:
        raise HTTPException(404, "ไม่พบ device")
    device_service.issue_pairing_code(device)
    device.device_token_hash = None
    device.paired_at = None
    device.status = DeviceStatus.UNPAIRED
    await db.commit()
    await db.refresh(device)
    # ออกรหัสจับคู่ใหม่ = ตัดสิทธิ์เครื่องเดิมออกจากระบบ ต้องมีร่องรอยว่าใครสั่ง
    await audit_service.log_action(
        db, request, actor, "device.regenerate_pairing",
        target_type="device", target_id=device.id,
        message=f"ออกรหัสจับคู่ใหม่ให้จอ {device.name}",
    )
    return device


# ===== PlayerGroup =====
# subroute /groups เพื่อแยกชัดจาก device

group_router = APIRouter()


def _set_group_members(group: PlayerGroup, devices: list[Device]) -> None:
    group.devices = devices


async def _load_devices(db: AsyncSession, device_ids: list[uuid.UUID]) -> list[Device]:
    if not device_ids:
        return []
    res = await db.execute(select(Device).where(Device.id.in_(device_ids)))
    return list(res.scalars().all())


@group_router.get("", response_model=list[PlayerGroupOut])
async def list_groups(db: AsyncSession = Depends(get_db), _: User = Depends(_can_view)):
    res = await db.execute(select(PlayerGroup).order_by(PlayerGroup.name))
    groups = res.scalars().all()
    return [_group_to_out(g) for g in groups]


@group_router.post("", response_model=PlayerGroupOut, status_code=201)
async def create_group(
    payload: PlayerGroupCreate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    actor: User = Depends(_can_manage),
):
    group = PlayerGroup(name=payload.name, description=payload.description)
    group.devices = await _load_devices(db, payload.device_ids)
    db.add(group)
    await db.commit()
    await db.refresh(group)
    await audit_service.log_action(
        db, request, actor, "group.create",
        target_type="group", target_id=group.id,
        message=f"สร้างกลุ่มจอ {group.name} ({len(group.devices)} จอ)",
    )
    return _group_to_out(group)


@group_router.patch("/{group_id}", response_model=PlayerGroupOut)
async def update_group(
    group_id: uuid.UUID,
    payload: PlayerGroupUpdate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    actor: User = Depends(_can_manage),
):
    group = await db.get(PlayerGroup, group_id)
    if group is None:
        raise HTTPException(404, "ไม่พบ group")
    data = payload.model_dump(exclude_unset=True)
    changed_fields = sorted(data)
    if "device_ids" in data:
        group.devices = await _load_devices(db, data.pop("device_ids"))
    for k, v in data.items():
        setattr(group, k, v)
    await db.commit()
    await db.refresh(group)
    await audit_service.log_action(
        db, request, actor, "group.update",
        target_type="group", target_id=group.id,
        message=f"แก้ไขกลุ่มจอ {group.name} ฟิลด์ {', '.join(changed_fields)}",
        extra={"fields": changed_fields},
    )
    return _group_to_out(group)


@group_router.delete("/{group_id}", status_code=204)
async def delete_group(
    group_id: uuid.UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
    actor: User = Depends(_can_manage),
):
    group = await db.get(PlayerGroup, group_id)
    if group is None:
        raise HTTPException(404, "ไม่พบ group")
    deleted_name = group.name
    await db.delete(group)
    await db.commit()
    await audit_service.log_action(
        db, request, actor, "group.delete",
        target_type="group", target_id=group_id,
        message=f"ลบกลุ่มจอ {deleted_name}",
    )


def _group_to_out(group: PlayerGroup) -> PlayerGroupOut:
    return PlayerGroupOut(
        id=group.id,
        name=group.name,
        description=group.description,
        device_ids=[d.id for d in group.devices],
        created_at=group.created_at,
        updated_at=group.updated_at,
    )
