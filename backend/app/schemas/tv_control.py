"""Pydantic schemas — TV control"""
import uuid
from pydantic import BaseModel, Field

from app.services.tv_control.base import TVBrand, TVCommandType


class TVCommandRequest(BaseModel):
    """admin ส่งสั่งให้ device 1 ตัว"""
    command_type: TVCommandType
    payload: dict | None = None
    set_id: int = Field(0, ge=0, le=99)
    # ถ้า device.tv_brand เป็น null และ admin ต้อง override
    brand_override: TVBrand | None = None


class TVCommandResponse(BaseModel):
    cmd_id: str
    device_id: uuid.UUID
    enqueued: bool = True


class TVCommandAck(BaseModel):
    """Player ack ผลลัพธ์"""
    success: bool
    error: str | None = None


class TVCommandInQueue(BaseModel):
    """รูปแบบที่ player เห็นเมื่อ pull queue"""
    cmd_id: str
    brand: str
    command_type: str
    raw_bytes_hex: str
    payload: dict | None = None
    set_id: int = 0
    attempts: int = 1


class TVCommandStatus(BaseModel):
    cmd_id: str
    device_id: uuid.UUID
    status: str
    attempts: int
    error: str | None = None
