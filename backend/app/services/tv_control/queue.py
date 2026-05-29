"""
TV Command Queue — §24
FIFO ต่อ device (Redis list) + retry on player ack failure

Key format:
- list   tv:queue:{device_id}          → pending commands (LPUSH/RPOP)
- hash   tv:cmd:{cmd_id}               → command body + status
- set    tv:inflight:{device_id}       → commands ส่งให้ player แล้ว แต่ยังไม่ ack
"""
import json
import uuid
from datetime import datetime, timezone
from typing import Any

import redis.asyncio as aioredis

from app.config import settings


_redis: aioredis.Redis | None = None


def get_redis() -> aioredis.Redis:
    """singleton Redis client"""
    global _redis
    if _redis is None:
        _redis = aioredis.from_url(settings.redis_url, decode_responses=True)
    return _redis


def _queue_key(device_id: uuid.UUID) -> str:
    return f"tv:queue:{device_id}"


def _cmd_key(cmd_id: str) -> str:
    return f"tv:cmd:{cmd_id}"


def _inflight_key(device_id: uuid.UUID) -> str:
    return f"tv:inflight:{device_id}"


async def enqueue_command(device_id: uuid.UUID, command: dict[str, Any]) -> str:
    """
    ใส่ command เข้า queue ของ device + บันทึก state
    command body ที่คาดหวัง: {brand, command_type, payload, set_id, raw_bytes_hex}
    คืน cmd_id
    """
    r = get_redis()
    cmd_id = uuid.uuid4().hex
    now = datetime.now(timezone.utc).isoformat()

    record = {
        **command,
        "cmd_id": cmd_id,
        "device_id": str(device_id),
        "status": "pending",
        "created_at": now,
        "attempts": 0,
    }
    await r.hset(_cmd_key(cmd_id), mapping={k: json.dumps(v) if not isinstance(v, str) else v for k, v in record.items()})
    await r.lpush(_queue_key(device_id), cmd_id)
    return cmd_id


async def pop_pending(device_id: uuid.UUID, max_count: int = 5) -> list[dict[str, Any]]:
    """
    Player เรียก → ดึง pending command (สูงสุด N ตัว) ย้ายเข้า inflight
    """
    r = get_redis()
    out: list[dict[str, Any]] = []
    for _ in range(max_count):
        cmd_id = await r.rpop(_queue_key(device_id))
        if cmd_id is None:
            break
        record = await r.hgetall(_cmd_key(cmd_id))
        if not record:
            continue
        # parse JSON-encoded values back
        parsed = {k: _try_json_load(v) for k, v in record.items()}
        parsed["status"] = "inflight"
        parsed["attempts"] = int(parsed.get("attempts", 0)) + 1
        await r.hset(_cmd_key(cmd_id), mapping={
            "status": "inflight",
            "attempts": str(parsed["attempts"]),
        })
        await r.sadd(_inflight_key(device_id), cmd_id)
        out.append(parsed)
    return out


async def ack_command(device_id: uuid.UUID, cmd_id: str, success: bool, error: str | None = None) -> bool:
    """Player report ผลลัพธ์ — ลบจาก inflight + บันทึก status"""
    r = get_redis()
    is_inflight = await r.sismember(_inflight_key(device_id), cmd_id)
    if not is_inflight:
        return False
    await r.srem(_inflight_key(device_id), cmd_id)
    mapping = {
        "status": "success" if success else "failed",
        "completed_at": datetime.now(timezone.utc).isoformat(),
    }
    if error:
        mapping["error"] = error
    await r.hset(_cmd_key(cmd_id), mapping=mapping)
    # ลบหลัง 24 ชม. (เก็บไว้ดู history สั้นๆ)
    await r.expire(_cmd_key(cmd_id), 86400)
    return True


async def get_command_status(cmd_id: str) -> dict[str, Any] | None:
    r = get_redis()
    record = await r.hgetall(_cmd_key(cmd_id))
    if not record:
        return None
    return {k: _try_json_load(v) for k, v in record.items()}


def _try_json_load(v: str) -> Any:
    if not isinstance(v, str):
        return v
    if v and v[0] in "{[\"":
        try:
            return json.loads(v)
        except json.JSONDecodeError:
            return v
    return v
