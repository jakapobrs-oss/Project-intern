"""
Manifest builder (§35.2) — pre-computed JSON ต่อ player

Flow:
1. หา player_group ของ device
2. หา schedules ที่ active บน group นั้น (ตอนนี้/อนาคต)
3. สำหรับแต่ละ schedule → load plan → load plan_items (sorted) → load presentations → zones → contents
4. สร้าง pre-signed URL ให้ content (S3)
5. คำนวณ version checksum
"""
import hashlib
import json
import uuid
from datetime import datetime, timezone
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.storage import presigned_get_url
from app.services import schedule_eval
from app.models.device import Device
from app.models.schedule import Schedule, ScheduleStatus
from app.models.plan import Plan
from app.models.presentation import Presentation
from app.models.content import Content, ContentType
from app.models.emergency import EmergencyBroadcast, EmergencyStatus
from app.schemas.manifest import (
    Manifest, ManifestItem, ManifestZone, ManifestSchedule, ManifestEmergency,
)


PRESIGNED_TTL = 3600  # 1 ชม. — player จะ poll manifest ใหม่ก่อน URL หมด


async def _device_schedules(db: AsyncSession, device: Device) -> list[Schedule]:
    """หา schedule ที่ active สำหรับ device นี้ — ผ่าน player_group membership"""
    group_ids = [g.id for g in device.groups]
    if not group_ids:
        return []
    now = datetime.now(timezone.utc)
    stmt = (
        select(Schedule)
        .where(
            Schedule.player_group_id.in_(group_ids),
            Schedule.status == ScheduleStatus.ACTIVE,
            Schedule.is_active.is_(True),
        )
        # ใช้ปัจจุบัน + อนาคตใกล้ — ของอดีตที่ expired ไม่ต้องส่ง
        .order_by(Schedule.priority.desc(), Schedule.start_at)
    )
    res = await db.execute(stmt)
    schedules = list(res.scalars().all())
    # filter (§23): เช็ค date-range + RRULE + daily window + วันในสัปดาห์ ตาม timezone ของ device
    # is_active_now() coerce datetime เป็น aware เองแล้ว (ปลอดภัยทั้ง SQLite/Postgres)
    # device อาจไม่มี field timezone → fallback ไป settings.app_timezone ใน schedule_eval
    device_tz = getattr(device, "timezone", None)
    return schedule_eval.filter_active(schedules, now=now, device_tz=device_tz)


def _content_url(content: Content) -> str | None:
    """คืน playable URL ของ content — file ใช้ presigned, web/stream ใช้ url ตรงๆ"""
    if content.type in (ContentType.WEB, ContentType.STREAM):
        return content.url
    if content.storage_key:
        return presigned_get_url(content.storage_key, expires_in=PRESIGNED_TTL)
    return None


async def _plan_to_items(db: AsyncSession, plan_id: uuid.UUID) -> list[ManifestItem]:
    """expand plan → plan_items → presentations → zones → contents"""
    plan = (await db.execute(
        select(Plan).where(Plan.id == plan_id).options(selectinload(Plan.items))
    )).scalar_one_or_none()
    if plan is None:
        return []

    # load presentations + zones + contents ทีเดียว (ลด N+1)
    presentation_ids = [it.presentation_id for it in plan.items]
    if not presentation_ids:
        return []

    pres_res = await db.execute(
        select(Presentation)
        .where(Presentation.id.in_(presentation_ids))
        .options(selectinload(Presentation.zones))
    )
    presentations_by_id: dict[uuid.UUID, Presentation] = {p.id: p for p in pres_res.scalars().all()}

    # collect content ids ที่ใช้
    content_ids: set[uuid.UUID] = set()
    for p in presentations_by_id.values():
        for z in p.zones:
            content_ids.add(z.content_id)

    contents_by_id: dict[uuid.UUID, Content] = {}
    if content_ids:
        c_res = await db.execute(select(Content).where(Content.id.in_(content_ids)))
        contents_by_id = {c.id: c for c in c_res.scalars().all()}

    items: list[ManifestItem] = []
    for plan_item in sorted(plan.items, key=lambda x: x.order_index):
        p = presentations_by_id.get(plan_item.presentation_id)
        if p is None:
            continue
        zones = []
        for z in sorted(p.zones, key=lambda x: x.order_index):
            c = contents_by_id.get(z.content_id)
            if c is None:
                continue
            zones.append(ManifestZone(
                zone_key=z.zone_key,
                content_id=c.id,
                content_type=c.type.value,
                content_url=_content_url(c),
                params=z.params_json or {},
            ))
        items.append(ManifestItem(
            presentation_id=p.id,
            presentation_name=p.name,
            layout=p.layout_json or {},
            duration_sec=plan_item.duration_sec_override or p.duration_sec,
            order_index=plan_item.order_index,
            zones=zones,
        ))
    return items


