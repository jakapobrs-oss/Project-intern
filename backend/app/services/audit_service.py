"""
Audit service — เขียน AuditLog entries แบบ best-effort (ไม่ raise ถ้า fail)

หลักการ:
- write-once, ไม่ throw error กลับไปทำให้ business flow ล่ม
- เรียกจาก endpoint หรือ service layer ทั้งสำหรับ success + denied + fail
- ใส่ context (ip, user-agent) ส่งมาจาก endpoint (Request object)

action verb ทั้งหมดอยู่ที่ AUDIT_ACTIONS ด้านล่าง — **แหล่งความจริงเดียว**
หน้าจอ audit ดึงรายการนี้ผ่าน GET /api/v1/audit/actions แทนการพิมพ์ลิสต์ซ้ำเอง
(เดิมฝั่งหน้าจอ hardcode ไว้แล้วหลุดจากของจริง จนมีตัวเลือกที่ไม่มีวันมีข้อมูล)
"""
from __future__ import annotations
from typing import Any
from fastapi import Request
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.client_ip import client_ip
from app.models.audit import AuditLog, AuditOutcome
from app.models.user import User


# ทุก action ที่ระบบเขียนจริง — เพิ่ม action ใหม่ที่ไหน ต้องมาเติมที่นี่ด้วย
# ไม่งั้นตัวกรองในหน้าจอจะไม่มีให้เลือก (แต่ข้อมูลยังถูกบันทึกปกติ)
AUDIT_ACTIONS: list[str] = [
    # การเข้าใช้งานระบบ
    "auth.login",
    "auth.logout",
    "auth.refresh",
    # ผู้ใช้งาน
    "user.create",
    "user.update",
    "user.delete",
    # สื่อ
    "content.upload",
    "content.create_url",
    "content.update",
    "content.delete",
    "content.submit",
    "content.approve",
    "content.reject",
    # เครื่องเล่น
    "device.create",
    "device.update",
    "device.delete",
    "device.pair",
    "device.regenerate_pairing",
    # กลุ่มจอ
    "group.create",
    "group.update",
    "group.delete",
    # ชุดนำเสนอ / ผังเวลา / ตารางออกอากาศ
    "presentation.create",
    "presentation.update",
    "presentation.delete",
    "plan.create",
    "plan.update",
    "plan.delete",
    "schedule.create",
    "schedule.update",
    "schedule.delete",
    # หมายเหตุ: การกดอนุมัติ (POST /schedules/{id}/approve) บันทึกเป็น schedule.activate
    # เพราะผลลัพธ์คือทำให้ตารางออกอากาศจริง — ไม่มี action ชื่อ schedule.approve
    "schedule.activate",
    "schedule.pause",
    # ประกาศฉุกเฉิน
    "emergency.create",
    "emergency.update",
    "emergency.activate",
    "emergency.cancel",
    # ควบคุมจอ
    "tv.command_sent",
    "led.message",
    # ความปลอดภัย
    "rbac.denied",
]


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
            try:
                await db.rollback()
            except Exception:  # noqa: BLE001
                pass
        return None


async def log_action(
    db: AsyncSession,
    request: Request | None,
    actor: User | None,
    action: str,
    *,
    target_type: str | None = None,
    target_id: Any = None,
    message: str | None = None,
    outcome: AuditOutcome = AuditOutcome.SUCCESS,
    extra: dict[str, Any] | None = None,
) -> AuditLog | None:
    """
    ทางลัดของ log_event สำหรับกรณีที่พบบ่อยที่สุด — "ผู้ใช้ที่ล็อกอินอยู่ทำอะไรกับอะไร"

    ดึง ip/user-agent จาก request และชื่อผู้ทำจาก actor ให้เอง เพื่อให้จุดเรียกสั้นลง
    (เดิมทุกจุดต้องเขียน actor_id/actor_label/extract_request_context เองครบทุกครั้ง
    ซึ่งยาวจนไม่มีใครอยากใส่ — เป็นสาเหตุหนึ่งที่ CRUD ส่วนใหญ่ไม่เคยถูกบันทึก)
    """
    return await log_event(
        db,
        action=action,
        actor_id=str(actor.id) if actor is not None else None,
        actor_label=actor.username if actor is not None else None,
        target_type=target_type,
        target_id=str(target_id) if target_id is not None else None,
        outcome=outcome,
        message=message,
        extra=extra,
        **extract_request_context(request),
    )


def extract_request_context(request) -> dict[str, str | None]:
    """
    ดึง ip + user-agent จาก FastAPI Request (เรียกจาก endpoint)

    IP คิดผ่าน core/client_ip.py ซึ่งเชื่อ X-Forwarded-For เฉพาะเมื่อมาจาก proxy
    ที่ตั้งไว้ว่าเชื่อถือได้ — ของเดิมเชื่อ header ดื้อ ๆ จึงถูกปลอมได้
    """
    if request is None:
        return {"ip_address": None, "user_agent": None}
    return {
        "ip_address": client_ip(request),
        "user_agent": request.headers.get("user-agent"),
    }
