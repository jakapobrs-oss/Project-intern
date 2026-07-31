"""
Content endpoints — upload + approve workflow (§22 + §21)
"""
import uuid
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.deps import get_current_user, require_role
from app.core import queue, url_guard
from app.db import get_db
from app.models.content import Content, ApprovalStatus, ContentType
from app.models.user import User, Role
from app.schemas.content import ContentOut, ContentUpdate, ContentCreateUrl, ApprovalAction
from app.services import audit_service, content_service
from app.services.content_service import ContentServiceError


router = APIRouter()


_can_upload = require_role(Role.SUPER_ADMIN, Role.ADMIN, Role.EDITOR)
_can_approve = require_role(Role.SUPER_ADMIN, Role.ADMIN, Role.APPROVER)
_can_view = require_role(Role.SUPER_ADMIN, Role.ADMIN, Role.EDITOR, Role.APPROVER, Role.VIEWER, Role.OPERATOR)


@router.get("", response_model=list[ContentOut])
async def list_contents(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(_can_view),
):
    res = await db.execute(select(Content).order_by(Content.created_at.desc()))
    return res.scalars().all()


@router.post("/upload", response_model=ContentOut, status_code=201)
async def upload_content(
    request: Request,
    name: str = Form(...),
    description: str = Form(""),
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(_can_upload),
):
    """อัปโหลดไฟล์ media — auto detect type จาก magic bytes + SHA-256 dedupe"""
    try:
        content = await content_service.upload_content_file(
            db,
            file=file.file,
            filename=file.filename or "unnamed",
            name=name,
            description=description,
            created_by=user.id,
        )
    except ContentServiceError as e:
        raise HTTPException(status_code=400, detail={"code": e.code, "message": e.message})

    # โยนงานหนักเข้า background (best-effort — ถ้า Redis ล่ม upload ยังสำเร็จ)
    # เช็ค thumbnail_key == None เพื่อกัน re-process กรณี dedupe คืน content เดิม (§22)
    if content.type in (ContentType.IMAGE, ContentType.VIDEO) and content.thumbnail_key is None:
        await queue.enqueue("generate_thumbnail", str(content.id))
        if content.type == ContentType.VIDEO:
            await queue.enqueue("transcode_video", str(content.id))
    await audit_service.log_action(
        db, request, user, "content.upload",
        target_type="content", target_id=content.id,
        message=f"อัปโหลดสื่อ {content.name} ชนิด {content.type.value}",
    )
    return content


@router.post("/url", response_model=ContentOut, status_code=201)
async def create_url_content(
    payload: ContentCreateUrl,
    request: Request,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(_can_upload),
):
    """สร้าง content แบบ web/stream URL (ไม่อัปโหลดไฟล์)"""
    if payload.type not in (ContentType.WEB, ContentType.STREAM):
        raise HTTPException(400, "URL content ต้องเป็นชนิด web หรือ stream")
    # SSRF guard (§26) — กัน URL ชี้เข้า network ภายใน
    try:
        url_guard.validate_public_url(str(payload.url))
    except url_guard.UnsafeUrlError as e:
        raise HTTPException(status_code=400, detail={"code": "UNSAFE_URL", "message": e.message})
    content = Content(
        name=payload.name,
        description=payload.description,
        type=payload.type,
        url=str(payload.url),
        created_by=user.id,
    )
    db.add(content)
    await db.commit()
    await db.refresh(content)
    await audit_service.log_action(
        db, request, user, "content.create_url",
        target_type="content", target_id=content.id,
        message=f"เพิ่มสื่อแบบลิงก์ {content.name} ชนิด {content.type.value}",
    )
    return content


@router.get("/{content_id}", response_model=ContentOut)
async def get_content(
    content_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(_can_view),
):
    content = await db.get(Content, content_id)
    if content is None:
        raise HTTPException(404, "ไม่พบ content")
    return content


@router.patch("/{content_id}", response_model=ContentOut)
async def update_content(
    content_id: uuid.UUID,
    payload: ContentUpdate,
    request: Request,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(_can_upload),
):
    content = await db.get(Content, content_id)
    if content is None:
        raise HTTPException(404, "ไม่พบ content")
    data = payload.model_dump(exclude_unset=True)
    for k, v in data.items():
        setattr(content, k, v)
    await db.commit()
    await db.refresh(content)
    await audit_service.log_action(
        db, request, user, "content.update",
        target_type="content", target_id=content.id,
        message=f"แก้ไขสื่อ {content.name} ฟิลด์ {', '.join(sorted(data))}",
        extra={"fields": sorted(data)},
    )
    return content


@router.delete("/{content_id}", status_code=204)
async def delete_content(
    content_id: uuid.UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(_can_upload),
):
    content = await db.get(Content, content_id)
    if content is None:
        raise HTTPException(404, "ไม่พบ content")
    deleted_name = content.name
    await db.delete(content)
    await db.commit()
    await audit_service.log_action(
        db, request, user, "content.delete",
        target_type="content", target_id=content_id,
        message=f"ลบสื่อ {deleted_name}",
    )


@router.post("/{content_id}/submit", response_model=ContentOut)
async def submit_for_approval(
    content_id: uuid.UUID,
    request: Request,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(_can_upload),
):
    """ส่ง content ที่ status=draft → pending"""
    content = await db.get(Content, content_id)
    if content is None:
        raise HTTPException(404, "ไม่พบ content")
    if content.approval_status != ApprovalStatus.DRAFT:
        raise HTTPException(400, f"content อยู่ในสถานะ {content.approval_status.value} แล้ว")
    content.approval_status = ApprovalStatus.PENDING
    await db.commit()
    await db.refresh(content)
    await audit_service.log_action(
        db, request, user, "content.submit",
        target_type="content", target_id=content.id,
        message=f"ส่งสื่อ {content.name} เข้าคิวรออนุมัติ",
    )
    return content


@router.post("/{content_id}/approve", response_model=ContentOut)
async def approve_content(
    content_id: uuid.UUID,
    action: ApprovalAction,
    request: Request,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(_can_approve),
):
    content = await db.get(Content, content_id)
    if content is None:
        raise HTTPException(404, "ไม่พบ content")
    if action.approve:
        content.approval_status = ApprovalStatus.APPROVED
        content.approved_by = user.id
        content.approved_at = datetime.now(timezone.utc)
        content.rejection_reason = None
        audit_action = "content.approve"
        msg = f"approved content: {content.name}"
    else:
        content.approval_status = ApprovalStatus.REJECTED
        content.rejection_reason = action.rejection_reason or "ไม่ระบุเหตุผล"
        content.approved_by = user.id
        content.approved_at = datetime.now(timezone.utc)
        audit_action = "content.reject"
        msg = f"rejected content: {content.name} ({content.rejection_reason})"
    await db.commit()
    await db.refresh(content)

    # audit (Phase 5 rest — audit-on-more-events)
    await audit_service.log_event(
        db,
        action=audit_action,
        actor_id=str(user.id),
        actor_label=user.username,
        target_type="content",
        target_id=str(content.id),
        message=msg,
        **audit_service.extract_request_context(request),
    )
    return content
