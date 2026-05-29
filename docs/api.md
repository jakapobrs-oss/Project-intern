# API Reference

API spec เต็มอยู่ที่ Swagger UI: <http://localhost:8000/api/docs>

API contract ลิสต์ครบใน [PLAN.md §13](../PLAN.md) — Phase 1+ จะ implement ทีละกลุ่ม:

| กลุ่ม | Endpoint prefix | Phase |
|---|---|---|
| Auth | `/api/v1/auth` | 1 |
| Users | `/api/v1/users` | 1 |
| Devices | `/api/v1/devices` | 2 |
| Contents | `/api/v1/contents` | 2 |
| Playlists | `/api/v1/playlists` | 3 |
| Schedules | `/api/v1/schedules` | 3 |
| Player (pull) | `/api/v1/player` | 3 |
| Emergency | `/api/v1/emergency` | 5 |
| Ops/Admin | `/api/v1/ops` | 6 |

## Auth pattern
- User: Bearer JWT (access 30 นาที, refresh 7 วัน) — header `Authorization: Bearer <token>`
- Device: Bearer device-token (อายุ 1 ปี, rotate ได้) — แยก secret กับ user JWT
