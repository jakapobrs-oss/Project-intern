"""
ทดสอบ TV protocol builders (pure functions — ไม่ต้อง mock hardware)
"""
import pytest

from app.services.tv_control import TVBrand, TVCommand, TVCommandType, build_command

# ===== Samsung MDC =====

def test_samsung_power_on():
    """Samsung MDC: power on = 0xAA 0x11 [id] 0x01 0x01 [chk]"""
    raw = build_command(TVCommand(TVBrand.SAMSUNG, TVCommandType.POWER_ON, set_id=0))
    assert raw[0] == 0xAA
    assert raw[1] == 0x11           # cmd: power
    assert raw[2] == 0x00           # set_id
    assert raw[3] == 0x01           # data len
    assert raw[4] == 0x01           # data: ON
    # checksum
    assert raw[5] == sum(raw[1:5]) & 0xFF


def test_samsung_power_off():
    raw = build_command(TVCommand(TVBrand.SAMSUNG, TVCommandType.POWER_OFF))
    assert raw[1] == 0x11
    assert raw[4] == 0x00


def test_samsung_set_volume_clamps():
    raw = build_command(TVCommand(TVBrand.SAMSUNG, TVCommandType.SET_VOLUME, payload={"value": 150}))
    assert raw[1] == 0x12
    assert raw[4] == 100  # clamped


def test_samsung_input_hdmi2():
    raw = build_command(TVCommand(TVBrand.SAMSUNG, TVCommandType.INPUT_HDMI2))
    assert raw[1] == 0x14
    assert raw[4] == 0x22


# ===== LG =====

def test_lg_power_on():
    """LG: 'ka 01 01\\r'"""
    raw = build_command(TVCommand(TVBrand.LG, TVCommandType.POWER_ON, set_id=1))
    assert raw == b"ka 01 01\r"


def test_lg_set_volume():
    raw = build_command(TVCommand(TVBrand.LG, TVCommandType.SET_VOLUME, payload={"value": 50}, set_id=1))
    # 50 hex = 32
    assert raw == b"kf 01 32\r"


# ===== Sony SimpleIP =====

def test_sony_power_on():
    raw = build_command(TVCommand(TVBrand.SONY, TVCommandType.POWER_ON))
    assert raw.startswith(b"*SCPOWR")
    assert raw.endswith(b"1\n")
    assert len(raw) == 24  # *S + C + 4-letter + 16-digit + \n


def test_sony_input_hdmi1():
    raw = build_command(TVCommand(TVBrand.SONY, TVCommandType.INPUT_HDMI1))
    assert b"INPT" in raw


# ===== Panasonic =====

def test_panasonic_power_on():
    """STX 'PON' ETX"""
    raw = build_command(TVCommand(TVBrand.PANASONIC, TVCommandType.POWER_ON))
    assert raw == b"\x02PON\x03"


def test_panasonic_input():
    raw = build_command(TVCommand(TVBrand.PANASONIC, TVCommandType.INPUT_HDMI2))
    assert b"IIS:HD2" in raw


# ===== NEC =====

def test_nec_power_on():
    raw = build_command(TVCommand(TVBrand.NEC, TVCommandType.POWER_ON))
    assert raw[0] == 0x01  # SOH
    assert raw[-1] == 0x0D  # CR


# ===== CEC =====

def test_cec_power_on():
    raw = build_command(TVCommand(TVBrand.CEC, TVCommandType.POWER_ON))
    assert raw == b"ON"


def test_cec_standby():
    raw = build_command(TVCommand(TVBrand.CEC, TVCommandType.POWER_OFF))
    assert raw == b"STANDBY"


# ===== Error handling =====

def test_unsupported_command():
    """Samsung ไม่รองรับ command บางอย่าง"""
    with pytest.raises(ValueError):
        build_command(TVCommand(TVBrand.NEC, TVCommandType.INPUT_HDMI3))


def test_toshiba_falls_back_to_cec():
    """Toshiba ใช้ CEC fallback"""
    raw = build_command(TVCommand(TVBrand.TOSHIBA, TVCommandType.POWER_ON))
    assert raw == b"ON"
