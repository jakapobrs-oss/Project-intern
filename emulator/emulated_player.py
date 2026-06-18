"""
emulated_player.py — จำลอง "เครื่องเล่นสื่อ" (signage player) แบบ software ล้วน เพื่อสาธิต "สิ่งที่ทำ"
ของบรีฟ โดยไม่ต้องมี hardware:

  สิ่งที่ทำ 1  — player เชื่อมต่อ backend ผ่าน LAN (pair + heartbeat + pull manifest ผ่าน HTTP)
  สิ่งที่ทำ 2a — แสดงผลข้อมูล (ดึง manifest มา render เป็นรายการที่จะขึ้นจอ)
  สิ่งที่ทำ 2b — ควบคุม TV ผ่าน Serial/HDMI-CEC:
                 admin ส่งคำสั่ง → backend สร้าง raw bytes → redis → player ดึง →
                 [in-process] decode ขึ้น Virtual TV   หรือ
                 [--serial-out COMx] เขียน byte จริงเข้า virtual COM (com0com) ให้ tv_emulator.py อ่าน

รัน (โหมด in-process, ไม่ต้องลงอะไร):
    python emulated_player.py --brand samsung

รัน (โหมด virtual serial — ต้องมี com0com COM10<->COM11 + pyserial):
    # หน้าต่าง 1:  python tv_emulator.py --port COM11 --brand samsung
    # หน้าต่าง 2:  python emulated_player.py --brand samsung --serial-out COM10
"""
import argparse
import json
import sys
import time
import urllib.request
import urllib.error
import urllib.parse

from tv_emulator import VirtualTV, decode

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

BASE = "http://localhost:8000"


def http(method, path, *, body=None, headers=None, form=False):
    url = BASE + path
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
        with urllib.request.urlopen(req, timeout=10) as r:
            t = r.read().decode()
            return r.status, (json.loads(t) if t else None)
    except urllib.error.HTTPError as e:
        t = e.read().decode()
        try:
            return e.code, json.loads(t)
        except Exception:
            return e.code, t


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--brand", default="samsung",
                    choices=["samsung", "lg", "sony", "panasonic", "nec", "cec", "toshiba"])
    ap.add_argument("--serial-out", help="เขียน raw bytes เข้า COM นี้ (com0com) แทน decode in-process")
    ap.add_argument("--keep", action="store_true", help="ไม่ลบ device ที่สร้างตอนจบ")
    args = ap.parse_args()

    ser = None
    if args.serial_out:
        try:
            import serial
            ser = serial.Serial(args.serial_out, 9600, timeout=1)
            print(f"🔌 เปิด serial {args.serial_out} @9600 — จะเขียน raw bytes เข้าพอร์ตนี้")
        except ImportError:
            print("✗ ต้องลง pyserial: backend\\.venv\\Scripts\\python.exe -m pip install pyserial"); sys.exit(1)

    print("=" * 60)
    print(f"  EMULATED SIGNAGE PLAYER  (brand={args.brand})")
    print("=" * 60)

    # ── สิ่งที่ทำ 1: เชื่อมต่อ backend ผ่าน LAN ──
    st, b = http("POST", "/api/v1/auth/login",
                 body={"username": "admin", "password": "ChangeMe123!"}, form=True)
    assert st == 200, f"login failed {st} {b}"
    AH = {"Authorization": f"Bearer {b['access_token']}"}
    print("\n[LAN] ✓ ต่อ backend ได้ (login admin)")

    st, dev = http("POST", "/api/v1/devices", body={
        "name": f"emu-{args.brand}", "location": "emulator",
        "platform": "android_tv", "tv_brand": args.brand}, headers=AH)
    assert st == 201, f"create device {st} {dev}"
    dev_id, code = dev["id"], dev["pairing_code"]
    print(f"[LAN] ✓ สร้าง device {dev_id[:8]}… (pairing code {code})")

    st, pair = http("POST", "/api/v1/player/pair", body={
        "pairing_code": code, "platform": "android_tv",
        "mac_address": "EE:00:00:00:00:01", "app_version": "emu-1.0"})
    assert st == 200, f"pair {st} {pair}"
    DH = {"Authorization": f"Bearer {pair['device_token']}"}
    print("[LAN] ✓ pair สำเร็จ (ได้ device token)")

    http("POST", "/api/v1/player/heartbeat",
         body={"status": "online", "uptime_sec": 1, "cpu_percent": 5.0}, headers=DH)
    print("[LAN] ✓ heartbeat → online")

    # ── สิ่งที่ทำ 2a: แสดงผลข้อมูล (manifest) ──
    st, mani = http("GET", "/api/v1/player/manifest", headers=DH)
    items = mani.get("items", []) if isinstance(mani, dict) else []
    print(f"\n[DISPLAY] ดึง manifest (version {str(mani.get('version',''))[:8]}…) — {len(items)} รายการที่จะขึ้นจอ:")
    if items:
        for it in items:
            print(f"          🖼  {it.get('name','?')}  ({it.get('type','?')}, {it.get('duration_sec','?')}s)")
    else:
        print("          (ยังไม่มี schedule active → จอจะขึ้นหน้า default/idle)")

    # ── สิ่งที่ทำ 2b: ควบคุม TV ผ่าน Serial/CEC ──
    print(f"\n[TV CONTROL] ส่งคำสั่งผ่าน backend → redis → player → {'serial '+args.serial_out if ser else 'Virtual TV (in-process)'}")
    tv = None if ser else VirtualTV(args.brand, name=f"emu-{args.brand}")
    if tv:
        print(tv.screen())

    sequence = [
        ("power_on", None), ("input_hdmi1", None), ("set_volume", {"value": 25}),
        ("mute", None), ("unmute", None), ("input_hdmi2", None), ("power_off", None),
    ]
    for ctype, payload in sequence:
        body = {"command_type": ctype}
        if payload:
            body["payload"] = payload
        st, cmd = http("POST", f"/api/v1/tv/devices/{dev_id}/commands", body=body, headers=AH)
        if st != 202:
            print(f"   (ข้าม {ctype}: backend ตอบ {st} {cmd})")
            continue
        time.sleep(0.15)
        # player ดึง pending commands
        st, pend = http("GET", "/api/v1/player/commands", headers=DH)
        for pc in (pend or []):
            raw = bytes.fromhex(pc["raw_bytes_hex"])
            brand = pc.get("brand", args.brand)
            if ser:
                ser.write(raw)
                print(f"   📤 {ctype:<12} → ส่ง {raw.hex()} เข้า {args.serial_out} (Virtual TV อีกหน้าต่างจะ decode)")
            else:
                action = tv.apply(raw)
                print(f"\n   ▶ admin สั่ง '{ctype}'  →  raw {raw.hex()}  →  TV: {action}")
                print(tv.screen())
            http("POST", f"/api/v1/player/commands/{pc['cmd_id']}/ack",
                 body={"success": True}, headers=DH)

    # cleanup
    if not args.keep:
        http("DELETE", f"/api/v1/devices/{dev_id}", headers=AH)
        print("\n[cleanup] ลบ emulator device แล้ว (ใช้ --keep ถ้าอยากเก็บ)")
    if ser:
        ser.close()
    print("\n✅ เดโมจบ — ครอบคลุม สิ่งที่ทำ 1 (LAN) + 2a (แสดงผล) + 2b (คุม TV ผ่าน serial/CEC)")


if __name__ == "__main__":
    main()
