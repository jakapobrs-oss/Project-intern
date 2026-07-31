"""
API v1 main router
"""
from fastapi import APIRouter

from app.api.v1.endpoints import auth, users, devices, contents, presentations

api_router = APIRouter()


@api_router.get("/ping", tags=["meta"])
async def ping():
    return {"pong": True}


# Phase 1
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(users.router, prefix="/users", tags=["users"])

# Phase 2
api_router.include_router(devices.router, prefix="/devices", tags=["devices"])
api_router.include_router(devices.group_router, prefix="/groups", tags=["player-groups"])
api_router.include_router(contents.router, prefix="/contents", tags=["contents"])
api_router.include_router(presentations.router, prefix="/presentations", tags=["presentations"])

# Phase 3+ (added next)
from app.api.v1.endpoints import plans, schedules, player, tv_control  # noqa: E402

api_router.include_router(plans.router, prefix="/plans", tags=["plans"])
api_router.include_router(schedules.router, prefix="/schedules", tags=["schedules"])
api_router.include_router(player.router, prefix="/player", tags=["player"])

# Phase 4 — TV Control (admin commands + queue)
api_router.include_router(tv_control.router, prefix="/tv", tags=["tv-control"])

# Phase 5 — Emergency Broadcast + Monitoring + Audit
from app.api.v1.endpoints import emergency, monitoring  # noqa: E402

api_router.include_router(emergency.router, prefix="/emergency", tags=["emergency"])
api_router.include_router(monitoring.router, tags=["monitoring"])

# §28 — Reporting & Analytics
from app.api.v1.endpoints import reports  # noqa: E402

api_router.include_router(reports.router, prefix="/reports", tags=["reports"])

# LED board control (scope บรีฟข้อ 2)
from app.api.v1.endpoints import led  # noqa: E402

api_router.include_router(led.router, prefix="/led", tags=["led"])

# §22 — ส่งไฟล์สื่อให้เครื่องเล่นผ่าน backend (แทนการให้ยิงหา MinIO ตรงๆ)
from app.api.v1.endpoints import media  # noqa: E402

api_router.include_router(media.router, tags=["media"])