async def _active_emergencies_for(db: AsyncSession, device: Device) -> list[EmergencyBroadcast]:
    """
    หา emergency broadcast ที่ active + targeting device นี้
    Targeting rules (อ่าน target JSON):
      - {"all": true}                 → ทุก device
      - {"device_ids": [...]}         → เฉพาะ device_id ที่ระบุ
      - {"group_ids": [...]}          → device ที่อยู่ใน group เหล่านั้น
    Time window:
      - starts_at NULL หรือ <= now
      - ends_at   NULL หรือ >= now
    """
    now = datetime.now(timezone.utc)
    stmt = (
        select(EmergencyBroadcast)
        .where(EmergencyBroadcast.status == EmergencyStatus.ACTIVE)
        .order_by(EmergencyBroadcast.priority.desc(), EmergencyBroadcast.created_at.desc())
    )
    res = await db.execute(stmt)
    candidates = list(res.scalars().all())

    device_group_ids = {str(g.id) for g in device.groups}
    device_id_str = str(device.id)

    out: list[EmergencyBroadcast] = []
    for e in candidates:
        # filter time window
        if e.starts_at is not None and e.starts_at > now:
            continue
        if e.ends_at is not None and e.ends_at < now:
            continue
        # filter target
        target = e.target or {}
        if target.get("all") is True:
            out.append(e)
            continue
        device_ids = {str(x) for x in (target.get("device_ids") or [])}
        if device_id_str in device_ids:
            out.append(e)
            continue
        group_ids = {str(x) for x in (target.get("group_ids") or [])}
        if device_group_ids & group_ids:
            out.append(e)
            continue
    return out


def _compute_version(payload: dict) -> str:
    """SHA-256 ของ manifest body (ไม่รวม version + server_time) → ใช้บอก player ว่า outdated มั้ย"""
    payload_for_hash = {k: v for k, v in payload.items() if k not in ("version", "server_time")}
    s = json.dumps(payload_for_hash, sort_keys=True, default=str)
    return hashlib.sha256(s.encode()).hexdigest()[:16]


async def build_manifest(db: AsyncSession, device: Device) -> Manifest:
    """สร้าง manifest สำหรับ device นี้"""
    schedules = await _device_schedules(db, device)

    # ใช้ schedule แรกตาม priority (ที่ active ตอนนี้) — Phase ถัดไปจะ stack หลาย schedule
    items: list[ManifestItem] = []
    if schedules:
        # pick the highest-priority active schedule
        top = schedules[0]
        items = await _plan_to_items(db, top.plan_id)

    # load plan names สำหรับ schedule list
    plan_ids = [s.plan_id for s in schedules]
    plan_name_by_id: dict[uuid.UUID, str] = {}
    if plan_ids:
        res = await db.execute(select(Plan.id, Plan.name).where(Plan.id.in_(plan_ids)))
        plan_name_by_id = {pid: name for pid, name in res.all()}

    schedule_payload = [
        ManifestSchedule(
            schedule_id=s.id,
            plan_name=plan_name_by_id.get(s.plan_id, ""),
            start_at=s.start_at,
            end_at=s.end_at,
            repeat_rule=s.repeat_rule,
            daily_window_start=s.daily_window_start,
            daily_window_end=s.daily_window_end,
            priority=s.priority,
        )
        for s in schedules
    ]

    # === Emergency override (Phase 5 manifest integration) ===
    emergencies_raw = await _active_emergencies_for(db, device)
    emergency_payload = [
        ManifestEmergency(
            emergency_id=e.id,
            title=e.title,
            kind=e.kind.value,
            payload=e.payload or {},
            priority=e.priority,
            starts_at=e.starts_at,
            ends_at=e.ends_at,
        )
        for e in emergencies_raw
    ]

    body = {
        "device_id": str(device.id),
        "device_name": device.name,
        "cache_seconds": 60,
        "schedules": [s.model_dump(mode="json") for s in schedule_payload],
        "items": [i.model_dump(mode="json") for i in items],
        "emergencies": [e.model_dump(mode="json") for e in emergency_payload],
    }
    version = _compute_version(body)

    return Manifest(
        version=version,
        device_id=device.id,
        device_name=device.name,
        server_time=datetime.now(timezone.utc),
        cache_seconds=60,
        schedules=schedule_payload,
        items=items,
        emergencies=emergency_payload,
    )
