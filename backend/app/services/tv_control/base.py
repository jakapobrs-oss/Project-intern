"""
Base abstractions ของ TV control
"""
import enum
from dataclasses import dataclass


class TVBrand(str, enum.Enum):
    SAMSUNG = "samsung"   # MDC
    LG = "lg"
    SONY = "sony"         # SimpleIP / IR
    PANASONIC = "panasonic"
    NEC = "nec"
    TOSHIBA = "toshiba"
    CEC = "cec"           # ผ่าน HDMI-CEC (consumer TV ทั่วไป)


class TVCommandType(str, enum.Enum):
    POWER_ON = "power_on"
    POWER_OFF = "power_off"
    VOLUME_UP = "volume_up"
    VOLUME_DOWN = "volume_down"
    MUTE = "mute"
    UNMUTE = "unmute"
    SET_VOLUME = "set_volume"            # payload: {"value": 0-100}
    INPUT_HDMI1 = "input_hdmi1"
    INPUT_HDMI2 = "input_hdmi2"
    INPUT_HDMI3 = "input_hdmi3"
    GET_STATUS = "get_status"


@dataclass
class TVCommand:
    """1 command ที่จะส่งให้ TV"""
    brand: TVBrand
    command_type: TVCommandType
    payload: dict | None = None
    set_id: int = 0  # MDC set id (เผื่อหลายจอบน RS-232 chain เดียว) — 0 = ทุกจอ


# ===== Helper checksum =====

def _checksum(data: bytes) -> int:
    """sum byte → 1 byte (MDC, NEC ใช้)"""
    return sum(data) & 0xFF


# ===== Samsung MDC =====
# Format: [HEADER 0xAA] [CMD] [ID] [DATA_LEN] [DATA...] [CHECKSUM]
# Power: cmd 0x11, data 0x01=on / 0x00=off
# Volume: cmd 0x12, data 0x00-0x64
# Source: cmd 0x14, data 0x21=HDMI1 0x22=HDMI2 0x23=HDMI3

_SAMSUNG_CMD = {
    TVCommandType.POWER_ON: (0x11, bytes([0x01])),
    TVCommandType.POWER_OFF: (0x11, bytes([0x00])),
    TVCommandType.MUTE: (0x13, bytes([0x01])),
    TVCommandType.UNMUTE: (0x13, bytes([0x00])),
    TVCommandType.INPUT_HDMI1: (0x14, bytes([0x21])),
    TVCommandType.INPUT_HDMI2: (0x14, bytes([0x22])),
    TVCommandType.INPUT_HDMI3: (0x14, bytes([0x23])),
    TVCommandType.GET_STATUS: (0x00, b""),
}


def _build_samsung(cmd: TVCommand) -> bytes:
    if cmd.command_type == TVCommandType.SET_VOLUME:
        value = int((cmd.payload or {}).get("value", 50))
        value = max(0, min(100, value))
        cmd_code, data = 0x12, bytes([value])
    elif cmd.command_type == TVCommandType.VOLUME_UP:
        return _build_samsung(TVCommand(cmd.brand, TVCommandType.SET_VOLUME, {"value": 60}, cmd.set_id))
    elif cmd.command_type == TVCommandType.VOLUME_DOWN:
        return _build_samsung(TVCommand(cmd.brand, TVCommandType.SET_VOLUME, {"value": 30}, cmd.set_id))
    else:
        if cmd.command_type not in _SAMSUNG_CMD:
            raise ValueError(f"Samsung MDC ไม่รองรับ command: {cmd.command_type}")
        cmd_code, data = _SAMSUNG_CMD[cmd.command_type]

    body = bytes([cmd_code, cmd.set_id, len(data)]) + data
    return bytes([0xAA]) + body + bytes([_checksum(body)])


# ===== LG RS-232C =====
# Format ASCII: "kk <id> <data>\r"
# k= power, kc=input, kf=volume, ke=mute
# Power: "ka 01 01\r" = on, "ka 01 00\r" = off

_LG_CMD = {
    TVCommandType.POWER_ON: ("ka", "01"),
    TVCommandType.POWER_OFF: ("ka", "00"),
    TVCommandType.MUTE: ("ke", "00"),
    TVCommandType.UNMUTE: ("ke", "01"),
    TVCommandType.INPUT_HDMI1: ("xb", "90"),
    TVCommandType.INPUT_HDMI2: ("xb", "91"),
    TVCommandType.INPUT_HDMI3: ("xb", "92"),
}


def _build_lg(cmd: TVCommand) -> bytes:
    set_id = cmd.set_id or 1
    if cmd.command_type == TVCommandType.SET_VOLUME:
        value = int((cmd.payload or {}).get("value", 50))
        value = max(0, min(100, value))
        return f"kf {set_id:02d} {value:02X}\r".encode()
    if cmd.command_type not in _LG_CMD:
        raise ValueError(f"LG RS-232C ไม่รองรับ: {cmd.command_type}")
    op, val = _LG_CMD[cmd.command_type]
    return f"{op} {set_id:02d} {val}\r".encode()


# ===== Sony SimpleIP =====
# Format: "*S<C/E><FOUR_LETTER_CMD><16_DIGIT_PARAM>\n"
# Power: "*SCPOWR0000000000000001\n" = on
# Input: "*SCINPT0000000100000001\n" = HDMI1

def _sony_set_cmd(cmd_name: str, param: str) -> bytes:
    """build Sony SET command"""
    return f"*SC{cmd_name:<4}{param:>016}\n".encode()


