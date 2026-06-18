# 🗃️ Data Dictionary (สร้างจาก SQLAlchemy models จริง)

> สร้างอัตโนมัติจาก `Base.metadata` — อัปเดต 2026-06-18 · **12 ตาราง** · ดู [er-diagram.md](er-diagram.md)

> ชนิดแบบ logical (UUID = PG `uuid` / SQLite `char(32)`) · PK/FK/UQ=unique/idx=index


### `audit_logs` — บันทึกการกระทำ (append-only)  (13 คอลัมน์)

| คอลัมน์ | ชนิด | Null | Keys |
|---|---|---|---|
| `id` | UUID | NOT NULL | PK |
| `actor_type` | string(32) | NOT NULL |  |
| `actor_id` | string(64) | — | idx |
| `actor_label` | string(255) | — |  |
| `action` | string(64) | NOT NULL | idx |
| `target_type` | string(32) | — |  |
| `target_id` | string(64) | — | idx |
| `outcome` | string(16) | NOT NULL |  |
| `ip_address` | string(45) | — |  |
| `user_agent` | string(512) | — |  |
| `message` | text | — |  |
| `extra` | json | — |  |
| `created_at` | datetime | NOT NULL | idx |

### `contents` — สื่อดิบ  (22 คอลัมน์)

| คอลัมน์ | ชนิด | Null | Keys |
|---|---|---|---|
| `id` | UUID | NOT NULL | PK |
| `name` | string(255) | NOT NULL | idx |
| `description` | text | NOT NULL |  |
| `type` | string(16) | NOT NULL |  |
| `storage_key` | string(512) | — |  |
| `mime_type` | string(128) | — |  |
| `file_size` | bigint | — |  |
| `sha256` | string(64) | — | idx |
| `width` | int | — |  |
| `height` | int | — |  |
| `duration_sec` | float | — |  |
| `thumbnail_key` | string(512) | — |  |
| `url` | string(2048) | — |  |
| `approval_status` | string(16) | NOT NULL |  |
| `approved_by` | UUID | — | FK→users |
| `approved_at` | datetime | — |  |
| `rejection_reason` | text | — |  |
| `expires_at` | datetime | — |  |
| `created_by` | UUID | NOT NULL | FK→users |
| `is_active` | bool | NOT NULL |  |
| `created_at` | datetime | NOT NULL |  |
| `updated_at` | datetime | NOT NULL |  |

### `devices` — จอ/เครื่องเล่น  (23 คอลัมน์)

| คอลัมน์ | ชนิด | Null | Keys |
|---|---|---|---|
| `id` | UUID | NOT NULL | PK |
| `name` | string(128) | NOT NULL | idx |
| `location` | string(255) | NOT NULL |  |
| `pairing_code` | string(16) | — | UQ |
| `pairing_code_expires_at` | datetime | — |  |
| `paired_at` | datetime | — |  |
| `device_token_hash` | string(255) | — |  |
| `platform` | string(32) | NOT NULL |  |
| `mac_address` | string(17) | — | idx |
| `ip_address` | string(45) | — |  |
| `serial_number` | string(128) | — |  |
| `tv_brand` | string(32) | — |  |
| `tv_model` | string(128) | — |  |
| `status` | string(32) | NOT NULL |  |
| `app_version` | string(32) | — |  |
| `last_heartbeat_at` | datetime | — |  |
| `last_manifest_version` | string(64) | — |  |
| `cpu_percent` | float | — |  |
| `temperature_c` | float | — |  |
| `uptime_sec` | int | — |  |
| `is_active` | bool | NOT NULL |  |
| `created_at` | datetime | NOT NULL |  |
| `updated_at` | datetime | NOT NULL |  |

### `emergency_broadcasts` — ประกาศฉุกเฉิน  (15 คอลัมน์)

| คอลัมน์ | ชนิด | Null | Keys |
|---|---|---|---|
| `id` | UUID | NOT NULL | PK |
| `title` | string(255) | NOT NULL |  |
| `kind` | string(16) | NOT NULL |  |
| `payload` | json | NOT NULL |  |
| `target` | json | NOT NULL |  |
| `status` | string(16) | NOT NULL |  |
| `priority` | int | NOT NULL |  |
| `starts_at` | datetime | — |  |
| `ends_at` | datetime | — |  |
| `requires_ack` | bool | NOT NULL |  |
| `acknowledged_at` | datetime | — |  |
| `created_by` | UUID | NOT NULL |  |
| `notes` | text | — |  |
| `created_at` | datetime | NOT NULL |  |
| `updated_at` | datetime | NOT NULL |  |

### `plan_items` — รายการใน plan  (5 คอลัมน์)

