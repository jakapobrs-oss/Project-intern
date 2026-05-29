# ============================================================
# verify.ps1 — static + integration smoke test (Windows)
# รัน: .\scripts\verify.ps1
#
# ทำ 5 ขั้น:
# 1. ตรวจไฟล์สำคัญครบมั้ย
# 2. parse Python syntax ทุกไฟล์
# 3. ถ้ามี docker: start stack + apply migration + run pytest + curl smoke
# 4. ถ้าไม่มี docker: skip ขั้น 3 และให้ summary
# 5. summary
# ============================================================

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

Write-Host "═══════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host " Signage Project — Verify Script" -ForegroundColor Cyan
Write-Host "═══════════════════════════════════════════════" -ForegroundColor Cyan

$failures = @()
function Ok($msg) { Write-Host "  ✓ $msg" -ForegroundColor Green }
function Fail($msg) { Write-Host "  ✗ $msg" -ForegroundColor Red; $script:failures += $msg }
function Info($msg) { Write-Host "  → $msg" -ForegroundColor Yellow }

# ── 1. Required files ───────────────────────────────────────
Write-Host "`n[1/5] ตรวจไฟล์สำคัญ" -ForegroundColor Cyan
$required = @(
    "docker-compose.yml", ".env.example", ".gitignore",
    "README.md", "PLAN.md", "WORKLOG.md", "SESSION.md",
    "backend/Dockerfile", "backend/requirements.txt", "backend/app/main.py",
    "backend/app/config.py", "backend/app/db.py",
    "backend/alembic.ini", "backend/alembic/env.py",
    "backend/alembic/versions/0001_initial_users.py",
    "backend/alembic/versions/0002_devices_contents.py",
    "backend/alembic/versions/0003_plans_schedules.py",
    "admin-ui/package.json", "admin-ui/Dockerfile",
    "player/android/build.gradle.kts",
    "player/android/app/build.gradle.kts",
    "player/web/index.html", "player/web/app.js",
    "tv-control/README.md"
)
foreach ($f in $required) {
    if (Test-Path $f) { Ok $f } else { Fail "missing: $f" }
}

# ── 2. Python syntax check ──────────────────────────────────
Write-Host "`n[2/5] Parse Python syntax (ทุกไฟล์ใน backend/app + tests)" -ForegroundColor Cyan
$python = (Get-Command python -ErrorAction SilentlyContinue) ?? (Get-Command python3 -ErrorAction SilentlyContinue)
if (-not $python) {
    Info "ไม่พบ python ในระบบ — ข้าม syntax check"
} else {
    $pyFiles = Get-ChildItem -Recurse backend/app, backend/tests, backend/alembic -Filter *.py -ErrorAction SilentlyContinue
    $bad = 0
    foreach ($f in $pyFiles) {
        $result = & $python.Source -c "import ast,sys; ast.parse(open(r'$($f.FullName)',encoding='utf-8').read())" 2>&1
        if ($LASTEXITCODE -ne 0) { Fail "syntax error: $($f.FullName) — $result"; $bad++ }
    }
    if ($bad -eq 0) { Ok "$($pyFiles.Count) python files OK" }
}

# ── 3. .env ─────────────────────────────────────────────────
Write-Host "`n[3/5] ตรวจ .env" -ForegroundColor Cyan
if (Test-Path ".env") {
    Ok ".env exists"
} else {
    Info ".env ไม่มี — คัดลอกจาก .env.example..."
    Copy-Item ".env.example" ".env"
    Ok "สร้าง .env แล้ว (โปรดแก้ JWT_SECRET_KEY ก่อน production)"
}

# ── 4. Docker integration (ถ้ามี) ───────────────────────────
Write-Host "`n[4/5] Docker integration test" -ForegroundColor Cyan
$docker = Get-Command docker -ErrorAction SilentlyContinue
if (-not $docker) {
    Info "ไม่พบ docker — ข้ามขั้นนี้ (ทดสอบ syntax + structure only)"
} else {
    try {
        docker info 2>&1 | Out-Null
        if ($LASTEXITCODE -ne 0) {
            Info "docker daemon ไม่ทำงาน — ข้ามขั้นนี้"
        } else {
            Info "docker พร้อม — รัน 'docker compose up -d --build' (อาจใช้เวลา 2-5 นาที)"
            docker compose up -d --build 2>&1 | Out-Null
            if ($LASTEXITCODE -ne 0) { Fail "docker compose up ล้มเหลว" }
            else {
                Ok "stack started"
                Info "รอ backend healthy (สูงสุด 60 วินาที)..."
                $ready = $false
                for ($i = 0; $i -lt 30; $i++) {
                    Start-Sleep -Seconds 2
                    try {
                        $r = Invoke-WebRequest "http://localhost:8000/healthz" -TimeoutSec 2 -ErrorAction Stop
                        if ($r.StatusCode -eq 200) { $ready = $true; break }
                    } catch { }
                }
                if (-not $ready) { Fail "backend ไม่ตอบใน 60 วินาที"; docker compose logs backend --tail 30 }
                else {
                    Ok "GET /healthz → 200"
                    # apply migration + seed
                    Info "apply migration..."
                    docker compose exec -T backend alembic upgrade head 2>&1 | Out-Null
                    if ($LASTEXITCODE -eq 0) { Ok "alembic upgrade head" } else { Fail "alembic migration ล้มเหลว" }
                    Info "seed admin..."
                    docker compose exec -T backend python -m app.scripts.seed 2>&1 | Out-Null
                    if ($LASTEXITCODE -eq 0) { Ok "seed admin" } else { Fail "seed admin ล้มเหลว" }
                    # pytest
                    Info "รัน pytest..."
                    docker compose exec -T backend pytest tests/ -q 2>&1 | Tee-Object -Variable testOutput | Out-Null
                    if ($LASTEXITCODE -eq 0) { Ok "pytest passed" } else { Fail "pytest failed: $testOutput" }
                    # smoke test API endpoints
                    Info "smoke test API..."
                    try {
                        $login = Invoke-RestMethod -Uri "http://localhost:8000/api/v1/auth/login" -Method POST -ContentType "application/x-www-form-urlencoded" -Body "username=admin&password=ChangeMe123!"
                        Ok "login → got access_token"
                        $H = @{ Authorization = "Bearer $($login.access_token)" }
                        $me = Invoke-RestMethod -Uri "http://localhost:8000/api/v1/auth/me" -Headers $H
                        Ok "auth/me → $($me.username) [$($me.role)]"
                    } catch { Fail "smoke test ล้มเหลว: $_" }
                }
            }
        }
    } catch { Fail "ขั้น docker error: $_" }
}

# ── 5. Summary ──────────────────────────────────────────────
Write-Host "`n[5/5] Summary" -ForegroundColor Cyan
if ($failures.Count -eq 0) {
    Write-Host "  ✅ ผ่านทั้งหมด" -ForegroundColor Green
    exit 0
} else {
    Write-Host "  ❌ $($failures.Count) failures:" -ForegroundColor Red
    foreach ($f in $failures) { Write-Host "     - $f" -ForegroundColor Red }
    exit 1
}
