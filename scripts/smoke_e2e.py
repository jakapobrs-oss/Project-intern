"""
smoke_e2e.py — end-to-end smoke test (ต้องการ docker compose up รันอยู่)

ครอบคลุม flow ทั้งหมดที่ phase 0-5 + 6 ใช้:
  [1] health + readiness + metrics
  [2] auth: login + refresh + me
  [3] device: create + pair + heartbeat
  [4] content: create url-content + approve workflow
  [5] presentation + plan + schedule
  [6] manifest (with content + emergency)
  [7] emergency broadcast: create → activate → manifest override → cancel
  [8] tv command queue
  [9] audit log filter
  [10] cleanup

รัน: python scripts/smoke_e2e.py [base_url]
    default base_url = http://localhost:8000
"""
import json
import os
import sys
import time
import urllib.request
import urllib.error
import urllib.parse

# Windows console (cp1252) encode อักขระ ✓/→/emoji ไม่ได้ → บังคับ stdout เป็น UTF-8
# (กัน UnicodeEncodeError ตั้งแต่ print บรรทัดแรกก่อนเช็คใดๆ บน terminal มาตรฐานของ Windows)
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass


BASE_URL = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8000"
ADMIN_USER = os.getenv("ADMIN_USERNAME", "admin")
ADMIN_PASS = os.getenv("ADMIN_PASSWORD", "ChangeMe123!")


def http(
    method: str,
    path: str,
    *,
    body=None,
    headers=None,
    form=False,
) -> tuple[int, dict | list | str]:
    url = BASE_URL + path
    h = {"Accept": "application/json", **(headers or {})}
    data = None
    if body is not None:
        if form:
            data = urllib.parse.urlencode(body).encode()
            h.setdefault("Content-Type", "application/x-www-form-urlencoded")
        else:
            data = json.dumps(body).encode()
            h.setdefault("Content-Type", "application/json")
    req = urllib.request.Request(url, data=data, headers=h, method=method)
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            text = resp.read().decode()
            try:
                return resp.status, json.loads(text)
            except json.JSONDecodeError:
                return resp.status, text
    except urllib.error.HTTPError as e:
        text = e.read().decode()
        try:
            return e.code, json.loads(text)
        except Exception:
            return e.code, text


def check(name: str, ok: bool, info: str = "") -> None:
    mark = "✓" if ok else "✗"
    color = "\033[92m" if ok else "\033[91m"
    reset = "\033[0m"
    print(f"  {color}{mark}{reset} {name}" + (f"  ({info})" if info else ""))
    if not ok:
        failures.append(name)


failures: list[str] = []
print(f"smoke_e2e.py → {BASE_URL}")
print("=" * 60)


# ═══ 1. health + readiness + metrics ═══
print("\n[1] Health / Readiness / Metrics")
status, _ = http("GET", "/healthz")
check("GET /healthz", status == 200)

status, ready = http("GET", "/api/v1/readiness")
check("GET /readiness", status == 200, f"db={ready.get('db') if isinstance(ready, dict) else '?'}")

status, metrics = http("GET", "/api/v1/metrics")
check("GET /metrics (Prometheus)", status == 200 and "signage_devices_total" in (metrics or ""))


# ═══ 2. login + refresh + me ═══
print("\n[2] Auth — login + refresh + me")
status, body = http("POST", "/api/v1/auth/login", body={"username": ADMIN_USER, "password": ADMIN_PASS}, form=True)
check("POST /auth/login", status == 200, f"status={status}")
if status != 200:
    print("→ ตรวจสอบว่า seed admin แล้วมั้ย: docker compose exec backend python -m app.scripts.seed")
    sys.exit(1)

ACCESS = body["access_token"]
REFRESH = body["refresh_token"]
H = {"Authorization": f"Bearer {ACCESS}"}

status, refreshed = http("POST", "/api/v1/auth/refresh", body={"refresh_token": REFRESH})
check("POST /auth/refresh", status == 200 and "access_token" in (refreshed or {}))

status, me = http("GET", "/api/v1/auth/me", headers=H)
check("GET /auth/me", status == 200 and me.get("username") == ADMIN_USER, f"role={me.get('role')}")


