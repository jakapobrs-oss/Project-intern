"""
tv_emulator.py — Virtual TV: decode raw bytes (ที่ backend สร้างและ player จะยิงเข้า Serial Port/CEC จริง)
แล้วแสดงสถานะ TV (power / input / volume / mute) — ใช้สาธิต "สิ่งที่ทำ ข้อ 2" โดยไม่ต้องมี TV จริง

decode mirror กับ backend/app/services/tv_control/base.py เป๊ะ (Samsung MDC / LG / Sony / Panasonic / NEC / CEC)

2 โหมด:
  - import VirtualTV ไปใช้ใน emulated_player.py (in-process, ไม่ต้องลงอะไร)
  - serial listener: python tv_emulator.py --port COM11 --brand samsung   (อ่านจาก virtual COM ที่ com0com สร้าง)
"""
import argparse
import sys
import unicodedata

try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass


# ============================================================================
# Decoder — รับ (brand, raw bytes) → (action label, state changes)
# ============================================================================
def decode(brand: str, raw: bytes) -> tuple[str, dict]:
    brand = (brand or "cec").lower()
    try:
        if brand == "samsung":
            return _dec_samsung(raw)
        if brand == "lg":
            return _dec_lg(raw)
        if brand == "sony":
            return _dec_sony(raw)
        if brand == "panasonic":
            return _dec_panasonic(raw)
        if brand == "nec":
            return _dec_nec(raw)
        if brand in ("cec", "toshiba"):
            return _dec_cec(raw)
    except Exception as e:
        return (f"⚠ decode error: {e} (raw={raw.hex()})", {})
    return (f"⚠ unknown brand={brand} (raw={raw.hex()})", {})


def _dec_samsung(raw: bytes):
    # [0xAA][CMD][ID][LEN][DATA..][CHECKSUM]
    if len(raw) < 5 or raw[0] != 0xAA:
        return (f"⚠ Samsung frame ไม่ถูกต้อง (raw={raw.hex()})", {})
    body, cksum = raw[1:-1], raw[-1]
    ok = (sum(body) & 0xFF) == cksum
    cmd, _id, ln = body[0], body[1], body[2]
    data = body[3:3 + ln]
    chk = "" if ok else "  ✗CHECKSUM"
    if cmd == 0x11:
        return (f"POWER {'ON' if data and data[0] == 0x01 else 'OFF'}{chk}",
                {"power": bool(data and data[0] == 0x01)})
    if cmd == 0x12:
        return (f"SET VOLUME {data[0]}{chk}", {"volume": data[0]})
    if cmd == 0x13:
        return (f"{'MUTE' if data and data[0] == 0x01 else 'UNMUTE'}{chk}",
                {"mute": bool(data and data[0] == 0x01)})
    if cmd == 0x14:
        m = {0x21: "HDMI1", 0x22: "HDMI2", 0x23: "HDMI3"}
        src = m.get(data[0] if data else -1, f"0x{data.hex()}")
        return (f"INPUT → {src}{chk}", {"input": src})
    if cmd == 0x00:
        return (f"GET STATUS{chk}", {})
    return (f"Samsung cmd 0x{cmd:02x}{chk}", {})


def _dec_lg(raw: bytes):
    # ASCII "op id val\r"
    s = raw.decode(errors="replace").strip()
    parts = s.split()
    if len(parts) < 3:
        return (f"LG raw='{s}'", {})
    op, _id, val = parts[0], parts[1], parts[2]
    if op == "ka":
        return (f"POWER {'ON' if val == '01' else 'OFF'}", {"power": val == "01"})
    if op == "ke":
        return (f"{'MUTE' if val == '00' else 'UNMUTE'}", {"mute": val == "00"})
    if op == "kf":
        return (f"SET VOLUME {int(val, 16)}", {"volume": int(val, 16)})
    if op == "xb":
        m = {"90": "HDMI1", "91": "HDMI2", "92": "HDMI3"}
        return (f"INPUT → {m.get(val, val)}", {"input": m.get(val, val)})
    return (f"LG {op} {val}", {})


def _dec_sony(raw: bytes):
    # "*SC<CMD4><16param>\n"
    s = raw.decode(errors="replace").strip()
    if not s.startswith("*S") or len(s) < 7:
        return (f"Sony raw='{s}'", {})
    cmd = s[3:7]
    param = s[7:]
    pval = param.lstrip("0") or "0"
    if cmd == "POWR":
        return (f"POWER {'ON' if pval == '1' else 'OFF'}", {"power": pval == "1"})
    if cmd == "AMUT":
        return (f"{'MUTE' if pval == '1' else 'UNMUTE'}", {"mute": pval == "1"})
    if cmd == "VOLU":
        return (f"SET VOLUME {int(pval)}", {"volume": int(pval)})
    if cmd == "INPT":
        last = param[-1]
        return (f"INPUT → HDMI{last}", {"input": f"HDMI{last}"})
    return (f"Sony {cmd}={pval}", {})


