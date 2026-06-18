"""
Device + PlayerGroup model
- Device = จอ/player ตัวจริง (1 record ต่อ 1 จอ)
- PlayerGroup = กลุ่มของ device (ใช้ตอน schedule)

ดู PLAN §35.1 (Hierarchy 5-tier)
"""
import enum
import secrets
import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Table,
    Text,
    Uuid,
    func,
)
from sqlalchemy import (
    Enum as SAEnum,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base


class DeviceStatus(str, enum.Enum):
    UNPAIRED = "unpaired"      # สร้างแล้ว แต่ player ยังไม่ pair
    ONLINE = "online"          # heartbeat ปกติ
    OFFLINE = "offline"        # ไม่มี heartbeat > threshold
    ERROR = "error"            # player report error


class DevicePlatform(str, enum.Enum):
    ANDROID_TV = "android_tv"
    ANDROID_TABLET = "android_tablet"
    RPI_KIOSK = "rpi_kiosk"        # Raspberry Pi + Chromium
    WINDOWS_PC = "windows_pc"
    WEB_BROWSER = "web_browser"
    UNKNOWN = "unknown"


# ตาราง M:N — device ↔ player_group
player_group_members = Table(
    "player_group_members",
    Base.metadata,
    Column("player_group_id", Uuid, ForeignKey("player_groups.id", ondelete="CASCADE"), primary_key=True),
    Column("device_id", Uuid, ForeignKey("devices.id", ondelete="CASCADE"), primary_key=True),
)


class PlayerGroup(Base):
    """กลุ่มของจอ — schedule จะผูกกับ group ไม่ใช่ device ตรงๆ (§35.1)"""
    __tablename__ = "player_groups"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String(128), unique=True, nullable=False, index=True)
    description: Mapped[str] = mapped_column(Text, default="", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    devices: Mapped[list["Device"]] = relationship(
        secondary=player_group_members,
        back_populates="groups",
        lazy="selectin",
    )


def _gen_pairing_code() -> str:
    """สุ่ม 6-digit pairing code (เลข + ตัวอักษรพิมพ์ใหญ่)"""
    alphabet = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"  # ตัด 0/O/I/1 ที่อ่านสับสน
    return "".join(secrets.choice(alphabet) for _ in range(6))


class Device(Base):
    """จอประชาสัมพันธ์ 1 ตัว — รวมข้อมูล hardware + status (§35)"""
    __tablename__ = "devices"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True, default=uuid.uuid4)

    # Identity
    name: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    location: Mapped[str] = mapped_column(String(255), default="", nullable=False)

    # Pairing (§13 device pairing)
    pairing_code: Mapped[str | None] = mapped_column(String(16), unique=True, nullable=True, index=True)
    pairing_code_expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    paired_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    # device token แยกจาก user JWT (§26) — เก็บ hash ของ token เพื่อ revoke ได้
    device_token_hash: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # Hardware
    platform: Mapped[DevicePlatform] = mapped_column(
        SAEnum(DevicePlatform, name="device_platform", native_enum=False, length=32),
        default=DevicePlatform.UNKNOWN,
        nullable=False,
    )
    mac_address: Mapped[str | None] = mapped_column(String(17), nullable=True, index=True)
    ip_address: Mapped[str | None] = mapped_column(String(45), nullable=True)
    serial_number: Mapped[str | None] = mapped_column(String(128), nullable=True)
    tv_brand: Mapped[str | None] = mapped_column(String(32), nullable=True)  # samsung/lg/sony/...
    tv_model: Mapped[str | None] = mapped_column(String(128), nullable=True)

    # Status (อัปเดตจาก heartbeat)
    status: Mapped[DeviceStatus] = mapped_column(
        SAEnum(DeviceStatus, name="device_status", native_enum=False, length=32),
        default=DeviceStatus.UNPAIRED,
        nullable=False,
    )
    app_version: Mapped[str | None] = mapped_column(String(32), nullable=True)
    last_heartbeat_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_manifest_version: Mapped[str | None] = mapped_column(String(64), nullable=True)

    # Telemetry — เก็บแค่ค่าล่าสุด (history → time-series table phase ถัดไป)
    cpu_percent: Mapped[float | None] = mapped_column(nullable=True)
    temperature_c: Mapped[float | None] = mapped_column(nullable=True)
    uptime_sec: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # Audit
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    groups: Mapped[list[PlayerGroup]] = relationship(
        secondary=player_group_members,
        back_populates="devices",
        lazy="selectin",
    )

    @staticmethod
    def generate_pairing_code() -> str:
        return _gen_pairing_code()