# ═══ 3. device create + pair + heartbeat ═══
print("\n[3] Device — create + pair + heartbeat")
status, dev = http("POST", "/api/v1/devices", body={
    "name": "smoke-test-tv",
    "location": "smoke test",
    "platform": "android_tv",
    "tv_brand": "samsung",
}, headers=H)
check("POST /devices", status == 201, f"id={dev.get('id', '?')[:8]}…")
device_id = dev["id"]
pairing_code = dev["pairing_code"]
check("pairing_code generated", pairing_code is not None and len(pairing_code) == 6)

status, pair = http("POST", "/api/v1/player/pair", body={
    "pairing_code": pairing_code,
    "platform": "android_tv",
    "mac_address": "AA:BB:CC:DD:EE:FF",
    "app_version": "0.2.0",
})
check("POST /player/pair", status == 200, "got token")
DEVICE_TOKEN = pair["device_token"]
DH = {"Authorization": f"Bearer {DEVICE_TOKEN}"}

status, hb = http("POST", "/api/v1/player/heartbeat",
                  body={"status": "online", "uptime_sec": 60, "cpu_percent": 23.5}, headers=DH)
check("POST /player/heartbeat", status == 200, f"manifest_outdated={hb.get('manifest_outdated')}")


# ═══ 4. content + approve workflow ═══
print("\n[4] Content — URL content + approve")
status, content = http("POST", "/api/v1/contents/url", body={
    "name": "smoke-url-content",
    "description": "smoke test url",
    "type": "web",
    "url": "https://example.com",
}, headers=H)
check("POST /contents/url", status == 201, f"id={content.get('id', '?')[:8]}…")
content_id = content["id"]

status, content2 = http("POST", f"/api/v1/contents/{content_id}/submit", headers=H)
check("POST /contents/{id}/submit", status == 200 and content2.get("approval_status") == "pending")

status, content3 = http("POST", f"/api/v1/contents/{content_id}/approve",
                        body={"approve": True}, headers=H)
check("POST /contents/{id}/approve", status == 200 and content3.get("approval_status") == "approved")


# ═══ 5. presentation + plan + schedule ═══
print("\n[5] Presentation + Plan + Schedule")
status, group = http("POST", "/api/v1/groups", body={
    "name": "smoke-group",
    "description": "smoke test group",
    "device_ids": [device_id],
}, headers=H)
check("POST /groups", status == 201, f"id={group.get('id', '?')[:8]}…")
group_id = group["id"]

status, pres = http("POST", "/api/v1/presentations", body={
    "name": "smoke-pres",
    "description": "fullscreen",
    "layout_json": {"template": "fullscreen", "zones": [{"key": "main", "x": 0, "y": 0, "w": 100, "h": 100}]},
    "duration_sec": 10,
    "zones": [{"zone_key": "main", "content_id": content_id, "order_index": 0, "params_json": {}}],
}, headers=H)
check("POST /presentations", status == 201)
pres_id = pres["id"]

status, plan = http("POST", "/api/v1/plans", body={
    "name": "smoke-plan",
    "description": "",
    "items": [{"presentation_id": pres_id, "order_index": 0}],
}, headers=H)
check("POST /plans", status == 201, f"items={len(plan.get('items', []))}")
plan_id = plan["id"]

# create schedule (admin → active immediately)
from datetime import datetime, timedelta, timezone
start_at = datetime.now(timezone.utc).isoformat()
end_at = (datetime.now(timezone.utc) + timedelta(hours=1)).isoformat()
status, sched = http("POST", "/api/v1/schedules", body={
    "name": "smoke-sched",
    "plan_id": plan_id,
    "player_group_id": group_id,
    "start_at": start_at,
    "end_at": end_at,
    "priority": 500,
}, headers=H)
check("POST /schedules", status == 201, f"status={sched.get('status')}")
schedule_id = sched["id"]


# ═══ 6. manifest — ต้องมี content + schedule แล้ว ═══
print("\n[6] Manifest")
status, manifest = http("GET", "/api/v1/player/manifest", headers=DH)
check("GET /player/manifest", status == 200, f"version={manifest.get('version', '?')[:8]}…")
check("manifest.device_id matches", manifest.get("device_id") == device_id)
check("manifest.items not empty (schedule applied)", len(manifest.get("items", [])) >= 1,
      f"items={len(manifest.get('items', []))}")
check("manifest.emergencies empty", isinstance(manifest.get("emergencies"), list) and len(manifest.get("emergencies", [])) == 0)
manifest_v1 = manifest.get("version")


