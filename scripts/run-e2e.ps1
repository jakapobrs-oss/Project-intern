# ============================================================================
# run-e2e.ps1 — Windows version ของ run-e2e.sh
#
# รัน:
#   .\scripts\run-e2e.ps1
#   .\scripts\run-e2e.ps1 -Down    # หยุด stack หลังเสร็จ
# ============================================================================

param([switch]$Down)

$ErrorActionPreference = "Stop"

# ไปที่ project root
Set-Location (Join-Path $PSScriptRoot "..")

function Step($msg) { Write-Host ""; Write-Host "▶ $msg" -ForegroundColor Yellow }
function Ok($msg)   { Write-Host "  ✓ $msg" -ForegroundColor Green }
function Err($msg)  { Write-Host "  ✗ $msg" -ForegroundColor Red }

# ---------- 1. Pre-flight ----------
Step "[1/6] Pre-flight checks"

if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
    Err "ไม่พบ docker — install ก่อน: https://docs.docker.com/get-docker/"; exit 1
}
Ok "docker found"

try { & docker info 2>&1 | Out-Null } catch { Err "docker daemon ไม่ทำงาน — start Docker Desktop"; exit 1 }
if ($LASTEXITCODE -ne 0) { Err "docker daemon ไม่ทำงาน"; exit 1 }
Ok "docker daemon running"

if (-not (Test-Path ".env")) {
    Copy-Item ".env.example" ".env"
    Ok "สร้าง .env จาก .env.example"
} else { Ok ".env exists" }

# ---------- 2. Build + start ----------
Step "[2/6] docker compose up -d --build"
& docker compose up -d --build
if ($LASTEXITCODE -ne 0) { Err "docker compose failed"; exit 1 }
Ok "stack started"

# ---------- 3. Wait healthy ----------
Step "[3/6] รอ backend ตอบ /healthz"
$ready = $false
for ($i = 1; $i -le 60; $i++) {
    try {
        Invoke-WebRequest -Uri "http://localhost:8000/healthz" -TimeoutSec 3 -UseBasicParsing | Out-Null
        $ready = $true; break
    } catch { Start-Sleep -Seconds 2 }
}
if (-not $ready) {
    Err "backend ไม่ตอบใน 120s — ดู logs:"
    & docker compose logs backend --tail 50
    exit 1
}
Ok "backend ready"

# ---------- 4. pytest ----------
Step "[4/6] pytest"
& docker compose exec -T backend pytest tests/ -q --tb=short
if ($LASTEXITCODE -ne 0) {
    Err "pytest failed"
    if ($Down) { & docker compose down }
    exit 1
}
Ok "pytest passed"

# ---------- 5. smoke ----------
Step "[5/6] smoke_e2e.py (Phase 0-6)"
$env:PYTHONUTF8 = "1"   # กัน UnicodeEncodeError บน Windows cp1252 console (smoke print ✓/→/emoji)

$py = $null
foreach ($c in @("python", "py", "python3")) {
    if (Get-Command $c -ErrorAction SilentlyContinue) { $py = $c; break }
}
if (-not $py) {
    # compose mount แค่ ./backend:/app ไม่ได้ mount scripts/ → exec path /scripts/... ไม่มีจริง
    # จึง pipe สคริปต์เข้า stdin ของ python ในคอนเทนเนอร์ (smoke ใช้ stdlib ล้วน รันได้เลย)
    Err "ไม่พบ host python — pipe smoke_e2e.py เข้า container backend แทน"
    Get-Content "scripts/smoke_e2e.py" -Raw | & docker compose exec -T backend python - "http://localhost:8000"
} else {
    & $py "scripts/smoke_e2e.py"
}
if ($LASTEXITCODE -ne 0) {
    Err "smoke_e2e failed"
    if ($Down) { & docker compose down }
    exit 1
}
Ok "smoke_e2e passed"

# ---------- 6. Summary ----------
Step "[6/6] E2E PASSED"
Write-Host ""
Write-Host "  เปิด services:"
Write-Host "    • Backend API   → http://localhost:8000/api/docs"
Write-Host "    • Admin UI      → http://localhost:3000"
Write-Host "    • MinIO Console → http://localhost:9001  (minioadmin / minioadmin)"
Write-Host "    • Prometheus    → http://localhost:8000/api/v1/metrics"
Write-Host ""
Write-Host "  Login: admin / ChangeMe123!    ⚠ เปลี่ยนทันที!" -ForegroundColor Yellow
Write-Host ""

if ($Down) {
    Step "หยุด stack (-Down flag)"
    & docker compose down
}