| คอลัมน์ | ชนิด | Null | Keys |
|---|---|---|---|
| `id` | UUID | NOT NULL | PK |
| `plan_id` | UUID | NOT NULL | FK→plans idx |
| `presentation_id` | UUID | NOT NULL | FK→presentations |
| `order_index` | int | NOT NULL |  |
| `duration_sec_override` | int | — |  |

### `plans` — ผังลำดับ presentation  (6 คอลัมน์)

| คอลัมน์ | ชนิด | Null | Keys |
|---|---|---|---|
| `id` | UUID | NOT NULL | PK |
| `name` | string(255) | NOT NULL | UQ |
| `description` | text | NOT NULL |  |
| `created_by` | UUID | NOT NULL | FK→users |
| `created_at` | datetime | NOT NULL |  |
| `updated_at` | datetime | NOT NULL |  |

### `player_group_members` — สมาชิกกลุ่มจอ (M:N)  (2 คอลัมน์)

| คอลัมน์ | ชนิด | Null | Keys |
|---|---|---|---|
| `player_group_id` | UUID | NOT NULL | PK FK→player_groups |
| `device_id` | UUID | NOT NULL | PK FK→devices |

### `player_groups` — กลุ่มจอ  (5 คอลัมน์)

| คอลัมน์ | ชนิด | Null | Keys |
|---|---|---|---|
| `id` | UUID | NOT NULL | PK |
| `name` | string(128) | NOT NULL | UQ |
| `description` | text | NOT NULL |  |
| `created_at` | datetime | NOT NULL |  |
| `updated_at` | datetime | NOT NULL |  |

### `presentation_zones` — โซนใน presentation  (6 คอลัมน์)

| คอลัมน์ | ชนิด | Null | Keys |
|---|---|---|---|
| `id` | UUID | NOT NULL | PK |
| `presentation_id` | UUID | NOT NULL | FK→presentations idx |
| `zone_key` | string(64) | NOT NULL |  |
| `content_id` | UUID | NOT NULL | FK→contents |
| `params_json` | json | NOT NULL |  |
| `order_index` | int | NOT NULL |  |

### `presentations` — เลย์เอาต์ที่ประกอบแล้ว  (8 คอลัมน์)

| คอลัมน์ | ชนิด | Null | Keys |
|---|---|---|---|
| `id` | UUID | NOT NULL | PK |
| `name` | string(255) | NOT NULL | idx |
| `description` | text | NOT NULL |  |
| `layout_json` | json | NOT NULL |  |
| `duration_sec` | int | NOT NULL |  |
| `created_by` | UUID | NOT NULL | FK→users |
| `created_at` | datetime | NOT NULL |  |
| `updated_at` | datetime | NOT NULL |  |

### `schedules` — ตารางเวลาออกอากาศ  (18 คอลัมน์)

| คอลัมน์ | ชนิด | Null | Keys |
|---|---|---|---|
| `id` | UUID | NOT NULL | PK |
| `name` | string(255) | NOT NULL | idx |
| `description` | text | NOT NULL |  |
| `plan_id` | UUID | NOT NULL | FK→plans idx |
| `player_group_id` | UUID | NOT NULL | FK→player_groups idx |
| `start_at` | datetime | NOT NULL | idx |
| `end_at` | datetime | — | idx |
| `repeat_rule` | string(512) | — |  |
| `daily_window_start` | string(8) | — |  |
| `daily_window_end` | string(8) | — |  |
| `priority` | int | NOT NULL | idx |
| `status` | string(32) | NOT NULL | idx |
| `created_by` | UUID | NOT NULL | FK→users |
| `approved_by` | UUID | — | FK→users |
| `approved_at` | datetime | — |  |
| `is_active` | bool | NOT NULL |  |
| `created_at` | datetime | NOT NULL |  |
| `updated_at` | datetime | NOT NULL |  |

### `users` — ผู้ใช้ระบบ + RBAC  (12 คอลัมน์)

| คอลัมน์ | ชนิด | Null | Keys |
|---|---|---|---|
| `id` | UUID | NOT NULL | PK |
| `username` | string(64) | NOT NULL | UQ |
| `email` | string(255) | NOT NULL | UQ |
| `password_hash` | string(255) | NOT NULL |  |
| `full_name` | string(255) | NOT NULL |  |
| `role` | string(32) | NOT NULL |  |
| `is_active` | bool | NOT NULL |  |
| `is_locked` | bool | NOT NULL |  |
| `failed_login_count` | int | NOT NULL |  |
| `created_at` | datetime | NOT NULL |  |
| `updated_at` | datetime | NOT NULL |  |
| `last_login_at` | datetime | — |  |
