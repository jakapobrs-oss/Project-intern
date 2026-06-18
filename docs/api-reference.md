# 📡 API Reference (สร้างจาก OpenAPI จริง)

> สร้างอัตโนมัติจาก `app.openapi()` — อัปเดต 2026-06-18 · รวม **63 endpoints** · ดู interactive ที่ `/api/docs`

> 🔒 = ต้องมี Bearer JWT (user) หรือ device token · — = ไม่ต้อง auth


## สารบัญ

- [Auth — เข้าสู่ระบบ](#auth) (5)
- [Users — จัดการผู้ใช้](#users) (5)
- [Devices — อุปกรณ์/จอ](#devices) (6)
- [Player Groups — กลุ่มจอ](#player-groups) (4)
- [Contents — สื่อ](#contents) (8)
- [Presentations — เลย์เอาต์](#presentations) (5)
- [Plans — ผังการเล่น](#plans) (5)
- [Schedules — ตารางเวลา](#schedules) (7)
- [Player — เครื่องเล่น (pull)](#player) (6)
- [TV Control — ควบคุมทีวี](#tv-control) (2)
- [Emergency — ประกาศฉุกเฉิน](#emergency) (6)
- [Monitoring — เฝ้าระวัง](#monitoring) (1)
- [Meta — health/ราก](#meta) (3)


<a id='auth'></a>
### Auth — เข้าสู่ระบบ

| Method | Path | Auth | สรุป |
|---|---|---|---|
| `GET` | `/api/v1/auth/csrf` | — public | Get Csrf Token |
| `POST` | `/api/v1/auth/login` | — public | Login |
| `POST` | `/api/v1/auth/logout` | 🔒 login | Logout |
| `GET` | `/api/v1/auth/me` | 🔒 login | Me |
| `POST` | `/api/v1/auth/refresh` | — public | Refresh |

<a id='users'></a>
### Users — จัดการผู้ใช้

| Method | Path | Auth | สรุป |
|---|---|---|---|
| `GET` | `/api/v1/users` | 🔒 login | List Users |
| `POST` | `/api/v1/users` | 🔒 login | Create User |
| `DELETE` | `/api/v1/users/{user_id}` | 🔒 login | Delete User |
| `GET` | `/api/v1/users/{user_id}` | 🔒 login | Get User |
| `PATCH` | `/api/v1/users/{user_id}` | 🔒 login | Update User |

<a id='devices'></a>
### Devices — อุปกรณ์/จอ

| Method | Path | Auth | สรุป |
|---|---|---|---|
| `GET` | `/api/v1/devices` | 🔒 login | List Devices |
| `POST` | `/api/v1/devices` | 🔒 login | Create Device |
| `DELETE` | `/api/v1/devices/{device_id}` | 🔒 login | Delete Device |
| `GET` | `/api/v1/devices/{device_id}` | 🔒 login | Get Device |
| `PATCH` | `/api/v1/devices/{device_id}` | 🔒 login | Update Device |
| `POST` | `/api/v1/devices/{device_id}/regenerate-pairing` | 🔒 login | Regenerate Pairing |

<a id='player-groups'></a>
### Player Groups — กลุ่มจอ

| Method | Path | Auth | สรุป |
|---|---|---|---|
| `GET` | `/api/v1/groups` | 🔒 login | List Groups |
| `POST` | `/api/v1/groups` | 🔒 login | Create Group |
| `DELETE` | `/api/v1/groups/{group_id}` | 🔒 login | Delete Group |
| `PATCH` | `/api/v1/groups/{group_id}` | 🔒 login | Update Group |

<a id='contents'></a>
### Contents — สื่อ

| Method | Path | Auth | สรุป |
|---|---|---|---|
| `GET` | `/api/v1/contents` | 🔒 login | List Contents |
| `POST` | `/api/v1/contents/upload` | 🔒 login | Upload Content |
| `POST` | `/api/v1/contents/url` | 🔒 login | Create Url Content |
| `DELETE` | `/api/v1/contents/{content_id}` | 🔒 login | Delete Content |
| `GET` | `/api/v1/contents/{content_id}` | 🔒 login | Get Content |
| `PATCH` | `/api/v1/contents/{content_id}` | 🔒 login | Update Content |
| `POST` | `/api/v1/contents/{content_id}/approve` | 🔒 login | Approve Content |
| `POST` | `/api/v1/contents/{content_id}/submit` | 🔒 login | Submit For Approval |

<a id='presentations'></a>
### Presentations — เลย์เอาต์

| Method | Path | Auth | สรุป |
|---|---|---|---|
| `GET` | `/api/v1/presentations` | 🔒 login | List Presentations |
| `POST` | `/api/v1/presentations` | 🔒 login | Create Presentation |
| `DELETE` | `/api/v1/presentations/{presentation_id}` | 🔒 login | Delete Presentation |
| `GET` | `/api/v1/presentations/{presentation_id}` | 🔒 login | Get Presentation |
| `PATCH` | `/api/v1/presentations/{presentation_id}` | 🔒 login | Update Presentation |

<a id='plans'></a>
### Plans — ผังการเล่น

| Method | Path | Auth | สรุป |
|---|---|---|---|
| `GET` | `/api/v1/plans` | 🔒 login | List Plans |
| `POST` | `/api/v1/plans` | 🔒 login | Create Plan |
| `DELETE` | `/api/v1/plans/{plan_id}` | 🔒 login | Delete Plan |
| `GET` | `/api/v1/plans/{plan_id}` | 🔒 login | Get Plan |
| `PATCH` | `/api/v1/plans/{plan_id}` | 🔒 login | Update Plan |

<a id='schedules'></a>
### Schedules — ตารางเวลา

| Method | Path | Auth | สรุป |
|---|---|---|---|
| `GET` | `/api/v1/schedules` | 🔒 login | List Schedules |
| `POST` | `/api/v1/schedules` | 🔒 login | Create Schedule |
| `DELETE` | `/api/v1/schedules/{schedule_id}` | 🔒 login | Delete Schedule |
| `GET` | `/api/v1/schedules/{schedule_id}` | 🔒 login | Get Schedule |
| `PATCH` | `/api/v1/schedules/{schedule_id}` | 🔒 login | Update Schedule |
| `POST` | `/api/v1/schedules/{schedule_id}/approve` | 🔒 login | Approve Schedule |
| `POST` | `/api/v1/schedules/{schedule_id}/pause` | 🔒 login | Pause Schedule |

<a id='player'></a>
### Player — เครื่องเล่น (pull)

| Method | Path | Auth | สรุป |
|---|---|---|---|
| `GET` | `/api/v1/player/commands` | — public | Player Pull Commands |
| `POST` | `/api/v1/player/commands/{cmd_id}/ack` | — public | Player Ack Command |
| `POST` | `/api/v1/player/heartbeat` | — public | Heartbeat |
| `GET` | `/api/v1/player/manifest` | — public | Get Manifest |
| `GET` | `/api/v1/player/me` | — public | Player Me |
| `POST` | `/api/v1/player/pair` | — public | Pair |

<a id='tv-control'></a>
### TV Control — ควบคุมทีวี

| Method | Path | Auth | สรุป |
|---|---|---|---|
| `GET` | `/api/v1/tv/commands/{cmd_id}/status` | 🔒 login | Command Status |
| `POST` | `/api/v1/tv/devices/{device_id}/commands` | 🔒 login | Send Command |

<a id='emergency'></a>
### Emergency — ประกาศฉุกเฉิน

| Method | Path | Auth | สรุป |
|---|---|---|---|
| `GET` | `/api/v1/emergency/` | 🔒 login | List Broadcasts |
| `POST` | `/api/v1/emergency/` | 🔒 login | Create Broadcast |
| `GET` | `/api/v1/emergency/{bid}` | 🔒 login | Get Broadcast |
| `PATCH` | `/api/v1/emergency/{bid}` | 🔒 login | Update Broadcast |
| `POST` | `/api/v1/emergency/{bid}/activate` | 🔒 login | Activate Broadcast |
| `POST` | `/api/v1/emergency/{bid}/cancel` | 🔒 login | Cancel Broadcast |

<a id='monitoring'></a>
### Monitoring — เฝ้าระวัง

| Method | Path | Auth | สรุป |
|---|---|---|---|
| `GET` | `/api/v1/audit/logs` | 🔒 login | List Audit Logs |

<a id='meta'></a>
### Meta — health/ราก

| Method | Path | Auth | สรุป |
|---|---|---|---|
| `GET` | `/` | — public | Root |
| `GET` | `/api/v1/ping` | — public | Ping |
| `GET` | `/healthz` | — public | Healthz |
