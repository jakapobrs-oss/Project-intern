"""
Device service — pairing + heartbeat
"""
import hashlib
import secrets
import uuid
from datetime import datetime, timedelta, timezone
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.device import Device, DeviceStatus


PAIRING_CODE_TTL_MINUTES = 15
HEARTBEAT_OFFLINE_THRESHOLD_SEC = 300  # 5 นาทีไม่มี heartbeat = offline


class DeviceServiceError(Exception):
    def __init__(self, code: str, message: str):
        self.code = code
        self.message = message
        super().__init__(message)


# ===== Pairing =====

def issue_pairing_code(device: Device) -> str:
    """ออก pairing code ใหม่ + กำหนด expire"""
    device.pairing_code = Device.generate_pairing_code()
    device.pairing_code_expires_at = datetime.now(timezone.utc) + timedelta(minutes=PAIRING_CODE_TTL_MINUTES)
    return device.pairing_code


async def claim_pairing(
    db: AsyncSession,
    pairing_code: str,
    platform,
    mac_address: str | None,
    serial_number: str | None,
    app_version: str | None,
) -> tuple[Device, str]:
    """
    Player claim pairing code → ออก device_token + เคลียร์ code
    คืน (device, plaintext_token) — เก็บแค่ hash ใน DB
    """
    code = pairing_code.upper().strip()
    res = await db.execute(select(Device).where(Device.pairing_code == code))
    device = res.scalar_one_or_none()
    if device is None:
        raise DeviceServiceError("INVALID_CODE", "pairing code ไม่ถูกต้อง")

    now = datetime.now(timezone.utc)
    if device.pairing_code_expires_at and device.pairing_code_expires_at < now:
        raise DeviceServiceError("CODE_EXPIRED", "pairing code หมดอายุแล้ว")

    # ออก device token (raw + hash)
    token = secrets.token_urlsafe(48)
    token_hash = hashlib.sha256(token.encode()).hexdigest()

    device.device_token_hash = token_hash
    device.pairing_code = None
    device.pairing_code_expires_at = None
    device.paired_at = now
    device.platform = platform
    device.mac_address = mac_address
    device.serial_number = serial_number
    device.app_version = app_version
    device.status = DeviceStatus.ONLINE
    device.last_heartbeat_at = now

    await db.commit()
    await db.refresh(device)
    return device, token


def verify_device_token(device: Device, token: str) -> bool:
    """ตรวจว่า raw token ตรงกับ hash ที่เก็บไว้"""
    if not device.device_token_hash:
        return False
    return hashlib.sha256(token.encode()).hexdigest() == device.device_token_hash


async def find_device_by_token(db: AsyncSession, token: str) -> Device | None:
    """หา device จาก raw token (compare ผ่าน hash)"""
    h = hashlib.sha256(token.encode()).hexdigest()
    res = await db.execute(select(Device).where(Device.device_token_hash == h))
    return res.scalar_one_or_none()


# ===== Heartbeat =====

async def apply_heartbeat(
    db: AsyncSession,
    device: Device,
    *,
    status: DeviceStatus,
    app_version: str | None,
    ip_address: str | None,
    cpu_percent: float | None,
    temperature_c: float | None,
    uptime_sec: int | None,
    current_manifest_version: str | None,
) -> Device:
    """อัปเดต heartbeat จาก player"""
    device.status = status
    device.last_heartbeat_at = datetime.now(timezone.utc)
    if app_version is not None:
        device.app_version = app_version
    if ip_address is not None:
        device.ip_address = ip_address
    if cpu_percent is not None:
        device.cpu_percent = cpu_percent
    if temperature_c is not None:
        device.temperature_c = temperature_c
    if uptime_sec is not None:
        device.uptime_sec = uptime_sec
    if current_manifest_version is not None:
        device.last_manifest_version = current_manifest_version
    await db.commit()
    await db.refresh(device)
    return device
