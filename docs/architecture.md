# Architecture

ดู [PLAN.md](../PLAN.md) §2-§3 + §34-§38 สำหรับ design เต็ม

## High-level
```
┌────────────┐    HTTPS    ┌──────────────┐    SQL    ┌────────────┐
│ Admin UI   │ ─────────▶ │  Backend API │ ───────▶ │ PostgreSQL │
│ (Next.js)  │             │  (FastAPI)   │            └────────────┘
└────────────┘             │              │    Redis   ┌────────────┐
                           │              │ ─────────▶ │   Redis    │
                           └──────┬───────┘            └────────────┘
                                  │                          ▲
                                  │ enqueue                  │
                                  ▼                          │
                           ┌──────────────┐                  │
                           │ Worker (Arq) │ ─────────────────┘
                           └──────┬───────┘
                                  │ S3 API
                                  ▼
                           ┌──────────────┐
                           │ MinIO (media)│
                           └──────────────┘
                                  ▲
                                  │ manifest + media
                                  │
                  ┌───────────────┼───────────────┐
                  │               │               │
            ┌─────▼────┐    ┌─────▼────┐   ┌─────▼────┐
            │ Player 1 │    │ Player 2 │   │ Player N │
            │ Android  │    │ RPi PWA  │   │   ...    │
            └─────┬────┘    └──────────┘   └──────────┘
                  │ HDMI-CEC / RS-232
                  ▼
              ┌───────┐
              │  TV   │
              └───────┘
```

## Key patterns
- **Pre-computed manifest** (§35.2) — Backend สร้าง JSON ต่อ player → push หรือให้ player pull → player cache local → render
- **Hierarchy 5 ชั้น** (§35.1): Content → Presentation → Plan → PlayerGroup → Player
- **Device JWT แยกจาก User JWT** (§26) — token ต่างชุด, expire ต่างกัน
- **Worker decomposition** (§37) — รวม background jobs ไว้ใน Arq worker เดียว
