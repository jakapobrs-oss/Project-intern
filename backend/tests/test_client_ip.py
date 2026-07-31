"""
ทดสอบการหา IP ผู้ใช้จริง — โดยเฉพาะเคสที่มีคนพยายามปลอม X-Forwarded-For

ที่มา: user-test 2026-07-31 พบว่า IP ใน audit เป็น 172.19.x (IP ในคอนเทนเนอร์)
ระหว่างไล่ดูพบว่าโค้ดเดิมเชื่อ header X-Forwarded-For ทุกกรณี ซึ่งใครก็แนบมาเองได้
"""
import pytest

from app.config import settings
from app.core import client_ip as mod


class _FakeClient:
    def __init__(self, host: str | None):
        self.host = host


class _FakeRequest:
    """แทน Request จริงเท่าที่ client_ip ใช้ — ไม่ต้องตั้ง ASGI ทั้งชุด"""

    def __init__(self, peer: str | None, headers: dict[str, str] | None = None):
        self.client = _FakeClient(peer) if peer else None
        self.headers = {k.lower(): v for k, v in (headers or {}).items()}


@pytest.fixture
def trusted_docker(monkeypatch):
    """ตั้งให้เชื่อ proxy ในวง docker (172.16.0.0/12) เหมือน deploy จริงที่มี nginx"""
    monkeypatch.setattr(settings, "trusted_proxies", "172.16.0.0/12")
    mod._parse_networks.cache_clear()
    yield
    mod._parse_networks.cache_clear()


@pytest.fixture
def trust_nobody(monkeypatch):
    monkeypatch.setattr(settings, "trusted_proxies", "")
    mod._parse_networks.cache_clear()
    yield
    mod._parse_networks.cache_clear()


# ===== ไม่ตั้ง trusted proxy = ไม่เชื่อ header เลย =====

def test_ignores_forwarded_header_when_no_proxy_configured(trust_nobody):
    """ค่า default ต้องไม่เชื่อ X-Forwarded-For — ไม่งั้นปลอมได้ทันที"""
    req = _FakeRequest("203.0.113.9", {"X-Forwarded-For": "1.2.3.4"})
    assert mod.client_ip(req) == "203.0.113.9"


def test_uses_peer_when_no_header(trust_nobody):
    req = _FakeRequest("203.0.113.9")
    assert mod.client_ip(req) == "203.0.113.9"


# ===== ตั้ง trusted proxy แล้ว =====

def test_trusts_header_from_configured_proxy(trusted_docker):
    """ผ่าน nginx ในวง docker → ได้ IP จริงของผู้ใช้จาก header"""
    req = _FakeRequest("172.19.0.5", {"X-Forwarded-For": "203.0.113.9"})
    assert mod.client_ip(req) == "203.0.113.9"


def test_spoofed_header_from_untrusted_peer_is_ignored(trusted_docker):
    """ผู้ใช้ต่อตรงแล้วแนบ header ปลอมมาเอง → ต้องไม่หลงเชื่อ"""
    req = _FakeRequest("203.0.113.9", {"X-Forwarded-For": "8.8.8.8"})
    assert mod.client_ip(req) == "203.0.113.9"


def test_spoofed_entry_prepended_by_client_is_skipped(trusted_docker):
    """
    ผู้ใช้แนบ X-Forwarded-For ปลอมมา แล้ว nginx ต่อท้ายด้วย IP จริง
    (พฤติกรรมของ $proxy_add_x_forwarded_for) — ต้องหยิบตัวขวาสุดที่ไม่ใช่ proxy ของเรา
    """
    req = _FakeRequest(
        "172.19.0.5", {"X-Forwarded-For": "9.9.9.9, 203.0.113.9"}
    )
    assert mod.client_ip(req) == "203.0.113.9"


def test_multiple_trusted_hops_are_skipped(trusted_docker):
    """มี proxy ของเราซ้อนกันหลายชั้น → ข้ามให้หมดจนเจอผู้ใช้จริง"""
    req = _FakeRequest(
        "172.19.0.5", {"X-Forwarded-For": "203.0.113.9, 172.20.0.3, 172.19.0.7"}
    )
    assert mod.client_ip(req) == "203.0.113.9"


def test_all_hops_trusted_falls_back_to_leftmost(trusted_docker):
    req = _FakeRequest("172.19.0.5", {"X-Forwarded-For": "172.20.0.3"})
    assert mod.client_ip(req) == "172.20.0.3"


# ===== ค่าเสีย/ขอบ =====

def test_broken_config_does_not_crash(monkeypatch):
    """ค่า config พิมพ์ผิดต้องไม่ทำให้ระบบล่ม — แค่ไม่เชื่อ proxy ตัวนั้น"""
    monkeypatch.setattr(settings, "trusted_proxies", "ไม่ใช่ไอพี, 172.16.0.0/12")
    mod._parse_networks.cache_clear()
    req = _FakeRequest("172.19.0.5", {"X-Forwarded-For": "203.0.113.9"})
    assert mod.client_ip(req) == "203.0.113.9"
    mod._parse_networks.cache_clear()


def test_no_client_returns_none(trust_nobody):
    assert mod.client_ip(_FakeRequest(None)) is None
    assert mod.client_ip(None) is None


def test_garbage_header_value_is_not_trusted(trusted_docker):
    """ค่าใน header ที่ไม่ใช่ IP → ถือว่าไม่ใช่ proxy ของเรา จึงถูกคืนตามหลักขวาสุด"""
    req = _FakeRequest("172.19.0.5", {"X-Forwarded-For": "not-an-ip"})
    assert mod.client_ip(req) == "not-an-ip"