def _build_sony(cmd: TVCommand) -> bytes:
    mapping = {
        TVCommandType.POWER_ON: ("POWR", "1"),
        TVCommandType.POWER_OFF: ("POWR", "0"),
        TVCommandType.MUTE: ("AMUT", "1"),
        TVCommandType.UNMUTE: ("AMUT", "0"),
        TVCommandType.INPUT_HDMI1: ("INPT", "100000001"),
        TVCommandType.INPUT_HDMI2: ("INPT", "100000002"),
        TVCommandType.INPUT_HDMI3: ("INPT", "100000003"),
    }
    if cmd.command_type == TVCommandType.SET_VOLUME:
        value = int((cmd.payload or {}).get("value", 50))
        value = max(0, min(100, value))
        return _sony_set_cmd("VOLU", str(value))
    if cmd.command_type not in mapping:
        raise ValueError(f"Sony SimpleIP ไม่รองรับ: {cmd.command_type}")
    name, param = mapping[cmd.command_type]
    return _sony_set_cmd(name, param)


# ===== Panasonic (Pro display) =====
# Format: STX <2-byte cmd> [param] ETX  → STX=0x02, ETX=0x03
# Power: STX "PON" ETX = on, STX "POF" ETX = off

def _panasonic_wrap(payload: str) -> bytes:
    return b"\x02" + payload.encode() + b"\x03"


def _build_panasonic(cmd: TVCommand) -> bytes:
    mapping = {
        TVCommandType.POWER_ON: "PON",
        TVCommandType.POWER_OFF: "POF",
        TVCommandType.MUTE: "AMT:1",
        TVCommandType.UNMUTE: "AMT:0",
        TVCommandType.INPUT_HDMI1: "IIS:HD1",
        TVCommandType.INPUT_HDMI2: "IIS:HD2",
        TVCommandType.INPUT_HDMI3: "IIS:HD3",
    }
    if cmd.command_type == TVCommandType.SET_VOLUME:
        value = int((cmd.payload or {}).get("value", 50))
        value = max(0, min(100, value))
        return _panasonic_wrap(f"AVL:{value:03d}")
    if cmd.command_type not in mapping:
        raise ValueError(f"Panasonic ไม่รองรับ: {cmd.command_type}")
    return _panasonic_wrap(mapping[cmd.command_type])


# ===== NEC =====
# Format: 0x01 0x30 0x?? 0x30 0x?? [CMD HEX ASCII...] 0x03 [CHECKSUM] 0x0D
# Power: "C2 03 D6 00 00 04 01 00 01" สำหรับ on (ตัวอย่างจาก manual)
# ใช้ alternate command "set parameter"

def _build_nec(cmd: TVCommand) -> bytes:
    mapping = {
        TVCommandType.POWER_ON: b"\x01\x30\x41\x30\x41\x30\x43\x02\x43\x32\x30\x33\x44\x36\x30\x30\x30\x30\x30\x34\x30\x31\x30\x30\x30\x31\x03",
        TVCommandType.POWER_OFF: b"\x01\x30\x41\x30\x41\x30\x43\x02\x43\x32\x30\x33\x44\x36\x30\x30\x30\x30\x30\x34\x30\x31\x30\x30\x30\x34\x03",
    }
    if cmd.command_type not in mapping:
        # commands อื่นๆ Phase ถัดไป (ต้องดู NEC monitor manual ของรุ่น)
        raise ValueError(f"NEC ยังไม่รองรับ command นี้: {cmd.command_type}")
    body = mapping[cmd.command_type]
    cksum = bytes([_checksum(body[1:])])  # checksum ไม่รวม SOH
    return body + cksum + b"\x0D"


# ===== HDMI-CEC =====
# CEC แต่ละ command เป็น opcode 1 byte ผ่าน libcec
# ตรงนี้คืน "opcode" + arg ให้ player ส่งผ่าน libcec lib

_CEC_CMD = {
    TVCommandType.POWER_ON: "ON",
    TVCommandType.POWER_OFF: "STANDBY",
    TVCommandType.VOLUME_UP: "VOLUP",
    TVCommandType.VOLUME_DOWN: "VOLDOWN",
    TVCommandType.MUTE: "MUTE",
}


def _build_cec(cmd: TVCommand) -> bytes:
    if cmd.command_type not in _CEC_CMD:
        raise ValueError(f"CEC ไม่รองรับ: {cmd.command_type}")
    # CEC ส่ง opcode keyword ให้ player แปลผ่าน libcec
    return _CEC_CMD[cmd.command_type].encode()


# ===== Dispatcher =====

_BUILDERS = {
    TVBrand.SAMSUNG: _build_samsung,
    TVBrand.LG: _build_lg,
    TVBrand.SONY: _build_sony,
    TVBrand.PANASONIC: _build_panasonic,
    TVBrand.NEC: _build_nec,
    TVBrand.CEC: _build_cec,
    TVBrand.TOSHIBA: _build_cec,  # Toshiba ใช้ CEC fallback
}


def build_command(cmd: TVCommand) -> bytes:
    """
    Entry point — รับ TVCommand → คืน raw bytes ที่ player จะส่งผ่าน serial/CEC
    raise ValueError ถ้า brand/command ไม่รองรับ
    """
    builder = _BUILDERS.get(cmd.brand)
    if builder is None:
        raise ValueError(f"ไม่รองรับ brand: {cmd.brand}")
    return builder(cmd)