# ═══ 7. emergency override flow ═══
print("\n[7] Emergency — create → activate → manifest override → cancel")
status, emer = http("POST", "/api/v1/emergency/", body={
    "title": "smoke-emergency",
    "kind": "text",
    "payload": {"message": "smoke test", "bg_color": "#c00", "text_color": "#fff"},
    "target": {"all": True},
    "priority": 2000,
}, headers=H)
check("POST /emergency", status == 201, f"status={emer.get('status')}")
emer_id = emer["id"]

status, emer2 = http("POST", f"/api/v1/emergency/{emer_id}/activate", headers=H)
check("POST /emergency/{id}/activate", status == 200 and emer2.get("status") == "active")

# manifest must now include emergency + new version
status, manifest2 = http("GET", "/api/v1/player/manifest", headers=DH)
check("manifest.emergencies has 1 entry after activate",
      len(manifest2.get("emergencies", [])) == 1, f"count={len(manifest2.get('emergencies', []))}")
check("manifest.version bumped", manifest2.get("version") != manifest_v1,
      f"{manifest_v1[:8]}→{manifest2.get('version', '')[:8]}")

status, emer3 = http("POST", f"/api/v1/emergency/{emer_id}/cancel", headers=H)
check("POST /emergency/{id}/cancel", status == 200 and emer3.get("status") == "cancelled")

# manifest must no longer have emergency
status, manifest3 = http("GET", "/api/v1/player/manifest", headers=DH)
check("manifest.emergencies empty after cancel", len(manifest3.get("emergencies", [])) == 0)


# ═══ 8. TV command queue ═══
print("\n[8] TV command queue")
status, cmd = http("POST", f"/api/v1/tv/devices/{device_id}/commands",
                   body={"command_type": "power_on"}, headers=H)
check("POST /tv/devices/{id}/commands", status == 202, f"cmd_id={cmd.get('cmd_id', '?')[:8]}…")
cmd_id = cmd["cmd_id"]

status, pending = http("GET", "/api/v1/player/commands", headers=DH)
check("GET /player/commands", status == 200 and len(pending) >= 1, f"got {len(pending)} pending")
if pending:
    pulled = pending[0]
    check("raw_bytes_hex present", pulled.get("raw_bytes_hex") not in (None, ""))
    check("brand=samsung", pulled.get("brand") == "samsung")
    status, _ = http("POST", f"/api/v1/player/commands/{pulled['cmd_id']}/ack",
                     body={"success": True}, headers=DH)
    check("POST /player/commands/{id}/ack", status == 204)

time.sleep(0.3)
status, st = http("GET", f"/api/v1/tv/commands/{cmd_id}/status", headers=H)
check("GET /tv/commands/{id}/status", status == 200 and st.get("status") == "success",
      f"status={st.get('status')}")


# ═══ 9. audit log filter ═══
print("\n[9] Audit log")
status, logs = http("GET", "/api/v1/audit/logs?action=auth.login&limit=10", headers=H)
check("GET /audit/logs?action=auth.login", status == 200 and isinstance(logs, list),
      f"got {len(logs) if isinstance(logs, list) else '?'} rows")
check("audit has emergency.activate event",
      any(r.get("action") == "emergency.activate" and r.get("target_id") == emer_id
          for r in (http("GET", "/api/v1/audit/logs?action=emergency.activate&limit=10", headers=H)[1] or [])))


# ═══ 10. cleanup ═══
print("\n[10] Cleanup")
http("DELETE", f"/api/v1/schedules/{schedule_id}", headers=H)
http("DELETE", f"/api/v1/plans/{plan_id}", headers=H)
http("DELETE", f"/api/v1/presentations/{pres_id}", headers=H)
http("DELETE", f"/api/v1/contents/{content_id}", headers=H)
http("DELETE", f"/api/v1/groups/{group_id}", headers=H)
status, _ = http("DELETE", f"/api/v1/devices/{device_id}", headers=H)
check("DELETE /devices/{id}", status == 204)


# ═══ summary ═══
print()
print("=" * 60)
if failures:
    print(f"\033[91m❌ {len(failures)} failures:\033[0m")
    for f in failures:
        print(f"   - {f}")
    sys.exit(1)
else:
    print("\033[92m✅ all smoke checks passed\033[0m")
    sys.exit(0)
