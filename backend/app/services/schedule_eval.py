"""
Schedule evaluation (§23) — ตัดสินว่า schedule "active ตอนนี้จริงไหม"

เดิม manifest เลือก schedule แค่ status=ACTIVE + ยังไม่หมดอายุ + priority
ทำให้ schedule แบบ "เล่นเฉพาะ จ-ศ 8:00-17:00" ไม่ทำงานตามนั้น

ไฟล์นี้รวม 3 เงื่อนไขที่ production signage ต้องมี:
  1. date-range gate — now ต้องอยู่ในช่วง [start_at, end_at]
  2. recurrence (RRULE iCal) — "วันนี้" ต้องตรงกับ rule (เช่น FREQ=WEEKLY;BYDAY=MO,TU,...)
  3. daily time-window (day-parting) — เวลาในวัน ต้องอยู่ใน [daily_window_start, daily_window_end]

ทุกเงื่อนไขคำนวณตาม timezone ของ device (fallback = settings.app_timezone)
ออกแบบ fail-open: ถ้า rule พัง/ไม่มี dateutil → ถือว่า active (กันจอดับเพราะ config ผิด)
"""
from __future__ import annotations

import datetime as dt
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

try:
    # dateutil ใช้ parse RRULE — ถ้าไม่มีจะ fail-open (ดู _matches_recurrence)
    from dateutil.rrule import rrulestr
except Exception:  # pragma: no cover — dateutil เป็น optional ตอน import
    rrulestr = None  # type: ignore[assignment]

from app.config import settings


def _tz(device_tz: str | None) -> dt.tzinfo:
    """
    หา timezone ของ device — fallback ไป app_timezone แล้ว UTC
    ใช้ stdlib timezone.utc เป็น fallback สุดท้าย (ZoneInfo อาจพังถ้าไม่มี tzdata)
    """
    name = device_tz or settings.app_timezone or "UTC"
    try:
        return ZoneInfo(name)
    except (ZoneInfoNotFoundError, ValueError, OSError):
        return dt.timezone.utc


def _ensure_aware(value: dt.datetime | None) -> dt.datetime | None:
    """ทำให้ datetime เป็น timezone-aware (สมมติ UTC ถ้า naive — DB เก็บ UTC)"""
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=dt.timezone.utc)
    return value


def _parse_hhmm(value: str | None) -> dt.time | None:
    """parse 'HH:MM' หรือ 'HH:MM:SS' → time (คืน None ถ้า parse ไม่ได้)"""
    if not value:
        return None
    parts = value.strip().split(":")
    try:
        hour = int(parts[0])
        minute = int(parts[1]) if len(parts) > 1 else 0
        second = int(parts[2]) if len(parts) > 2 else 0
        if not (0 <= hour <= 23 and 0 <= minute <= 59 and 0 <= second <= 59):
            return None
        return dt.time(hour=hour, minute=minute, second=second)
    except (ValueError, IndexError):
        return None


def _in_daily_window(local_now: dt.datetime, start: dt.time | None, end: dt.time | None) -> bool:
    """
    เช็คว่าเวลาในวัน (ของ local_now) อยู่ในช่วง window ไหม
    รองรับ window ข้ามเที่ยงคืน (เช่น 22:00-06:00)
    """
    if start is None and end is None:
        return True
    now_t = local_now.time().replace(tzinfo=None)
    s = start or dt.time(0, 0, 0)
    e = end or dt.time(23, 59, 59)
    if s <= e:
        # window ปกติในวันเดียว
        return s <= now_t <= e
    # window ข้ามเที่ยงคืน: active ถ้าหลัง start หรือ ก่อน end
    return now_t >= s or now_t <= e


