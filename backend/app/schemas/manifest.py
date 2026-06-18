"""
Pydantic schema สำหรับ Manifest (§35.2)
JSON ที่ player pull/cache แล้วเล่นตามนี้
"""
import uuid
from datetime import datetime

from pydantic import BaseModel


class ManifestZone(BaseModel):
    zone_key: str
    content_id: uuid.UUID
    content_type: str
    content_url: str | None      # presigned URL หรือ external URL
    params: dict = {}


class ManifestItem(BaseModel):
    """1 item ใน playback queue = 1 presentation"""
    presentation_id: uuid.UUID
    presentation_name: str
    layout: dict
    duration_sec: int
    order_index: int
    zones: list[ManifestZone]


class ManifestSchedule(BaseModel):
    """ช่วงเวลาที่ plan นี้ active"""
    schedule_id: uuid.UUID
    plan_name: str
    start_at: datetime
    end_at: datetime | None
    repeat_rule: str | None
    daily_window_start: str | None
    daily_window_end: str | None
    priority: int


class ManifestEmergency(BaseModel):
    """
    Active emergency broadcast ที่ player ต้องเล่นทับ schedule ปกติ
    Phase 5 manifest-integration — priority สูงกว่าทุก schedule (default 1000+)
    """
    emergency_id: uuid.UUID
    title: str
    kind: str                # "text" | "image" | "url"
    payload: dict            # ตาม kind — ดู models/emergency.py
    priority: int
    starts_at: datetime | None
    ends_at: datetime | None


class Manifest(BaseModel):
    version: str                    # checksum / timestamp ของ manifest
    device_id: uuid.UUID
    device_name: str
    server_time: datetime
    cache_seconds: int = 60         # บอก player ให้ poll ใหม่ทุก N วินาที
    schedules: list[ManifestSchedule]
    items: list[ManifestItem]
    # active emergency override — ถ้ามี player ต้องเล่นอันนี้ก่อน (full-screen)
    # list (ไม่ใช่ single) เผื่อมีหลาย emergency ซ้อนกัน — player เลือก priority สูงสุดเอง
    emergencies: list[ManifestEmergency] = []
