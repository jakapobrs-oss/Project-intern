"""
Audit service — เขียน AuditLog entries แบบ best-effort (ไม่ raise ถ้า fail)

หลักการ:
- write-once, ไม่ throw error กลับไปทำให้ business flow ล่ม
- เรียกจาก endpoint หรือ service layer ทั้งสำหรับ success + denied + fail
- ใส่ context (ip, user-agent) ส่งมาจาก endpoint (Request object)

ตัวอย่าง action verb (กำหนดให้สม่ำเสมอ):
- auth.login / auth.refresh / auth.logout / auth.login_failed
- user.create / user.update / user.delete
- content.upload / content.approve / content.reject
- schedule.activate / schedule.pause
- device.pair / device.unpair / device.command_sent
- emergency.activate / emergency.cancel
- rbac.denied
"""
from __future__ import annotations

import contextlib
from typing import Any

from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.audit import AuditLog, AuditOutcome


async def log_event(
    db: AsyncSession,
    *,
    action: str,
    actor_type: str = "user",
    actor_id: str | None = None,
    actor_label: str | None = None,
    target_type: str | None = None,
    target_id: str | None = None,
    outcome: AuditOutcome = AuditOutcome.SUCCESS,
    ip_address: str | None = None,
    user_agent: str | None = None,
    message: str | None = None,
    extra: dict[str, Any] | None = None,
    autocommit: bool = True,
) -> AuditLog | None:
    """
    Insert audit row — best-effort
    ถ้า error → log warning แต่ไม่ raise (กัน audit ล่มทำ business flow ล่ม)

    autocommit=False ใช้เมื่อ caller ทำ transaction ของตัวเองอยู่
    (ค่า default True เพื่อให้ใช้ง่ายในกรณีทั่วไป)
    """
    try:
        row = AuditLog(
            action=action,
            actor_type=actor_type,
            actor_id=str(actor_id) if actor_id is not None else None,
            actor_label=actor_label,
            target_type=target_type,
            target_id=str(target_id) if target_id is not None else None,
            outcome=outcome,
            ip_address=ip_address,
            user_agent=(user_agent[:512] if user_agent else None),
            message=message,
            extra=extra,
        )
        db.add(row)
        if autocommit:
            await db.commit()
            await db.refresh(row)
        else:
            await db.flush()
        return row
    except Exception as e:  # noqa: BLE001 — audit ห้าม raise
        logger.warning(f"audit_service.log_event failed: {e}")
        # rollback ถ้าเรา autocommit เอง — ไม่ rollback caller's transaction
        if autocommit:
            with contextlib.suppress(Exception):
                await db.rollback()
        return None


def extract_request_context(request) -> dict[str, str | None]:
    """ดึง ip + user-agent จาก FastAPI Request (เรียกจาก endpoint)"""
    if request is None:
        return {"ip_address": None, "user_agent": None}
    # respect X-Forwarded-For (proxy/load-balancer)
    fwd = request.headers.get("x-forwarded-for")
    ip = (fwd.split(",")[0].strip() if fwd else None) or (
        request.client.host if request.client else None
    )
    return {
        "ip_address": ip,
        "user_agent": request.headers.get("user-agent"),
    }
