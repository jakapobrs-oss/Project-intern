"""
ตั้งค่า demo content + device (ยังไม่ pair) สำหรับ web player E2E
สร้าง: device(web_browser) + web content(example.com) + presentation + plan + schedule(active)
→ print PAIR_CODE ให้ puppeteer เอาไป pair

รัน:    python _webplayer_setup.py            # setup → print PAIR_CODE / DEVICE_ID
ลบทิ้ง: python _webplayer_setup.py --cleanup DEVICE_ID
"""
import sys
import json
import urllib.request
import urllib.error
import urllib.parse
from datetime import datetime, timedelta, timezone

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

BASE = "http://localhost:8000"


def http(method, path, body=None, headers=None, form=False):
    h = {"Accept": "application/json", **(headers or {})}
    data = None
    if body is not None:
        if form:
            data = urllib.parse.urlencode(body).encode()
            h.setdefault("Content-Type", "application/x-www-form-urlencoded")
        else:
            data = json.dumps(body).encode()
            h.setdefault("Content-Type", "application/json")
    req = urllib.request.Request(BASE + path, data=data, headers=h, method=method)
    try:
        with urllib.request.urlopen(req, timeout=10) as r:
            t = r.read().decode()
            return r.status, (json.loads(t) if t else None)
    except urllib.error.HTTPError as e:
        t = e.read().decode()
        try:
            return e.code, json.loads(t)
        except Exception:
            return e.code, t


def login():
    st, b = http("POST", "/api/v1/auth/login",
                 {"username": "admin", "password": "ChangeMe123!"}, form=True)
    assert st == 200, f"login {st} {b}"
    return {"Authorization": f"Bearer {b['access_token']}"}


if len(sys.argv) >= 3 and sys.argv[1] == "--cleanup":
    AH = login()
    http("DELETE", f"/api/v1/devices/{sys.argv[2]}", headers=AH)
    print("cleanup done")
    sys.exit(0)

AH = login()

st, dev = http("POST", "/api/v1/devices", {
    "name": "web-player-emu", "location": "emulator",
    "platform": "web_browser", "tv_brand": "samsung"}, AH)
assert st == 201, f"device {st} {dev}"
did, code = dev["id"], dev["pairing_code"]

# web content (public URL → ผ่าน url_guard + iframe ได้)
st, c = http("POST", "/api/v1/contents/url", {
    "name": "หน้าเว็บประชาสัมพันธ์", "description": "demo",
    "type": "web", "url": "https://example.com"}, AH)
assert st == 201, f"content {st} {c}"
cid = c["id"]
http("POST", f"/api/v1/contents/{cid}/submit", headers=AH)
http("POST", f"/api/v1/contents/{cid}/approve", {"approve": True}, AH)

st, g = http("POST", "/api/v1/groups",
             {"name": "emu-grp", "description": "", "device_ids": [did]}, AH)
gid = g["id"]
st, p = http("POST", "/api/v1/presentations", {
    "name": "emu-pres", "description": "fullscreen",
    "layout_json": {"template": "fullscreen",
                    "zones": [{"key": "main", "x": 0, "y": 0, "w": 100, "h": 100}]},
    "duration_sec": 30,
    "zones": [{"zone_key": "main", "content_id": cid, "order_index": 0, "params_json": {}}]}, AH)
pid = p["id"]
st, pl = http("POST", "/api/v1/plans", {
    "name": "emu-plan", "description": "",
    "items": [{"presentation_id": pid, "order_index": 0}]}, AH)
plid = pl["id"]
sa = datetime.now(timezone.utc).isoformat()
ea = (datetime.now(timezone.utc) + timedelta(hours=2)).isoformat()
st, sc = http("POST", "/api/v1/schedules", {
    "name": "emu-sched", "plan_id": plid, "player_group_id": gid,
    "start_at": sa, "end_at": ea, "priority": 500}, AH)
assert st == 201, f"schedule {st} {sc}"

print(f"PAIR_CODE={code}")
print(f"DEVICE_ID={did}")
print("SETUP_OK")
