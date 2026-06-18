"""
cec_helper_stub.py — จำลอง HDMI-CEC helper (แทน tv-control/cec_helper.py ที่ต้องมี libcec + สาย HDMI จริง)

มี HTTP API ชุดเดียวกับ cec_helper.py (ตาม tv-control/README.md) ให้ player/web (sendViaCecHelper)
หรือ curl เรียกได้ → จำลองการคุม TV ผ่าน HDMI-CEC โดยไม่ต้องมี CEC bus จริง

รัน:  python cec_helper_stub.py            # ฟัง 127.0.0.1:7600 (เหมือนของจริง)
ทดสอบ: curl -X POST 127.0.0.1:7600/cec/named -d "{\"name\":\"power_on\"}"
"""
import json
import sys
from http.server import BaseHTTPRequestHandler, HTTPServer

from tv_emulator import VirtualTV

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

TV = VirtualTV("cec", name="Virtual TV (HDMI-CEC)")
_NAMED = {  # map ชื่อคำสั่ง → keyword ที่ base.py สร้างให้ CEC
    "power_on": "ON", "power_off": "STANDBY",
    "volume_up": "VOLUP", "volume_down": "VOLDOWN", "mute": "MUTE",
}


def _show(action: str):
    print(f"\n📥 [CEC] {action}")
    print(TV.screen(), flush=True)


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass  # เงียบ default access log

    def _send(self, obj, code=200):
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps(obj).encode())

    def _body(self):
        n = int(self.headers.get("Content-Length", 0))
        if not n:
            return {}
        try:
            return json.loads(self.rfile.read(n).decode())
        except Exception:
            return {}

    def do_GET(self):
        if self.path == "/health":
            self._send({"status": "ok", "cec_available": True})
        elif self.path == "/scan":
            self._send({"ok": True, "output": "device #0: TV (Virtual CEC) vendor: Emulator"})
        else:
            self._send({"ok": False, "error": "not found"}, 404)

    def do_POST(self):
        body = self._body()
        if self.path == "/cec/power":
            kw = "ON" if body.get("on") else "STANDBY"
        elif self.path == "/cec/volume":
            kw = "VOLUP" if body.get("direction") == "up" else "VOLDOWN"
        elif self.path == "/cec/mute":
            kw = "MUTE"
        elif self.path == "/cec/named":
            kw = _NAMED.get(body.get("name", ""), "")
        elif self.path == "/cec/raw":
            # ของจริงรับ "10:36" (logical addr:opcode) — stub แค่ echo
            self._send({"ok": True, "output": f"tx {body.get('hex','')}"})
            _show(f"raw {body.get('hex','')}")
            return
        else:
            self._send({"ok": False, "error": "not found"}, 404)
            return
        if not kw:
            self._send({"ok": False, "error": "unknown command"}, 400)
            return
        action = TV.apply(kw.encode())
        _show(action)
        self._send({"ok": True, "output": f"cec: {action}"})


if __name__ == "__main__":
    port = 7600
    print(f"🎧 CEC helper stub ฟัง 127.0.0.1:{port} (API เดียวกับ tv-control/cec_helper.py)")
    print(TV.screen(), flush=True)
    HTTPServer(("127.0.0.1", port), Handler).serve_forever()