def _matches_recurrence(
    repeat_rule: str | None,
    anchor: dt.datetime,
    local_now: dt.datetime,
    tz: ZoneInfo,
) -> bool:
    """
    เช็คว่า "วันนี้" (ตาม local_now) มี occurrence ของ RRULE ไหม
    ประเมินที่ระดับวัน — daily_window จัดการชั่วโมงแยกต่างหาก
    """
    if not repeat_rule:
        return True
    if rrulestr is None:
        return True  # ไม่มี dateutil → fail-open

    # dtstart ต้องเป็น local naive (dateutil ทำงานกับ naive ได้เสถียรสุด)
    dtstart_local = anchor.astimezone(tz).replace(tzinfo=None)
    try:
        rule = rrulestr(repeat_rule, dtstart=dtstart_local)
    except (ValueError, TypeError):
        return True  # rule string พัง → fail-open

    day_start = local_now.replace(hour=0, minute=0, second=0, microsecond=0, tzinfo=None)
    day_end = day_start + dt.timedelta(days=1) - dt.timedelta(microseconds=1)
    try:
        occurrences = rule.between(day_start, day_end, inc=True)
    except (ValueError, TypeError):
        return True
    return len(occurrences) > 0


def is_active_now(
    schedule,
    now: dt.datetime | None = None,
    device_tz: str | None = None,
) -> bool:
    """
    schedule active ตอนนี้จริงไหม — รวม 3 เงื่อนไข
    `schedule` ต้องมี attribute: start_at, end_at, repeat_rule,
                                 daily_window_start, daily_window_end
    """
    now = _ensure_aware(now) or dt.datetime.now(dt.timezone.utc)

    # 1) date-range gate
    start_at = _ensure_aware(getattr(schedule, "start_at", None))
    if start_at is not None and now < start_at:
        return False
    end_at = _ensure_aware(getattr(schedule, "end_at", None))
    if end_at is not None and now > end_at:
        return False

    tz = _tz(device_tz)
    local_now = now.astimezone(tz)

    # 2) recurrence (RRULE รายวัน)
    anchor = start_at or now
    if not _matches_recurrence(getattr(schedule, "repeat_rule", None), anchor, local_now, tz):
        return False

    # 3) daily time-window (day-parting)
    if not _in_daily_window(
        local_now,
        _parse_hhmm(getattr(schedule, "daily_window_start", None)),
        _parse_hhmm(getattr(schedule, "daily_window_end", None)),
    ):
        return False

    return True


def filter_active(schedules, now: dt.datetime | None = None, device_tz: str | None = None) -> list:
    """คืนเฉพาะ schedule ที่ active ตอนนี้ (รักษาลำดับเดิม)"""
    return [s for s in schedules if is_active_now(s, now=now, device_tz=device_tz)]


def _ranges_overlap(
    a_start: dt.datetime,
    a_end: dt.datetime | None,
    b_start: dt.datetime,
    b_end: dt.datetime | None,
) -> bool:
    """
    ช่วงเวลา 2 อันซ้อนกันไหม (end=None = open-ended ไม่มีวันจบ)
    overlap เมื่อ a_start <= b_end และ b_start <= a_end
    """
    a_start = _ensure_aware(a_start)
    a_end = _ensure_aware(a_end)
    b_start = _ensure_aware(b_start)
    b_end = _ensure_aware(b_end)
    a_before_b_end = (b_end is None) or (a_start <= b_end)
    b_before_a_end = (a_end is None) or (b_start <= a_end)
    return a_before_b_end and b_before_a_end


def find_conflicts(new_schedule, existing_schedules) -> list:
    """
    หา schedule ที่ "ชนกัน" กับอันใหม่ (§23 conflict resolution)
    เงื่อนไขชน: group เดียวกัน + ช่วงวันที่ซ้อนกัน + priority เท่ากัน
      → priority เท่ากัน = ระบบเลือกไม่ได้ว่าใครเล่น (ambiguous)
    priority ต่างกันไม่นับว่าชน เพราะ priority stack ตัดสินได้
    """
    conflicts = []
    for s in existing_schedules:
        if getattr(s, "id", None) is not None and s.id == getattr(new_schedule, "id", None):
            continue  # ตัวเดียวกัน (กรณี update)
        if s.player_group_id != new_schedule.player_group_id:
            continue
        if s.priority != new_schedule.priority:
            continue
        if _ranges_overlap(new_schedule.start_at, new_schedule.end_at, s.start_at, s.end_at):
            conflicts.append(s)
    return conflicts
