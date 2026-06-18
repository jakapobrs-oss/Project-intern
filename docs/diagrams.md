# 📊 Diagrams — Use-case & Sequence (สำหรับใส่เล่ม)

> Mermaid ทั้งหมด render ได้บน GitHub / VS Code / Obsidian — หากต้องการรูป PNG ใส่เล่ม ให้คัดลอกบล็อกไปวางที่ <https://mermaid.live> แล้ว export
> เสริมจาก [architecture.md](architecture.md) (สถาปัตยกรรม) และ [er-diagram.md](er-diagram.md) (ฐานข้อมูล)

---

## 1) Use-case Diagram (ภาพรวมผู้ใช้ ↔ ฟังก์ชัน)

แสดงว่าแต่ละบทบาท (RBAC 7 roles) ทำอะไรได้บ้าง

```mermaid
flowchart LR
    SA(["👑 Super Admin"])
    AD(["🛠️ Admin"])
    ED(["✏️ Editor"])
    AP(["✅ Approver"])
    OP(["🚨 Operator"])
    VW(["👁️ Viewer"])
    DV(["📺 Device/Player"])

    subgraph UC["ฟังก์ชันระบบ"]
        u1([จัดการผู้ใช้/สิทธิ์])
        u2([อัปโหลดสื่อ])
        u3([อนุมัติ/ปฏิเสธสื่อ+ตาราง])
        u4([จัด Presentation/Plan])
        u5([ตั้ง Schedule])
        u6([จับคู่/จัดการจอ])
        u7([ควบคุมทีวี CEC/RS-232])
        u8([ประกาศฉุกเฉิน])
        u9([ดูรายงาน/Audit])
        u10([ดึง Manifest + รายงาน Heartbeat])
    end

    SA --- u1
    SA --- u3
    AD --- u4
    AD --- u6
    AD --- u7
    ED --- u2
    ED --- u4
    ED --- u5
    AP --- u3
    OP --- u8
    OP --- u7
    VW --- u9
    DV --- u10
```

---

## 2) Sequence — Login + JWT (§26)

```mermaid
sequenceDiagram
    actor U as ผู้ใช้ (Admin UI)
    participant API as Backend (FastAPI)
    participant AS as auth_service
    participant DB as PostgreSQL
    participant AU as audit_service

    U->>API: POST /api/v1/auth/login (username, password)
    API->>AS: authenticate(username, password)
    AS->>DB: SELECT user WHERE username/email
    DB-->>AS: user
    alt password ผิด
        AS->>DB: failed_login_count += 1 (lock ถ้าเกิน 5)
        AS-->>API: AuthError(INVALID_CREDENTIALS)
        API->>AU: log auth.login (FAIL)
        API-->>U: 401 Unauthorized
    else สำเร็จ
        AS-->>API: user
        API->>API: ออก access (30 นาที) + refresh (7 วัน)
        API->>AU: log auth.login (SUCCESS)
        API-->>U: 200 + TokenPair (+ set httpOnly cookies)
    end
```

---

## 3) Sequence — อัปโหลด → อนุมัติสื่อ (§21–§22)

```mermaid
sequenceDiagram
    actor ED as Editor
    actor AP as Approver
    participant API as Backend
    participant CS as content_service
    participant S3 as MinIO (S3)
    participant DB as PostgreSQL

    ED->>API: POST /contents/upload (multipart file)
    API->>CS: upload_content_file()
    CS->>CS: ตรวจ magic bytes + คำนวณ SHA-256 (dedupe)
    CS->>S3: put object (ถ้ายังไม่ซ้ำ)
    CS->>DB: INSERT content (status=draft)
    API-->>ED: 201 Content
    ED->>API: POST /contents/{id}/submit
    API->>DB: status → pending
    AP->>API: POST /contents/{id}/approve (approve/reject)
    API->>DB: status → approved/rejected + approved_by
    API-->>AP: 200 Content
```

---

## 4) Sequence — จับคู่จอ + ดึง Manifest (§35.2)

```mermaid
sequenceDiagram
    actor AD as Admin
    participant P as Player (Android/PWA)
    participant API as Backend
    participant MS as manifest_service
    participant DB as PostgreSQL

    AD->>API: POST /devices (สร้างจอ → ได้ pairing_code)
    P->>API: POST /player/pair (pairing_code)
    API->>DB: ตรวจ code + ออก device_token (เก็บ hash)
    API-->>P: device_token (อายุ 1 ปี)
    loop ทุกช่วงเวลา (polling)
        P->>API: POST /player/heartbeat (Bearer device_token)
        API->>DB: อัปเดต status/telemetry
        API-->>P: manifest_outdated? + latest_version
        opt manifest เปลี่ยน
            P->>API: GET /player/manifest
            API->>MS: build_manifest(device)
            MS->>DB: รวม schedule→plan→presentation→content (priority+เวลา)
            API-->>P: Manifest JSON (cache local → render)
        end
    end
```

---

## 5) Sequence — ควบคุมทีวีผ่าน Queue (§24)

```mermaid
sequenceDiagram
    actor OP as Operator/Admin
    participant API as Backend
    participant Q as Redis Queue
    participant P as Player
    participant TV as ทีวี (CEC/RS-232)

    OP->>API: POST /tv-control/{device_id} (เช่น power_off)
    API->>API: build_command() → raw bytes ตาม brand
    API->>Q: enqueue command (per device)
    API-->>OP: 202 cmd_id
    loop player polling
        P->>API: GET /player/commands (Bearer device_token)
        API->>Q: pop pending
        API-->>P: รายการคำสั่ง (raw_bytes_hex)
        P->>TV: ส่งผ่าน HDMI-CEC / USB-Serial
        P->>API: POST /player/commands/{cmd_id}/ack (success/error)
        API->>Q: mark acked + audit
    end
```

---

## 6) Sequence — ประกาศฉุกเฉิน (§8.5)

```mermaid
sequenceDiagram
    actor OP as Operator
    participant API as Backend
    participant DB as PostgreSQL
    participant W as Worker (Arq)
    participant P as Player

    OP->>API: POST /emergency (title, payload, target, priority)
    API->>DB: INSERT broadcast (status=active, priority=1000)
    API-->>OP: 201 Emergency
    Note over P,API: Player ดึง manifest ครั้งถัดไป → เห็น broadcast แทรกทับ (priority สูงสุด)
    P->>API: GET /player/manifest
    API-->>P: manifest + emergency overlay
    W->>DB: expire_emergencies() — auto หมดอายุเมื่อเลย ends_at
```

---

**ดูเพิ่ม:** [report-guide.md](report-guide.md) (ข้อมูลทำเล่ม) · [api-reference.md](api-reference.md) · [data-dictionary.md](data-dictionary.md)
