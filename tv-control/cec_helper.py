#!/usr/bin/env python3
"""
HDMI-CEC native helper — wrap `cec-client` (Pulse-Eight libcec)
Phase 7 — completes player-side TV control สำหรับ Linux RPi player

Why subprocess (not python-cec binding):
  - python-cec ต้อง compile libcec จาก source + build wheel เอง (ยุ่งบน RPi)
  - cec-client CLI มาใน apt: `apt-get install cec-utils`
  - performance พอใช้ (< 100ms per command) — TV control ไม่ realtime

Usage modes:
  1. Standalone CLI:
       python cec_helper.py power on
       python cec_helper.py power off
       python cec_helper.py volume up
       python cec_helper.py volume down
       python cec_helper.py mute
       python cec_helper.py raw "10:36"        # raw CEC hex (10=TV, 36=standby)
       python cec_helper.py scan               # scan devices บน CEC bus

  2. HTTP service (called from Web PWA player):
       python cec_helper.py serve              # listen 127.0.0.1:7600 (localhost only)
       curl -X POST http://127.0.0.1:7600/cec/power -d '{"on": true}'

  3. Python module:
       from cec_helper import send_cec_command
       send_cec_command("standby 0")           # ปิดทีวี

Install:
  sudo apt-get install cec-utils
  # ตรวจ HDMI-CEC bus connected (TV เปิด CEC)
  echo scan | cec-client -s -d 1

Permissions:
  cec-client ต้องการ access /dev/cec0 — เพิ่ม user เข้า group video:
  sudo usermod -aG video $USER && newgrp video
"""
from __future__ import annotations
import argparse
import json
import logging
import re
import shutil
import subprocess
import sys
from http.server import BaseHTTPRequestHandler, HTTPServer

logger = logging.getLogger("cec_helper")
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")


# ─── CEC command mapping ────────────────────────────────────────────
# libcec CLI accepts text commands via stdin
CEC_COMMANDS: dict[str, str] = {
    "power_on":    "on 0",          # 0 = address TV
    "power_off":   "standby 0",
    "volume_up":   "volup",
    "volume_down": "voldown",
    "mute":        "mute",
    "as_active":   "as",            # ask TV to switch to this HDMI source
}

# ─── Subprocess helper ──────────────────────────────────────────────

CEC_CLIENT = "cec-client"
CEC_TIMEOUT_SEC = 10


def is_available() -> bool:
    """ตรวจว่า cec-client ติดตั้งและรันได้"""
    return shutil.which(CEC_CLIENT) is not None


def send_cec_command(cmd: str, *, timeout_sec: int = CEC_TIMEOUT_SEC) -> tuple[bool, str]:
    """
    ส่ง 1 command ผ่าน cec-client (stdin mode)

    Args:
        cmd: คำสั่งที่ libcec CLI เข้าใจ เช่น "on 0", "standby 0", "volup"

    Returns:
        (success, stdout_or_error)
    """
    if not is_available():
        return False, "cec-client ไม่ได้ติดตั้ง — `sudo apt-get install cec-utils`"

    try:
        # -s = single command + exit (ไม่ interactive)
        # -d 1 = log level "Error only" (กัน spam)
        proc = subprocess.run(
            [CEC_CLIENT, "-s", "-d", "1"],
            input=cmd + "\n",
            capture_output=True,
            text=True,
            timeout=timeout_sec,
        )
        ok = proc.returncode == 0
        out = (proc.stdout or "") + (proc.stderr or "")
        return ok, out.strip()
    except subprocess.TimeoutExpired:
        return False, f"timeout after {timeout_sec}s"
    except Exception as e:
        return False, f"exception: {e}"


def send_named(cmd_name: str) -> tuple[bool, str]:
    """ส่ง command ที่ map ใน CEC_COMMANDS"""
    cmd = CEC_COMMANDS.get(cmd_name)
    if cmd is None:
        return False, f"unknown command: {cmd_name} (valid: {list(CEC_COMMANDS.keys())})"
    return send_cec_command(cmd)


def send_raw_hex(hex_str: str) -> tuple[bool, str]:
    """
    ส่ง raw CEC frame เป็น hex string (e.g. "10:36" → standby คำสั่ง)
    cec-client เข้าใจคำสั่ง `tx <hex>`
    """
    clean = re.sub(r"[^0-9a-fA-F:]", "", hex_str)
    if not clean:
        return False, "invalid hex"
    return send_cec_command(f"tx {clean}")


