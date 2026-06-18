"""Pydantic schemas — device + player group"""
import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.device import DevicePlatform, DeviceStatus

# ===== Device =====

class DeviceBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=128)
    location: str = Field("", max_length=255)
    platform: DevicePlatform = DevicePlatform.UNKNOWN
    tv_brand: str | None = Field(None, max_length=32)
    tv_model: str | None = Field(None, max_length=128)


class DeviceCreate(DeviceBase):
    """สร้าง device แบบ manual (admin) — จะได้ pairing_code กลับ"""


class DeviceUpdate(BaseModel):
    name: str | None = Field(None, max_length=128)
    location: str | None = Field(None, max_length=255)
    tv_brand: str | None = None
    tv_model: str | None = None
    is_active: bool | None = None


class DeviceOut(DeviceBase):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    status: DeviceStatus
    pairing_code: str | None
    pairing_code_expires_at: datetime | None
    paired_at: datetime | None
    mac_address: str | None
    ip_address: str | None
    serial_number: str | None
    app_version: str | None
    last_heartbeat_at: datetime | None
    last_manifest_version: str | None
    cpu_percent: float | None
    temperature_c: float | None
    uptime_sec: int | None
    is_active: bool
    created_at: datetime
    updated_at: datetime


# ===== Pairing (§13) =====

class PairingClaimRequest(BaseModel):
    """player ส่งมาเพื่อ claim pairing code"""
    pairing_code: str = Field(..., min_length=4, max_length=16)
    platform: DevicePlatform = DevicePlatform.UNKNOWN
    mac_address: str | None = Field(None, max_length=17)
    serial_number: str | None = Field(None, max_length=128)
    app_version: str | None = Field(None, max_length=32)


class PairingClaimResponse(BaseModel):
    """response หลัง pair สำเร็จ — มี device_token"""
    device_id: uuid.UUID
    device_token: str
    server_time: datetime


# ===== Heartbeat (player → backend, §35) =====

class HeartbeatRequest(BaseModel):
    status: DeviceStatus = DeviceStatus.ONLINE
    app_version: str | None = None
    ip_address: str | None = None
    cpu_percent: float | None = None
    temperature_c: float | None = None
    uptime_sec: int | None = None
    current_manifest_version: str | None = None


class HeartbeatResponse(BaseModel):
    """response บอก player ว่าต้องอัปเดต manifest มั้ย"""
    server_time: datetime
    manifest_outdated: bool
    latest_manifest_version: str | None


# ===== PlayerGroup =====

class PlayerGroupBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=128)
    description: str = ""


class PlayerGroupCreate(PlayerGroupBase):
    device_ids: list[uuid.UUID] = []


class PlayerGroupUpdate(BaseModel):
    name: str | None = Field(None, max_length=128)
    description: str | None = None
    device_ids: list[uuid.UUID] | None = None


class PlayerGroupOut(PlayerGroupBase):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    device_ids: list[uuid.UUID] = []
    created_at: datetime
    updated_at: datetime
