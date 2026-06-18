"""
Test scheduler evaluation (§23) — pure logic ไม่ต้องพึ่ง DB
ใช้ SimpleNamespace แทน Schedule model เพื่อ test แยกจาก SQLAlchemy
"""
import datetime as dt
from types import SimpleNamespace

import pytest

from app.services import schedule_eval


UTC = dt.timezone.utc


def _sched(**kwargs):
    """สร้าง fake schedule — ใส่ default ครบทุก field ที่ is_active_now ต้องใช้"""
    base = dict(
        id="s1",
        player_group_id="g1",
        priority=100,
        start_at=dt.datetime(2026, 1, 1, 0, 0, tzinfo=UTC),
        end_at=None,
        repeat_rule=None,
        daily_window_start=None,
        daily_window_end=None,
    )
    base.update(kwargs)
    return SimpleNamespace(**base)


# ===== date-range gate =====

def test_before_start_is_inactive():
    sch = _sched(start_at=dt.datetime(2026, 6, 10, tzinfo=UTC))
    now = dt.datetime(2026, 6, 5, 12, 0, tzinfo=UTC)
    assert schedule_eval.is_active_now(sch, now=now) is False


def test_after_end_is_inactive():
    sch = _sched(end_at=dt.datetime(2026, 6, 1, tzinfo=UTC))
    now = dt.datetime(2026, 6, 5, 12, 0, tzinfo=UTC)
    assert schedule_eval.is_active_now(sch, now=now) is False


def test_within_range_no_rules_is_active():
    sch = _sched()
    now = dt.datetime(2026, 6, 5, 12, 0, tzinfo=UTC)
    assert schedule_eval.is_active_now(sch, now=now) is True


# ===== daily time-window (day-parting) =====

def test_inside_daily_window():
    # window 08:00-17:00 ตาม Asia/Bangkok (UTC+7)
    sch = _sched(daily_window_start="08:00", daily_window_end="17:00")
    # 03:00 UTC = 10:00 Bangkok → อยู่ในช่วง
    now = dt.datetime(2026, 6, 5, 3, 0, tzinfo=UTC)
    assert schedule_eval.is_active_now(sch, now=now, device_tz="Asia/Bangkok") is True


def test_outside_daily_window():
    sch = _sched(daily_window_start="08:00", daily_window_end="17:00")
    # 14:00 UTC = 21:00 Bangkok → นอกช่วง
    now = dt.datetime(2026, 6, 5, 14, 0, tzinfo=UTC)
    assert schedule_eval.is_active_now(sch, now=now, device_tz="Asia/Bangkok") is False


def test_overnight_daily_window():
    # window 22:00-06:00 (ข้ามเที่ยงคืน)
    sch = _sched(daily_window_start="22:00", daily_window_end="06:00")
    # 16:00 UTC = 23:00 Bangkok → อยู่ในช่วงกลางคืน
    now_in = dt.datetime(2026, 6, 5, 16, 0, tzinfo=UTC)
    assert schedule_eval.is_active_now(sch, now=now_in, device_tz="Asia/Bangkok") is True
    # 06:00 UTC = 13:00 Bangkok → นอกช่วง
    now_out = dt.datetime(2026, 6, 5, 6, 0, tzinfo=UTC)
    assert schedule_eval.is_active_now(sch, now=now_out, device_tz="Asia/Bangkok") is False


# ===== recurrence (RRULE) =====

def test_rrule_weekday_match():
    # จันทร์-ศุกร์ — 2026-06-05 เป็นวันศุกร์
    sch = _sched(repeat_rule="FREQ=WEEKLY;BYDAY=MO,TU,WE,TH,FR")
    friday = dt.datetime(2026, 6, 5, 5, 0, tzinfo=UTC)  # ศุกร์ (Bangkok 12:00)
    assert schedule_eval.is_active_now(sch, now=friday, device_tz="Asia/Bangkok") is True


def test_rrule_weekday_no_match_on_weekend():
    sch = _sched(repeat_rule="FREQ=WEEKLY;BYDAY=MO,TU,WE,TH,FR")
    sunday = dt.datetime(2026, 6, 7, 5, 0, tzinfo=UTC)  # อาทิตย์
    assert schedule_eval.is_active_now(sch, now=sunday, device_tz="Asia/Bangkok") is False


def test_broken_rrule_fails_open():
    # rule พัง → ไม่ทำให้จอดับ (fail-open) ตราบใดที่เงื่อนไขอื่นผ่าน
    sch = _sched(repeat_rule="THIS_IS_NOT_A_RULE")
    now = dt.datetime(2026, 6, 5, 5, 0, tzinfo=UTC)
    assert schedule_eval.is_active_now(sch, now=now) is True


def test_combined_rrule_and_window():
    # จ-ศ + 08:00-17:00 — ศุกร์ 10:00 Bangkok ผ่านทั้งคู่
    sch = _sched(
        repeat_rule="FREQ=WEEKLY;BYDAY=MO,TU,WE,TH,FR",
        daily_window_start="08:00",
        daily_window_end="17:00",
    )
    now = dt.datetime(2026, 6, 5, 3, 0, tzinfo=UTC)  # ศุกร์ 10:00 Bangkok
    assert schedule_eval.is_active_now(sch, now=now, device_tz="Asia/Bangkok") is True
    # ศุกร์ 21:00 Bangkok → นอก window
    now2 = dt.datetime(2026, 6, 5, 14, 0, tzinfo=UTC)
    assert schedule_eval.is_active_now(sch, now=now2, device_tz="Asia/Bangkok") is False


# ===== filter_active =====

def test_filter_active_keeps_order():
    active = _sched(id="a")
    future = _sched(id="b", start_at=dt.datetime(2099, 1, 1, tzinfo=UTC))
    now = dt.datetime(2026, 6, 5, 12, 0, tzinfo=UTC)
    result = schedule_eval.filter_active([active, future], now=now)
    assert [s.id for s in result] == ["a"]


# ===== conflict detection =====

def test_conflict_same_priority_overlap():
    existing = _sched(id="e1", priority=100,
                      start_at=dt.datetime(2026, 6, 1, tzinfo=UTC),
                      end_at=dt.datetime(2026, 6, 30, tzinfo=UTC))
    new = _sched(id="e2", priority=100,
                 start_at=dt.datetime(2026, 6, 15, tzinfo=UTC),
                 end_at=dt.datetime(2026, 7, 15, tzinfo=UTC))
    conflicts = schedule_eval.find_conflicts(new, [existing])
    assert len(conflicts) == 1


def test_no_conflict_different_priority():
    existing = _sched(id="e1", priority=100)
    new = _sched(id="e2", priority=200)  # priority ต่าง → stack ตัดสินได้ ไม่ชน
    assert schedule_eval.find_conflicts(new, [existing]) == []


def test_no_conflict_different_group():
    existing = _sched(id="e1", player_group_id="gA")
    new = _sched(id="e2", player_group_id="gB")
    assert schedule_eval.find_conflicts(new, [existing]) == []


def test_no_conflict_non_overlapping_ranges():
    existing = _sched(id="e1",
                      start_at=dt.datetime(2026, 6, 1, tzinfo=UTC),
                      end_at=dt.datetime(2026, 6, 10, tzinfo=UTC))
    new = _sched(id="e2",
                 start_at=dt.datetime(2026, 7, 1, tzinfo=UTC),
                 end_at=dt.datetime(2026, 7, 10, tzinfo=UTC))
    assert schedule_eval.find_conflicts(new, [existing]) == []