def _dec_panasonic(raw: bytes):
    # STX payload ETX
    if len(raw) < 3 or raw[0] != 0x02 or raw[-1] != 0x03:
        return (f"Panasonic frame ผิด (raw={raw.hex()})", {})
    p = raw[1:-1].decode(errors="replace")
    mapping = {"PON": ("POWER ON", {"power": True}), "POF": ("POWER OFF", {"power": False}),
               "AMT:1": ("MUTE", {"mute": True}), "AMT:0": ("UNMUTE", {"mute": False}),
               "IIS:HD1": ("INPUT → HDMI1", {"input": "HDMI1"}),
               "IIS:HD2": ("INPUT → HDMI2", {"input": "HDMI2"}),
               "IIS:HD3": ("INPUT → HDMI3", {"input": "HDMI3"})}
    if p in mapping:
        return mapping[p]
    if p.startswith("AVL:"):
        return (f"SET VOLUME {int(p[4:])}", {"volume": int(p[4:])})
    return (f"Panasonic '{p}'", {})


def _dec_nec(raw: bytes):
    # match known power on/off sequences (base.py)
    if b"\x30\x30\x30\x31\x03" in raw:
        return ("POWER ON", {"power": True})
    if b"\x30\x30\x30\x34\x03" in raw:
        return ("POWER OFF", {"power": False})
    return (f"NEC raw={raw.hex()}", {})


def _dec_cec(raw: bytes):
    kw = raw.decode(errors="replace").strip().upper()
    m = {"ON": ("POWER ON (CEC)", {"power": True}),
         "STANDBY": ("POWER OFF (CEC)", {"power": False}),
         "VOLUP": ("VOLUME + (CEC)", {}), "VOLDOWN": ("VOLUME - (CEC)", {}),
         "MUTE": ("MUTE (CEC)", {"mute": True})}
    return m.get(kw, (f"CEC '{kw}'", {}))


# ============================================================================
# Virtual TV — เก็บสถานะ + วาดหน้าจอ (กว้างคงที่ รองรับอักษรไทย/wide ด้วย _dw)
# ============================================================================
def _dw(s: str) -> int:
    """display width: combining mark=0, East-Asian wide/full=2, อื่นๆ=1"""
    w = 0
    for ch in s:
        if unicodedata.combining(ch):
            continue
        w += 2 if unicodedata.east_asian_width(ch) in ("W", "F") else 1
    return w


def _pad(s: str, width: int) -> str:
    return s + " " * max(0, width - _dw(s))


def _fit(s: str, width: int) -> str:
    """ตัดข้อความให้พอดี display width (กันชื่อยาวล้นกล่อง)"""
    if _dw(s) <= width:
        return s
    out = ""
    for ch in s:
        if _dw(out + ch) > width - 1:
            return out + "…"
        out += ch
    return out


class VirtualTV:
    def __init__(self, brand: str, name: str = "Virtual TV"):
        self.brand = brand
        self.name = name
        self.power = False
        self.input = "—"
        self.volume = 20
        self.mute = False

    def apply(self, raw: bytes) -> str:
        action, delta = decode(self.brand, raw)
        for k, v in delta.items():
            setattr(self, k, v)
        return action

    def screen(self) -> str:
        W = 38  # ความกว้างภายในกล่อง (ASCII ล้วน → align แน่นอน)
        bar = "+" + "-" * W + "+"

        def row(s):
            return "| " + _pad(_fit(s, W - 1), W - 1) + "|"

        if not self.power:
            l1, l2 = "POWER: OFF   (standby)", ""
        else:
            l1 = f"POWER: ON    SOURCE: {self.input}"
            l2 = f"VOLUME: {self.volume:<3}  " + ("[MUTED]" if self.mute else "")
        return "\n".join([bar, row(f"[TV] {self.name}  ({self.brand})"),
                          row(""), row(l1), row(l2), bar])


# ============================================================================
# Serial listener mode (ใช้กับ com0com) — อ่าน byte จาก virtual COM
# ============================================================================
def _serial_listen(port: str, brand: str):
    try:
        import serial  # pyserial
    except ImportError:
        print("✗ ต้องลง pyserial ก่อน: backend\\.venv\\Scripts\\python.exe -m pip install pyserial")
        sys.exit(1)
    tv = VirtualTV(brand, name=f"Virtual TV @ {port}")
    print(f"🎧 ฟัง serial {port} @9600 (brand={brand}) — รอ byte จาก player … Ctrl+C เพื่อออก\n")
    print(tv.screen(), flush=True)
    with serial.Serial(port, 9600, timeout=1) as ser:
        buf = bytearray()
        while True:
            chunk = ser.read(256)
            if not chunk:
                continue
            buf += chunk
            # แต่ละ command มาเป็นเฟรมเดียว (demo) → decode ทั้ง buffer แล้วเคลียร์
            action = tv.apply(bytes(buf))
            print(f"\n📥 recv {bytes(buf).hex()}  →  {action}")
            print(tv.screen(), flush=True)
            buf.clear()


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="Virtual TV emulator")
    ap.add_argument("--port", help="COM port ฝั่งรับ (com0com) เช่น COM11")
    ap.add_argument("--brand", default="samsung",
                    choices=["samsung", "lg", "sony", "panasonic", "nec", "cec", "toshiba"])
    args = ap.parse_args()
    if args.port:
        _serial_listen(args.port, args.brand)
    else:
        # self-test: decode ตัวอย่าง Samsung power-on (0xAA 11 00 01 01 13)
        tv = VirtualTV(args.brand)
        for hexs in ["AA11000101 13".replace(" ", ""), "aa1400012147".replace(" ", "")]:
            try:
                print(tv.apply(bytes.fromhex(hexs)))
            except Exception as e:
                print("err", e)
        print(tv.screen())
