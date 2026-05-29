# Signage Admin UI (Next.js 14)

หน้าเว็บจัดการระบบ Digital Signage — เชื่อมกับ FastAPI backend ผ่าน `/api/v1`

## Stack
- **Next.js 14** (App Router) + TypeScript strict
- **Tailwind CSS 3** (no shadcn — ใช้ component เอง [`src/components/ui.tsx`](src/components/ui.tsx))
- **lucide-react** สำหรับ icon
- **localStorage** เก็บ JWT (Phase 7 จะย้ายเป็น httpOnly cookie)

## Setup (ครั้งแรก)

```bash
cd admin-ui
npm install                     # หรือ pnpm install / yarn
cp .env.example .env.local
# แก้ NEXT_PUBLIC_API_URL ตามที่ตั้ง backend ไว้

npm run dev                     # → http://localhost:3000
```

## Scripts

| คำสั่ง | ทำอะไร |
|---|---|
| `npm run dev` | dev server (hot reload) |
| `npm run build` | build production bundle |
| `npm run start` | serve production build |
| `npm run lint` | ESLint |
| `npm run type-check` | tsc --noEmit |

## โครงสร้าง

```
src/
├── app/
│   ├── layout.tsx              ← Root (AuthProvider)
│   ├── globals.css             ← Tailwind + theme vars
│   ├── login/page.tsx          ← Login (public)
│   └── (dashboard)/            ← route group + Sidebar/Topbar (protected)
│       ├── layout.tsx
│       ├── page.tsx            ← Dashboard (stat cards)
│       ├── devices/            ← list + pair code
│       ├── contents/           ← upload + approve workflow
│       ├── schedules/          ← list + approve/pause
│       ├── tv-control/         ← TV command panel
│       ├── emergency/          ← Emergency broadcast
│       ├── audit/              ← Audit log viewer
│       └── users/              ← User management (super_admin only)
├── components/
│   ├── ui.tsx                  ← Button/Card/Input/Modal/Table/...
│   ├── sidebar.tsx
│   └── topbar.tsx
└── lib/
    ├── api.ts                  ← fetch wrapper + auto-refresh
    ├── auth.tsx                ← AuthProvider + useAuth + hasRole
    └── types.ts                ← TypeScript types ตาม backend schemas
```

## Auth flow

1. `/login` → POST `/api/v1/auth/login` → เก็บ access+refresh ใน localStorage
2. ทุก request แนบ `Authorization: Bearer <access>`
3. ถ้า 401 → auto retry หลัง refresh (single-flight protection)
4. ถ้า refresh fail → ล้าง token → redirect `/login`

## RBAC (UI level)
Sidebar item ซ่อนตาม role ผ่าน `hasRole(user, ...)` ใน [`sidebar.tsx`](src/components/sidebar.tsx)
แต่ **backend ยังคงเป็น source of truth** — UI hiding ไม่ใช่ security

| Role | เห็นเมนู |
|---|---|
| super_admin | ทุกอย่าง + Users |
| admin | ทุกอย่าง ยกเว้น Users |
| editor / approver / viewer | Dashboard / Devices / Contents / Schedules |
| operator | + TV Control, Emergency |

## Pass 2 ✅ Done
- [x] Toast notification system (`components/toast.tsx`)
- [x] Player groups CRUD (`/groups`)
- [x] Presentations layout composer — 3 preset layouts (fullscreen / split 70-30 / main+ticker)
- [x] Plans drag-drop ordering (HTML5 drag, no dnd-kit)
- [x] Schedule create wizard — Plan + Group + datetime + RRULE preset + daily window
- [x] Emergency target picker — all / groups / specific devices
- [x] Device detail page (`/devices/[id]`) — telemetry + manifest + member groups
- [x] Replaced `alert()` with toast across all pages

## ที่ยังไม่ทำ (Phase 7)
- [ ] Dark mode + i18n switcher
- [ ] Bulk operations (multi-select)
- [ ] Presentation custom layout (ตอนนี้แค่ preset)
- [ ] Calendar view สำหรับ schedules
- [ ] httpOnly cookie + CSRF (Phase 7 security hardening)

## ไม่ติดตั้ง deps ใน scheduled run
`npm install` ยังไม่ได้รัน — ดู `package.json` แล้ว user รันเอง:
```bash
cd admin-ui && npm install
```
