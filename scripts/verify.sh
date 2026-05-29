#!/usr/bin/env bash
# verify.sh — Linux/macOS version ของ verify.ps1
# รัน: bash scripts/verify.sh
set -e
cd "$(dirname "$0")/.."

echo "═══════════════════════════════════════════════"
echo " Signage Project — Verify Script"
echo "═══════════════════════════════════════════════"

failures=()
ok()   { echo "  ✓ $*"; }
fail() { echo "  ✗ $*"; failures+=("$*"); }
info() { echo "  → $*"; }

# 1. Required files
echo
echo "[1/5] ตรวจไฟล์สำคัญ"
required=(
    docker-compose.yml .env.example .gitignore
    README.md PLAN.md WORKLOG.md SESSION.md
    backend/Dockerfile backend/requirements.txt backend/app/main.py
    backend/app/config.py backend/app/db.py
    backend/alembic.ini backend/alembic/env.py
    backend/alembic/versions/0001_initial_users.py
    backend/alembic/versions/0002_devices_contents.py
    backend/alembic/versions/0003_plans_schedules.py
    admin-ui/package.json admin-ui/Dockerfile
    player/android/build.gradle.kts
    player/android/app/build.gradle.kts
    player/web/index.html player/web/app.js
    tv-control/README.md
)
for f in "${required[@]}"; do
    if [[ -f "$f" ]]; then ok "$f"; else fail "missing: $f"; fi
done

# 2. Python syntax
echo
echo "[2/5] Parse Python syntax"

# หา python ที่ใช้งานได้จริง (ไม่ใช่ Windows Store stub)
py_cmd=""
for c in python3 python py; do
    if command -v $c >/dev/null 2>&1; then
        if $c --version >/dev/null 2>&1; then
            py_cmd=$c
            break
        fi
    fi
done

if [[ -z "$py_cmd" ]]; then
    info "ไม่พบ python ที่ใช้งานได้ — ข้าม syntax check"
    info "(ทางเลือก: docker compose exec backend ruff check)"
else
    info "ใช้ $py_cmd ($($py_cmd --version 2>&1))"
    bad=0
    total=0
    while IFS= read -r f; do
        total=$((total+1))
        if ! $py_cmd -c "import ast,sys; ast.parse(open(sys.argv[1],encoding='utf-8').read())" "$f" 2>/dev/null; then
            err=$($py_cmd -c "import ast,sys; ast.parse(open(sys.argv[1],encoding='utf-8').read())" "$f" 2>&1 | tail -1)
            fail "syntax error: $f — $err"
            bad=$((bad+1))
        fi
    done < <(find backend/app backend/tests backend/alembic -name "*.py" 2>/dev/null)
    [[ $bad -eq 0 ]] && ok "$total python files OK"
fi

# 2b. JSON syntax (ใช้ node ถ้ามี)
if command -v node >/dev/null 2>&1; then
    info "JSON files"
    bad=0
    for f in admin-ui/package.json admin-ui/tsconfig.json player/web/manifest.json; do
        if [[ -f "$f" ]]; then
            if node -e "JSON.parse(require('fs').readFileSync('$f','utf8'))" 2>/dev/null; then
                ok "  $f"
            else
                fail "  $f — invalid JSON"
                bad=$((bad+1))
            fi
        fi
    done
    info "JS syntax"
    for f in player/web/app.js player/web/sw.js; do
        if [[ -f "$f" ]]; then
            if node --check "$f" 2>/dev/null; then
                ok "  $f"
            else
                fail "  $f — JS parse error"
            fi
        fi
    done
fi

# 3. .env
echo
echo "[3/5] ตรวจ .env"
if [[ -f .env ]]; then ok ".env exists"
else
    info ".env ไม่มี — copy จาก .env.example"
    cp .env.example .env
    ok "สร้าง .env แล้ว (โปรดแก้ JWT_SECRET_KEY ก่อน production)"
fi

# 4. Docker integration
echo
echo "[4/5] Docker integration test"
if ! command -v docker >/dev/null 2>&1; then
    info "ไม่พบ docker — ข้ามขั้นนี้"
elif ! docker info >/dev/null 2>&1; then
    info "docker daemon ไม่ทำงาน — ข้ามขั้นนี้"
else
    info "docker พร้อม — รัน docker compose up -d --build (อาจใช้เวลา 2-5 นาที)"
    if docker compose up -d --build >/dev/null 2>&1; then
        ok "stack started"
        info "รอ backend healthy..."
        ready=false
        for i in $(seq 1 30); do
            sleep 2
            if curl -fsS http://localhost:8000/healthz >/dev/null 2>&1; then
                ready=true; break
            fi
        done
        if ! $ready; then
            fail "backend ไม่ตอบใน 60s"
            docker compose logs backend --tail 30
        else
            ok "GET /healthz → 200"
            info "apply migration..."
            if docker compose exec -T backend alembic upgrade head >/dev/null 2>&1; then ok "alembic upgrade head"; else fail "alembic migration"; fi
            info "seed admin..."
            if docker compose exec -T backend python -m app.scripts.seed >/dev/null 2>&1; then ok "seed admin"; else fail "seed admin"; fi
            info "pytest..."
            if docker compose exec -T backend pytest tests/ -q >/dev/null 2>&1; then ok "pytest passed"; else fail "pytest failed"; fi
            info "smoke API test..."
            token=$(curl -fsS -X POST http://localhost:8000/api/v1/auth/login \
                -d "username=admin&password=ChangeMe123!" | python3 -c "import sys,json;print(json.load(sys.stdin)['access_token'])" 2>/dev/null || echo "")
            if [[ -n "$token" ]]; then
                ok "login → got access_token"
                if curl -fsS -H "Authorization: Bearer $token" http://localhost:8000/api/v1/auth/me >/dev/null; then
                    ok "auth/me OK"
                else fail "auth/me failed"; fi
            else fail "login failed"; fi
        fi
    else
        fail "docker compose up failed"
    fi
fi

# 5. Summary
echo
echo "[5/5] Summary"
if [[ ${#failures[@]} -eq 0 ]]; then
    echo "  ✅ ผ่านทั้งหมด"
    exit 0
else
    echo "  ❌ ${#failures[@]} failures:"
    for f in "${failures[@]}"; do echo "     - $f"; done
    exit 1
fi
