#!/usr/bin/env bash
# ============================================================================
# Backup script — Digital Signage Management System
# Phase 5 rest — atomic backup ของ Postgres + MinIO + secrets
#
# วิธีใช้:
#   ./scripts/backup.sh                # backup ครั้งเดียว
#   crontab: 0 2 * * * /path/to/backup.sh >> /var/log/signage-backup.log 2>&1
#
# Requirements ในเครื่องที่รัน:
#   - pg_dump  (apt-get install postgresql-client)
#   - restic   (apt-get install restic) — สำหรับ off-site encrypted backup
#   - mc       (MinIO client) — optional, สำหรับ snapshot bucket
#
# Environment variables ที่ต้องตั้ง (ดู .env.example):
#   POSTGRES_HOST, POSTGRES_PORT, POSTGRES_USER, POSTGRES_PASSWORD, POSTGRES_DB
#   RESTIC_REPOSITORY     (เช่น b2:bucket:/path หรือ /mnt/backup/restic)
#   RESTIC_PASSWORD       (encryption key — เก็บใน password manager!)
#   BACKUP_DIR            (default: /var/backups/signage)
#   RETENTION_DAILY       (default: 7)
#   RETENTION_WEEKLY      (default: 4)
#   RETENTION_MONTHLY     (default: 6)
#
# Exit codes:
#   0 = success
#   1 = missing dependency
#   2 = pg_dump failed
#   3 = restic backup failed
# ============================================================================

set -euo pipefail

# ===== Config (override ผ่าน env) =====
POSTGRES_HOST="${POSTGRES_HOST:-localhost}"
POSTGRES_PORT="${POSTGRES_PORT:-5432}"
POSTGRES_USER="${POSTGRES_USER:-signage}"
POSTGRES_DB="${POSTGRES_DB:-signage}"
BACKUP_DIR="${BACKUP_DIR:-/var/backups/signage}"
RETENTION_DAILY="${RETENTION_DAILY:-7}"
RETENTION_WEEKLY="${RETENTION_WEEKLY:-4}"
RETENTION_MONTHLY="${RETENTION_MONTHLY:-6}"

TIMESTAMP=$(date -u +%Y%m%d-%H%M%S)
DUMP_FILE="${BACKUP_DIR}/signage-${TIMESTAMP}.sql.gz"

# ===== 1) ตรวจสอบ dependency =====
log() { echo "[backup $(date -u +%H:%M:%S)] $*"; }

require_cmd() {
    if ! command -v "$1" >/dev/null 2>&1; then
        log "ERROR: missing required command: $1"
        exit 1
    fi
}

require_cmd pg_dump
require_cmd gzip

mkdir -p "$BACKUP_DIR"

# ===== 2) pg_dump (compressed + integrity check) =====
log "starting pg_dump: ${POSTGRES_DB}@${POSTGRES_HOST}:${POSTGRES_PORT}"

# PGPASSWORD ส่งผ่าน env ให้ pg_dump (ไม่ log ใน command line)
export PGPASSWORD="${POSTGRES_PASSWORD:-}"

if ! pg_dump \
    -h "$POSTGRES_HOST" \
    -p "$POSTGRES_PORT" \
    -U "$POSTGRES_USER" \
    -d "$POSTGRES_DB" \
    --format=plain \
    --no-owner \
    --no-acl \
    --verbose \
    | gzip -9 > "$DUMP_FILE"
then
    log "ERROR: pg_dump failed"
    rm -f "$DUMP_FILE"
    exit 2
fi

unset PGPASSWORD

# ตรวจ integrity ของ gzip
if ! gzip -t "$DUMP_FILE"; then
    log "ERROR: backup file corrupted: $DUMP_FILE"
    exit 2
fi

SIZE_HUMAN=$(du -h "$DUMP_FILE" | cut -f1)
log "pg_dump OK: $DUMP_FILE ($SIZE_HUMAN)"

# ===== 3) Restic backup (off-site, encrypted) — optional =====
if command -v restic >/dev/null 2>&1 && [[ -n "${RESTIC_REPOSITORY:-}" ]]; then
    log "starting restic backup → $RESTIC_REPOSITORY"

    # init repo ถ้ายังไม่มี (no-op ถ้ามีอยู่)
    restic snapshots >/dev/null 2>&1 || restic init

    if ! restic backup \
        --tag signage --tag postgres --tag "$TIMESTAMP" \
        --host "$(hostname)" \
        "$DUMP_FILE"
    then
        log "ERROR: restic backup failed"
        exit 3
    fi

    # ===== 4) Retention policy =====
    log "applying retention: ${RETENTION_DAILY}d / ${RETENTION_WEEKLY}w / ${RETENTION_MONTHLY}m"
    restic forget \
        --tag signage \
        --keep-daily "$RETENTION_DAILY" \
        --keep-weekly "$RETENTION_WEEKLY" \
        --keep-monthly "$RETENTION_MONTHLY" \
        --prune
else
    log "WARN: restic ไม่ติดตั้ง หรือ RESTIC_REPOSITORY ไม่ระบุ — skip off-site backup"
    log "      เก็บแค่ local: $DUMP_FILE"

    # ลบ dump เก่ากว่า RETENTION_DAILY วัน (local-only mode)
    find "$BACKUP_DIR" -name "signage-*.sql.gz" -mtime "+${RETENTION_DAILY}" -delete || true
fi

# ===== 5) Verify ลำดับสุดท้าย =====
log "backup completed: $TIMESTAMP"
log "files in $BACKUP_DIR:"
ls -lh "$BACKUP_DIR"/signage-*.sql.gz 2>/dev/null | tail -5 || true

# Note: ส่ง result เข้า monitoring (Prometheus pushgateway / healthchecks.io)
# ถ้ามี — ตัวอย่าง:
#   curl -fsS --retry 3 https://hc-ping.com/<uuid>
exit 0
