#!/usr/bin/env bash
# ============================================================================
# run-e2e.sh — One-command integration test (Option E)
#
# Flow:
#   1. ตรวจ docker + .env
#   2. docker compose up -d --build
#   3. รอ backend healthy
#   4. pytest ใน backend container
#   5. smoke_e2e.py (HTTP flow ครอบ Phase 0-6)
#   6. รายงาน + ปล่อย stack ไว้ให้ user เปิด admin-ui
#
# รัน:
#   bash scripts/run-e2e.sh [--down]
#
#   --down → หยุด stack หลังเสร็จ (ปกติปล่อยไว้ให้ user เข้า UI)
# ============================================================================
set -euo pipefail
cd "$(dirname "$0")/.."

GREEN=$'\033[92m'; RED=$'\033[91m'; YELLOW=$'\033[93m'; RESET=$'\033[0m'
DOWN_AFTER=false
[[ "${1:-}" == "--down" ]] && DOWN_AFTER=true

step() { echo; echo "${YELLOW}▶${RESET} $*"; }
ok()   { echo "  ${GREEN}✓${RESET} $*"; }
err()  { echo "  ${RED}✗${RESET} $*"; }

# ---------- 1. Pre-flight ----------
step "[1/6] Pre-flight checks"

if ! command -v docker >/dev/null 2>&1; then
    err "ไม่พบ docker — install ก่อน: https://docs.docker.com/get-docker/"
    exit 1
fi
ok "docker found ($(docker --version | head -c 60))"

if ! docker compose version >/dev/null 2>&1; then
    err "docker compose plugin ไม่มี — install ก่อน"
    exit 1
fi
ok "docker compose plugin available"

if ! docker info >/dev/null 2>&1; then
    err "docker daemon ไม่ทำงาน — start Docker Desktop / systemctl start docker"
    exit 1
fi
ok "docker daemon running"

if [[ ! -f .env ]]; then
    cp .env.example .env
    ok "สร้าง .env จาก .env.example"
else
    ok ".env exists"
fi

# ---------- 2. Build + start stack ----------
step "[2/6] docker compose up -d --build (อาจใช้ 2-5 นาที ครั้งแรก)"
docker compose up -d --build
ok "stack started"

# ---------- 3. Wait for backend healthy ----------
step "[3/6] รอ backend ตอบ /healthz"
ready=false
for i in $(seq 1 60); do
    if curl -fsS http://localhost:8000/healthz >/dev/null 2>&1; then
        ready=true; break
    fi
    sleep 2
done
if ! $ready; then
    err "backend ไม่ตอบใน 120s — ดู logs:"
    docker compose logs backend --tail 50
    exit 1
fi
ok "backend ตอบ /healthz แล้ว ($(($(date +%s) - $(date +%s)))s)"

# ---------- 4. pytest ----------
step "[4/6] pytest (backend unit tests)"
if docker compose exec -T backend pytest tests/ -q --tb=short; then
    ok "pytest passed"
else
    err "pytest failed — ดู logs ข้างบน"
    $DOWN_AFTER && docker compose down
    exit 1
fi

# ---------- 5. smoke_e2e ----------
step "[5/6] smoke_e2e.py (HTTP flow Phase 0-6)"

# หา python จาก host
py_cmd=""
for c in python3 python py; do
    if command -v $c >/dev/null 2>&1 && $c --version >/dev/null 2>&1; then
        py_cmd=$c
        break
    fi
done

if [[ -z "$py_cmd" ]]; then
    err "ไม่พบ python ใน host — รัน smoke ผ่าน container แทน"
    docker compose exec -T backend python /app/../scripts/smoke_e2e.py || {
        err "smoke_e2e failed"
        $DOWN_AFTER && docker compose down
        exit 1
    }
else
    $py_cmd scripts/smoke_e2e.py || {
        err "smoke_e2e failed"
        $DOWN_AFTER && docker compose down
        exit 1
    }
fi
ok "smoke_e2e passed"

# ---------- 6. Summary ----------
step "[6/6] ${GREEN}E2E PASSED${RESET}"
cat <<EOF

  เปิด services:
    • Backend API   → http://localhost:8000/api/docs
    • Admin UI      → http://localhost:3000
    • MinIO Console → http://localhost:9001  (minioadmin / minioadmin)
    • Prometheus    → http://localhost:8000/api/v1/metrics

  Login:
    username: admin
    password: ChangeMe123!    ⚠ เปลี่ยนทันที!

  จัดการ stack:
    docker compose ps           # ดูสถานะ
    docker compose logs -f      # ดู logs realtime
    docker compose down         # หยุด (ไม่ลบ volumes)
    docker compose down -v      # หยุด + ลบ data

EOF

if $DOWN_AFTER; then
    step "หยุด stack (--down flag)"
    docker compose down
fi
