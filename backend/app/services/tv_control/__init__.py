"""
TV Control — protocol command builders + command queue
ดู §17 + §24 ใน PLAN.md

Protocol builders เป็น "pure function" — รับ payload คืน bytes
ไม่แตะ hardware ตรงนี้ (hardware execution อยู่บน player ที่ connect HDMI/RS-232 จริง)

Architecture:
    admin → POST /api/v1/devices/{id}/commands  → enqueue (Redis)
    player → GET  /api/v1/player/commands       → pull
    player → POST /api/v1/player/commands/{id}/ack
"""
from app.services.tv_control.base import (  # noqa: F401
    TVCommand, TVCommandType, TVBrand, build_command,
)

__all__ = ["TVCommand", "TVCommandType", "TVBrand", "build_command"]
