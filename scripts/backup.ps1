# ============================================================================
# backup.ps1 — Windows equivalent ของ backup.sh
# Phase 5 rest — atomic backup ของ Postgres + restic (Windows)
#
# วิธีใช้:
#   .\scripts\backup.ps1
#   Task Scheduler: รันทุก 02:00 ของทุกคืน
#
# ต้องติดตั้ง: pg_dump (จาก PostgreSQL installer), restic (https://restic.net)
# Env vars: ดู backup.sh (เหมือนกัน) — ตั้งผ่าน System Properties → Environment Variables
# ============================================================================

$ErrorActionPreference = "Stop"

# ===== Config (override ผ่าน env) =====
$PG_HOST = if ($env:POSTGRES_HOST) { $env:POSTGRES_HOST } else { "localhost" }
$PG_PORT = if ($env:POSTGRES_PORT) { $env:POSTGRES_PORT } else { "5432" }
$PG_USER = if ($env:POSTGRES_USER) { $env:POSTGRES_USER } else { "signage" }
$PG_DB   = if ($env:POSTGRES_DB)   { $env:POSTGRES_DB }   else { "signage" }
$BACKUP_DIR  = if ($env:BACKUP_DIR) { $env:BACKUP_DIR } else { "C:\backups\signage" }
$RETENTION_DAILY = if ($env:RETENTION_DAILY) { [int]$env:RETENTION_DAILY } else { 7 }

$TIMESTAMP = (Get-Date -Format "yyyyMMdd-HHmmss")
$DUMP_FILE = Join-Path $BACKUP_DIR "signage-$TIMESTAMP.sql.gz"

function Write-Log($msg) {
    Write-Host "[backup $(Get-Date -Format HH:mm:ss)] $msg"
}

# ตรวจ dependency
function Require-Cmd($name) {
    if (-not (Get-Command $name -ErrorAction SilentlyContinue)) {
        Write-Log "ERROR: missing required command: $name"
        exit 1
    }
}

Require-Cmd "pg_dump"

if (-not (Test-Path $BACKUP_DIR)) {
    New-Item -ItemType Directory -Path $BACKUP_DIR | Out-Null
}

# ===== pg_dump → gzip via pipeline =====
Write-Log "starting pg_dump: ${PG_DB}@${PG_HOST}:${PG_PORT}"

$env:PGPASSWORD = $env:POSTGRES_PASSWORD

try {
    # ใช้ .NET gzip stream เพราะ Windows ไม่มี gzip ใน PATH โดย default
    $tempSql = Join-Path $BACKUP_DIR "signage-$TIMESTAMP.sql.tmp"

    & pg_dump -h $PG_HOST -p $PG_PORT -U $PG_USER -d $PG_DB `
        --format=plain --no-owner --no-acl `
        -f $tempSql

    if ($LASTEXITCODE -ne 0) {
        Write-Log "ERROR: pg_dump failed (exit $LASTEXITCODE)"
        Remove-Item $tempSql -ErrorAction SilentlyContinue
        exit 2
    }

    # gzip ด้วย .NET (ไม่ต้องพึ่ง external gzip.exe)
    Add-Type -AssemblyName System.IO.Compression.FileSystem
    $inStream  = [System.IO.File]::OpenRead($tempSql)
    $outStream = [System.IO.File]::Create($DUMP_FILE)
    $gzStream  = New-Object System.IO.Compression.GZipStream($outStream, [System.IO.Compression.CompressionLevel]::Optimal)
    try {
        $inStream.CopyTo($gzStream)
    } finally {
        $gzStream.Dispose(); $outStream.Dispose(); $inStream.Dispose()
    }
    Remove-Item $tempSql

    $size = (Get-Item $DUMP_FILE).Length / 1MB
    Write-Log ("pg_dump OK: $DUMP_FILE ({0:N2} MB)" -f $size)
}
finally {
    Remove-Item Env:PGPASSWORD -ErrorAction SilentlyContinue
}

# ===== Restic (optional) =====
if ((Get-Command restic -ErrorAction SilentlyContinue) -and $env:RESTIC_REPOSITORY) {
    Write-Log "restic backup → $env:RESTIC_REPOSITORY"

    & restic snapshots 2>&1 | Out-Null
    if ($LASTEXITCODE -ne 0) { & restic init }

    & restic backup --tag signage --tag postgres --tag $TIMESTAMP $DUMP_FILE
    if ($LASTEXITCODE -ne 0) {
        Write-Log "ERROR: restic backup failed"
        exit 3
    }

    & restic forget --tag signage `
        --keep-daily $RETENTION_DAILY --keep-weekly 4 --keep-monthly 6 --prune
}
else {
    Write-Log "WARN: restic ไม่ติดตั้ง หรือ RESTIC_REPOSITORY ไม่ระบุ — skip off-site"

    # ลบ dump เก่ากว่า RETENTION_DAILY วัน
    $cutoff = (Get-Date).AddDays(-$RETENTION_DAILY)
    Get-ChildItem $BACKUP_DIR -Filter "signage-*.sql.gz" |
        Where-Object { $_.LastWriteTime -lt $cutoff } |
        Remove-Item -Force
}

Write-Log "backup completed: $TIMESTAMP"
exit 0
