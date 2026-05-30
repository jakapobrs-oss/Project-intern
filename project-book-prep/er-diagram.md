# 🗂️ ER Diagram — Digital Signage Management System

> **ที่มา:** สังเคราะห์จาก SQLAlchemy models ใน [`backend/app/models/`](../backend/app/models)
> **อัปเดต:** 2026-05-28 (Session #19 / scheduled run)
> **ครอบคลุม:** ตารางทั้งหมดที่มีในระบบหลัง Phase 0–5 (Auth / Devices / Contents / Presentation / Plan / Schedule / Emergency / Audit)
>
> ใช้ Mermaid `erDiagram` — GitHub / VS Code / Obsidian render ได้ทันที (ไม่ต้องลง plugin)
> **เปิด/แก้ไข/export PNG-SVG ออนไลน์ (ฟรี ไม่ต้องลงอะไร):** คลิกลิงก์ mermaid.live ในแต่ละ diagram ด้านล่าง — ลิงก์ฝัง diagram มาให้พร้อม กดปุ่ม Actions → PNG/SVG ได้เลย
> ลิงก์ถูกสร้างด้วย [`assets/gen_mermaid_links.py`](assets/gen_mermaid_links.py) (pako-encoded เหมือน live editor + ผ่าน round-trip decode test) — รันใหม่ทุกครั้งที่ schema เปลี่ยน

---

## 1) ภาพรวมระบบ (Bird's-eye view)

ระบบมีตารางทั้งหมด **12 ตาราง** = **11 mapped entity tables + 1 association table (M:N)** โดยเป็น **8 entity หลัก** (`users`, `devices`, `player_groups`, `contents`, `presentations`, `plans`, `schedules`, `emergency_broadcasts`) + **3 ตารางลูก/สนับสนุน** (`audit_logs`, `presentation_zones`, `plan_items`) + **1 association** (`player_group_members`) แบ่งเป็น 5 กลุ่ม:

| กลุ่ม | Entities | บทบาท |
|---|---|---|
| 🔐 **Identity & Audit** | `users`, `audit_logs` | ผู้ใช้ระบบ + บันทึก action ทั้งหมด (append-only) |
| 📺 **Devices** | `devices`, `player_groups`, `player_group_members` | จอ + กลุ่มจอ (M:N) |
| 🎞️ **Content & Composition** | `contents`, `presentations`, `presentation_zones` | สื่อ raw + layout 5-tier (§35.1) |
| 📋 **Playlists & Schedules** | `plans`, `plan_items`, `schedules` | sequence ของ presentation + เวลาเล่น |
| 🚨 **Emergency** | `emergency_broadcasts` | override schedule (target เป็น JSON — ไม่มี FK) |

> หมายเหตุ ER diagram: `emergency_broadcasts.created_by` และ `audit_logs.actor_id` ไม่ได้กำหนด FK ฝั่ง DB
> (เก็บเป็น UUID/String เพื่อให้ user ถูกลบได้แต่ log ยังคงอยู่ — pattern audit trail)
> เลยใส่เป็นเส้นประ (logical link) ใน diagram

---

## 2) Mermaid ER Diagram — Full

> 🔗 **เปิดใน mermaid.live (คลิกแล้ว export PNG/SVG ได้):** [mermaid.live — Full ER Diagram](https://mermaid.live/edit#pako:eNq1WNuO2zYQ_RXCQIAEzS7TFu3DAn0ockHSdNMgi7wZIGhxbDGWSJWk7CibfWqBpn3vB_QT-rb5G39Kh5Rk60LXbnfXWKwtXudy5syMLieJFjA5IxMwTyRfGJ5PFcHPvXvkO_8hLwQoJ11VP9aTpQVjyWX9EAZKKQj-vX65G7POSLUIaxXPgbwdz0HOZRabKLi1a20ES7lNR7PzMsuYP3M3A6rMidEZkOnElgUYxkUuFa3_g5BOG8qLwugVGLqSsMYvjeu4nxCwkglMJ7vzZlpnRFrGEydXMB7PdLIEsRuXypE5KgMCpxZSsUSXyu3mBXfgJFohMYA_BeOxybIQ-yczbl1zeDt_NVUDbz0Jmtius0QzdJy7-mZtBlFb7qRWET9J_808iHp-3ErdXcHgfSEN2Lh-fuVA9-aWWgPm9BLUABHB70XG3VybHH3PlTBaCuZWdPuTzzJw1BSSLaW2S7qWSui1ZUVC1zBjM4MPYLreb-7NeYIwEiixHc3JYu8UHiY5ArTMZ3jscNat8EaUzQOV57ZUC5otqNWqoqenpxEpcEOOxssGSlvHXWnxlFLVlqNaZVIB1fN5-AZjdEwrjAKGQWB7_uyjLAVu3AyBGvNGWJFzJeeAP0YnzTPNHUmKkmF0JdANgnrKQR7irjTAkn4ElYWXgVlIDkfi_4uobcQgZipkiYXRZfFfYiPGVgJsYmTh4ha9uXwsBw-lsZi9RUHmh89eDtY0wdOfHRPHY60cOqtLHEk9dCPmiJom4NdVhSdrmfMFICEL0D4aKe4DnlMH710EuxbZGtezJVS49-Jrei7Vi5-QOlwai18PJn9PB01yEagamZpZ-WEssE35V998i4cLEJhHuqf6jWspXNofSkEu0hHKRWkCZfbB3IZ0itygMF14RcYZ02R4_84YXRmC6eo8hhSz5QBh-NzRApTAA9o8J6iBd5AgvLonBA-2K9isIs9itL1dECGA-lSvG0pno5iPEX24uA2Gwb13FeQoAyI4OOL2YfwOdUc2rHTpWPg9nXhuw2QE5AvyQSuwQ_jEUfFvlrlFC7Ag0iEz1MTS3YbPz8Z28oc1cZhzl6RdS4zw1lDJ8KhgtYJj0WlbC650VuZA59KFrDfMid6IWBci6WESh_f72Ow1CpNJi9xFyUWSYihn_aIIvaTuhPbv0pcoM5MIsSN9GJb3DX7QuVH7xtDLfCFtkLYHQtqttW873A4oNUiFUbsjXxoXtzpSZ5zrCl8GmTJ0FvIxz8ibN29_fBrJNgL5vGJ1ccnCTbjj-fOz8_NDiyFUg6Ol3uSFkdr47ms6-fLRIzTMnJeZG2WEeCJgbaKgNa_SgmM3JmjNzuOssAe2N8gYd8Tr2zh_moNZgEoqch8NvgBHNp9_2Vz_sfn8O_nh4qdX-Pjr5vqvzedP7fgnlP5BlwmgPcI3Alwk3B5d8WBbnA170KUMzvT1C61rG0znXUs3nFdhlSAGo40K2MVkGd3WbZa2oLaH_N64ufEvTbhKIMv6nh6jKgqrfszYvUFjx_428HNZZ_9kGQNKslR6jVItBn4fYnA6URq9RU7IEqAgaCD_LgGFxXYOIjGltAN7-xj7vhTSkfuIb1T3BJus6iGpBdtc_7m5_huxtrn-LeDrUw9Z3G_0HfuxeEL3acOawtjr2oCA2soi7WNHi11irksb6-rCXimGVkulr5mrvTsyPgNfblrFC5tqt31fE98hQ5LmpUtPw6sI2mT20yb89_WwAdmDWrw_J8UA21hMJDqvX-gkCTba1L9gQZMo2Uf04Y7c68QwFtWY4HNcjzODSMToNfwIKI3R8gayutxMZWHH78w-fjw50Ze71mr7OUM9d9hv1TtiU4eYo7v6NfCRV9XlUfdzxKZd6r_xpoFS_RdZV7qVsdPB1_vqRpnoObl_fvbqQXtjf-lOx3GH7Q9pd7X31Z9jdsW6jt7mcTXut6bc9tuFsacPnICRu1ZI7R0hRh7s-rYpI7smD1UfIDX5ma3h9qsSP8XAHE_BtCNI13X7pRn7v1aoGcbCw8a9eMQhNbNMJ5OHBJFhci6Ff9N9iTMpeIY7C31-k_uu_DJkNn1RqQSnnCkBR-oE0bwbb4av_gEep2YS)

```mermaid
erDiagram
    %% ===== Identity =====
    users {
        uuid id PK
        string username UK
        string email UK
        string password_hash
        string full_name
        enum role "super_admin/admin/editor/approver/viewer/operator/device"
        bool is_active
        bool is_locked
        int failed_login_count
        datetime created_at
        datetime updated_at
        datetime last_login_at
    }

    %% ===== Devices =====
    devices {
        uuid id PK
        string name
        string location
        string pairing_code UK
        datetime pairing_code_expires_at
        datetime paired_at
        string device_token_hash
        enum platform "android_tv/android_tablet/rpi_kiosk/windows_pc/web_browser"
        string mac_address
        string ip_address
        string serial_number
        string tv_brand "samsung/lg/sony/..."
        string tv_model
        enum status "unpaired/online/offline/error"
        string app_version
        datetime last_heartbeat_at
        string last_manifest_version
        float cpu_percent
        float temperature_c
        int uptime_sec
        bool is_active
        datetime created_at
        datetime updated_at
    }

    player_groups {
        uuid id PK
        string name UK
        string description
        datetime created_at
        datetime updated_at
    }

    player_group_members {
        uuid player_group_id PK,FK
        uuid device_id PK,FK
    }

    %% ===== Content =====
    contents {
        uuid id PK
        string name
        string description
        enum type "image/video/web/stream/text"
        string storage_key "S3/MinIO path"
        string mime_type
        bigint file_size
        string sha256 "dedupe"
        int width
        int height
        float duration_sec
        string thumbnail_key
        string url "web/stream"
        enum approval_status "draft/pending/approved/rejected"
        uuid approved_by FK
        datetime approved_at
        string rejection_reason
        datetime expires_at
        uuid created_by FK
        bool is_active
        datetime created_at
        datetime updated_at
    }

    presentations {
        uuid id PK
        string name
        string description
        json layout_json "template + zones"
        int duration_sec
        uuid created_by FK
        datetime created_at
        datetime updated_at
    }

    presentation_zones {
        uuid id PK
        uuid presentation_id FK
        string zone_key "match layout_json"
        uuid content_id FK
        json params_json "volume/fit_mode/..."
        int order_index
    }

    %% ===== Playlists / Schedules =====
    plans {
        uuid id PK
        string name UK
        string description
        uuid created_by FK
        datetime created_at
        datetime updated_at
    }

    plan_items {
        uuid id PK
        uuid plan_id FK
        uuid presentation_id FK
        int order_index
        int duration_sec_override
    }

    schedules {
        uuid id PK
        string name
        string description
        uuid plan_id FK
        uuid player_group_id FK
        datetime start_at
        datetime end_at
        string repeat_rule "iCal RRULE"
        string daily_window_start "HH:MM"
        string daily_window_end "HH:MM"
        int priority "100 default"
        enum status "draft/pending_approval/active/paused/expired"
        uuid created_by FK
        uuid approved_by FK
        datetime approved_at
        bool is_active
        datetime created_at
        datetime updated_at
    }

    %% ===== Emergency (target ใช้ JSON ไม่ใช่ FK) =====
    emergency_broadcasts {
        uuid id PK
        string title
        enum kind "text/image/url"
        json payload
        json target "all/device_ids/group_ids"
        enum status "draft/active/expired/cancelled"
        int priority "1000 default"
        datetime starts_at
        datetime ends_at
        bool requires_ack
        datetime acknowledged_at
        uuid created_by "no FK - keep on user delete"
        string notes
        datetime created_at
        datetime updated_at
    }

    %% ===== Audit (append-only, no FK ตั้งใจ) =====
    audit_logs {
        uuid id PK
        string actor_type "user/device/system/anonymous"
        string actor_id "no FK - keep history"
        string actor_label "snapshot username"
        string action "auth.login/content.approve/..."
        string target_type
        string target_id
        enum outcome "success/fail/denied"
        string ip_address
        string user_agent
        string message
        json extra
        datetime created_at
    }

    %% ===== Relationships =====
    users ||--o{ contents          : "created_by"
    users ||--o{ contents          : "approved_by"
    users ||--o{ presentations     : "created_by"
    users ||--o{ plans             : "created_by"
    users ||--o{ schedules         : "created_by"
    users ||--o{ schedules         : "approved_by"

    devices }o--o{ player_groups   : "member of (M:N)"
    player_groups ||--o{ player_group_members : ""
    devices       ||--o{ player_group_members : ""

    presentations      ||--o{ presentation_zones : "has zones"
    contents           ||--o{ presentation_zones : "shown in"

    plans              ||--o{ plan_items         : "ordered items"
    presentations      ||--o{ plan_items         : "referenced by"

    plans              ||--o{ schedules          : "scheduled as"
    player_groups      ||--o{ schedules          : "target"
```

---

## 3) Subgraph — Content Composition (5-Tier Hierarchy §35.1)

ระดับเริ่มจาก **content ดิบ → ประกอบเป็น zone → ใส่ใน presentation (layout) → เรียงใน plan → ผูกกับ schedule** เน้นให้ editor reuse content ได้

> 🔗 **เปิดใน mermaid.live:** [mermaid.live — 5-Tier Composition](https://mermaid.live/edit#pako:eNqlVMFqwzAM_RXj0wbrYdcedhq7FMZg9BYIJtZSb7EdZHksS_Pvs5N0WVqvKVQEHEt60XuW4pYXVgJfMw74qESJQmeGBSusITDkWDvso3mvJAvPy2bygfGaUVPD5HKEypRhsShKyD-gOYl5rAZfNyw1ggvVBClr8m9rYLFu75vBwv7pOGFUcRwbWcRCc3rKELMoAXNlJHz9y3GR3ruzhlWisZ7y-D4vIT0OnB0U8xqVCEII9IX6-_SE7nMHk9SYYpbbT0BUEk4oLrIbD9gIDWy7meFdsQPpK7hWYTjcIKFE6-uUwhqVRUV_eisFAalAyJFAygUlQmDkbyDwPfoVetvvVyvbpiZ2zTJ-z1YP7JndIHgHtxlPjc4lXziPnKbkYAlk36eDXY2c2pZE8jvGNaAWSsbLpM047UBDxmOShDfhK8p4F9OEJ_vamCKECD0Ej69jA8brZ3R3P4ZxZPg)

```mermaid
erDiagram
    contents {
        uuid id PK
        enum type
        string storage_key
        string url
    }
    presentation_zones {
        uuid id PK
        uuid presentation_id FK
        uuid content_id FK
        string zone_key
        int order_index
    }
    presentations {
        uuid id PK
        json layout_json
        int duration_sec
    }
    plan_items {
        uuid id PK
        uuid plan_id FK
        uuid presentation_id FK
        int order_index
        int duration_sec_override
    }
    plans {
        uuid id PK
        string name UK
    }
    schedules {
        uuid id PK
        uuid plan_id FK
        uuid player_group_id FK
        int priority
        datetime start_at
        datetime end_at
    }

    contents      ||--o{ presentation_zones : "1 → N (reuse ได้)"
    presentations ||--o{ presentation_zones : "1 → N"
    presentations ||--o{ plan_items         : "1 → N"
    plans         ||--o{ plan_items         : "1 → N"
    plans         ||--o{ schedules          : "1 → N"
```

**Tier mapping (จาก §35.1):**
1. **Tier 1 — Content** (raw asset เดียว ใช้ได้หลายที่)
2. **Tier 2 — Zone** (1 zone = 1 content + params ใน layout)
3. **Tier 3 — Presentation** (layout + zones รวมกัน → 1 หน้าจอที่ compose แล้ว)
4. **Tier 4 — Plan** (sequence ของ presentation พร้อม override duration)
5. **Tier 5 — Schedule** (จับ plan กับ player_group + เวลา + priority)

---

## 4) Subgraph — Devices & Schedule Routing

```mermaid
erDiagram
    devices {
        uuid id PK
        string pairing_code UK
        enum status
        string tv_brand
        datetime last_heartbeat_at
    }
    player_groups {
        uuid id PK
        string name UK
    }
    player_group_members {
        uuid player_group_id PK,FK
        uuid device_id PK,FK
    }
    schedules {
        uuid id PK
        uuid plan_id FK
        uuid player_group_id FK
        int priority
    }

    devices       }o--o{ player_groups : "M:N via player_group_members"
    player_groups ||--o{ schedules     : "1 → N"
```

**ทำไม schedule ผูกกับ `player_group` ไม่ใช่ `device` ตรง ๆ?**
- เปลี่ยน schedule ครั้งเดียวกระทบทั้งกลุ่ม (เช่น "จอชั้น 1 ทั้งหมด")
- เพิ่มจอเข้ากลุ่ม → ได้ schedule อัตโนมัติ ไม่ต้องแก้แต่ละจอ
- ถ้าต้องการ schedule เฉพาะจอ ให้สร้าง group ที่มี 1 device

---

## 5) Subgraph — Identity, Audit & Emergency

```mermaid
erDiagram
    users {
        uuid id PK
        string username UK
        enum role
        bool is_locked
        int failed_login_count
    }
    audit_logs {
        uuid id PK
        string actor_id
        string action
        string target_type
        string target_id
        enum outcome
        datetime created_at
    }
    emergency_broadcasts {
        uuid id PK
        enum kind
        json payload
        json target
        int priority
        enum status
        datetime starts_at
        datetime ends_at
    }

    users }o..o{ audit_logs            : "logical (no FK — append-only)"
    users }o..o{ emergency_broadcasts  : "created_by (no FK — soft history)"
```

> เส้น `..` = logical link (ไม่มี FK constraint จริง) — ตั้งใจเพื่อให้ audit/emergency คงอยู่หาก user ถูกลบ ตาม §31 (PDPA retention)

---

## 6) Index ที่ต้องตรวจสอบ (สำคัญต่อ performance)

| ตาราง | คอลัมน์ | สาเหตุ |
|---|---|---|
| `users` | `username`, `email` | UNIQUE + login lookup |
| `devices` | `pairing_code` | UNIQUE + pair lookup |
| `devices` | `mac_address` | network identification |
| `contents` | `sha256` | dedupe lookup §22 |
| `contents` | `name` | admin list search |
| `schedules` | `start_at`, `end_at`, `priority`, `status` | manifest computation (filter by time + priority sort) |
| `schedules` | `plan_id`, `player_group_id` | join |
| `audit_logs` | `created_at`, `action`, `actor_id`, `target_id` | forensic query |
| `presentation_zones` | `presentation_id` | join load |
| `plan_items` | `plan_id` | join load |

> ทั้งหมดมีกำหนดไว้ใน model แล้ว (ตรวจสอบที่ `index=True` / `unique=True`) — Alembic generate auto

---

## 7) Cascade & Deletion Policy

| Relationship | ON DELETE | เหตุผล |
|---|---|---|
| `player_group_members` → `player_groups` / `devices` | **CASCADE** | join table → ลบได้เมื่อต้น/ปลายหาย |
| `presentation_zones` → `presentations` | **CASCADE** | zones ไม่มีความหมายถ้า presentation หาย |
| `plan_items` → `plans` | **CASCADE** | items ไม่มีความหมายถ้า plan หาย |
| `presentation_zones.content_id` → `contents` | **RESTRICT** (default) | ห้ามลบ content ถ้ายังถูกใช้ |
| `plan_items.presentation_id` → `presentations` | **RESTRICT** (default) | ห้ามลบ presentation ถ้ายังถูก plan ใช้ |
| `schedules.plan_id` / `player_group_id` | **RESTRICT** (default) | ห้ามลบของที่ยัง schedule อยู่ |
| `audit_logs`, `emergency_broadcasts` → `users` | **ไม่มี FK** | append-only — ลบ user แล้ว log ยังอยู่ |

> **Optional (รอ permission):** เปลี่ยนบาง RESTRICT เป็น `SET NULL` หรือ soft-delete pattern (`is_active=False`) — ขึ้นกับ business rule

---

## 8) Schema คงเหลือ (ที่ยังไม่มีใน DB, อยู่ใน PLAN.md)

| ตาราง | สถานะ | Phase ที่จะเพิ่ม |
|---|---|---|
| `device_telemetry_history` (time-series) | ⏸️ Pending | Phase 5 rest (เก็บ heartbeat history) |
| `tv_command_log` | ⏸️ Pending | Phase 4 (ปัจจุบันใช้ Redis queue + audit_log แทน) |
| `content_tags` / `tags` | ⏸️ Optional | Phase 6 (taxonomy) |
| `notification_preferences` | ⏸️ Optional | Phase 5 rest (Line/Telegram per-user) |
| `pdpa_consents` | ⏸️ Optional | Phase 6/7 (§31) |
| `device_logs` (player → server log forwarding) | ⏸️ Optional | Phase 5 rest |

---

## 9) วิธีอัปเดต ER diagram (เมื่อ schema เปลี่ยน)

1. แก้ model ใน `backend/app/models/*.py`
2. รัน `alembic revision --autogenerate -m "..."` → ได้ migration ใหม่
3. อัปเดต block Mermaid ในไฟล์นี้ให้ตรง field ที่เพิ่ม/ลด
4. commit คู่กับ migration (review เห็น diff schema + diagram พร้อมกัน)

---

**ดูเพิ่ม:**
- [PLAN.md §35.1 — 5-Tier Hierarchy](../PLAN.md)
- [docs/architecture.md](architecture.md)
- [backend/app/models/](../backend/app/models)
