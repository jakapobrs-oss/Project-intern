"""
Monitoring endpoints — /metrics (Prometheus), /audit (search), /readiness
Phase 5 §monitoring + §audit
"""
from datetime import datetime
from uuid import UUID
from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel, ConfigDict

from app.api.v1.deps import require_role
from app.core.metrics import build_metrics
from app.db import get_db
from app.models.audit import AuditLog, AuditOutcome
from app.models.user import Role
from app.services import audit_service


router = APIRouter()


# --- /metrics (no auth — protect ด้วย network policy / IP allowlist ระดับ proxy) ---
@router.get("/metrics", include_in_schema=False)
async def metrics(db: AsyncSession = Depends(get_db)) -> Response:
    body = await build_metrics(db)
    return Response(content=body, media_type="text/plain; version=0.0.4")


# --- /audit/logs ---
class AuditLogOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    actor_type: str
    actor_id: str | None
    actor_label: str | None
    action: str
    target_type: str | None
    target_id: str | None
    outcome: AuditOutcome
    ip_address: str | None
    message: str | None
    extra: dict | None
    created_at: datetime


@router.get("/audit/actions", response_model=list[str])
async def list_audit_actions(
    _=Depends(require_role(Role.SUPER_ADMIN, Role.ADMIN)),
):
    """
    รายชื่อ action ทั้งหมดที่ระบบบันทึก — ให้หน้าจอเอาไปทำตัวเลือกในตัวกรอง

    มีไว้เพื่อไม่ให้ฝั่งหน้าจอ hardcode รายการเอง ซึ่งเคยหลุดจากของจริงจนมีตัวเลือก
    ที่ไม่มีวันมีข้อมูล (auth.login_failed / content.upload / rbac.denied)
    """
    return audit_service.AUDIT_ACTIONS


@router.get("/audit/logs", response_model=list[AuditLogOut])
async def list_audit_logs(
    action: str | None = Query(None, description="filter exact action verb"),
    actor_id: str | None = None,
    target_id: str | None = None,
    outcome: AuditOutcome | None = None,
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    _=Depends(require_role(Role.SUPER_ADMIN, Role.ADMIN)),
    db: AsyncSession = Depends(get_db),
):
    """list audit log entries (admin only) — sort desc by created_at"""
    stmt = select(AuditLog).order_by(AuditLog.created_at.desc())
    if action:
        stmt = stmt.where(AuditLog.action == action)
    if actor_id:
        stmt = stmt.where(AuditLog.actor_id == actor_id)
    if target_id:
        stmt = stmt.where(AuditLog.target_id == target_id)
    if outcome:
        stmt = stmt.where(AuditLog.outcome == outcome)
    stmt = stmt.limit(limit).offset(offset)
    rows = (await db.execute(stmt)).scalars().all()
    return rows


# --- /readiness — เช็ค DB ใช้ได้จริง ---
@router.get("/readiness", include_in_schema=False)
async def readiness(db: AsyncSession = Depends(get_db)):
    """ตรวจ DB connection (deeper kว่า /healthz ที่เป็น liveness)"""
    from sqlalchemy import text
    try:
        await db.execute(text("SELECT 1"))
        return {"status": "ready", "db": "ok"}
    except Exception as e:  # noqa: BLE001
        return Response(
            content=f'{{"status":"not_ready","db_error":"{e}"}}',
            status_code=503,
            media_type="application/json",
        )