def scan_devices() -> tuple[bool, str]:
    """รัน `scan` เพื่อหา CEC device ทั้งหมดใน bus"""
    return send_cec_command("scan", timeout_sec=20)


# ─── HTTP service (localhost only) ──────────────────────────────────

class CecHandler(BaseHTTPRequestHandler):
    """
    Simple HTTP API สำหรับเรียกจาก Web PWA player
    Bind 127.0.0.1 only — ห้าม expose ออกข้างนอก (ไม่มี auth)
    """

    def _send_json(self, status: int, body: dict) -> None:
        data = json.dumps(body).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Access-Control-Allow-Origin", "*")    # CORS สำหรับ PWA localhost
        self.send_header("Access-Control-Allow-Methods", "POST, GET, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()
        self.wfile.write(data)

    def do_OPTIONS(self) -> None:  # CORS preflight
        self._send_json(204, {})

    def do_GET(self) -> None:
        if self.path == "/health":
            self._send_json(200, {"status": "ok", "cec_available": is_available()})
            return
        if self.path == "/scan":
            ok, out = scan_devices()
            self._send_json(200 if ok else 500, {"ok": ok, "output": out})
            return
        self._send_json(404, {"error": "not_found"})

    def do_POST(self) -> None:
        try:
            length = int(self.headers.get("Content-Length", "0"))
            body = json.loads(self.rfile.read(length)) if length > 0 else {}
        except Exception as e:
            self._send_json(400, {"error": f"bad json: {e}"})
            return

        path = self.path.rstrip("/")
        if path == "/cec/power":
            cmd = "power_on" if body.get("on", True) else "power_off"
            ok, out = send_named(cmd)
        elif path == "/cec/volume":
            direction = body.get("direction", "up").lower()
            cmd = "volume_up" if direction == "up" else "volume_down"
            ok, out = send_named(cmd)
        elif path == "/cec/mute":
            ok, out = send_named("mute")
        elif path == "/cec/named":
            ok, out = send_named(body.get("name", ""))
        elif path == "/cec/raw":
            ok, out = send_raw_hex(body.get("hex", ""))
        else:
            self._send_json(404, {"error": "unknown endpoint", "path": path})
            return

        self._send_json(200 if ok else 500, {"ok": ok, "output": out})

    # quiet down access log
    def log_message(self, format: str, *args) -> None:
        logger.debug("HTTP " + format % args)


def serve_http(port: int = 7600, bind: str = "127.0.0.1") -> None:
    server = HTTPServer((bind, port), CecHandler)
    logger.info(f"CEC helper listening on http://{bind}:{port}")
    logger.info(f"cec-client available: {is_available()}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        logger.info("shutting down")
        server.shutdown()


# ─── CLI entrypoint ─────────────────────────────────────────────────

def main() -> int:
    parser = argparse.ArgumentParser(description="HDMI-CEC helper สำหรับ Linux player")
    sub = parser.add_subparsers(dest="cmd", required=True)

    sub.add_parser("power").add_argument("state", choices=["on", "off"])
    sub.add_parser("volume").add_argument("direction", choices=["up", "down"])
    sub.add_parser("mute")
    sub.add_parser("scan")

    p_raw = sub.add_parser("raw")
    p_raw.add_argument("hex", help="raw CEC hex e.g. '10:36'")

    p_serve = sub.add_parser("serve")
    p_serve.add_argument("--port", type=int, default=7600)
    p_serve.add_argument("--bind", default="127.0.0.1")

    args = parser.parse_args()

    if args.cmd == "power":
        ok, out = send_named("power_on" if args.state == "on" else "power_off")
    elif args.cmd == "volume":
        ok, out = send_named("volume_up" if args.direction == "up" else "volume_down")
    elif args.cmd == "mute":
        ok, out = send_named("mute")
    elif args.cmd == "scan":
        ok, out = scan_devices()
    elif args.cmd == "raw":
        ok, out = send_raw_hex(args.hex)
    elif args.cmd == "serve":
        serve_http(port=args.port, bind=args.bind)
        return 0
    else:
        parser.error(f"unknown cmd: {args.cmd}")
        return 2

    print(out)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
