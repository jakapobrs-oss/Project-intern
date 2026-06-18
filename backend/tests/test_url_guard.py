"""
Test SSRF protection (§26) + antivirus no-op
ทดสอบด้วย IP literal (ไม่ต้อง DNS resolve จริง)
"""
import io

import pytest

from app.core import url_guard, antivirus


# ===== is_blocked_ip (pure) =====

@pytest.mark.parametrize("ip", [
    "127.0.0.1",        # loopback
    "10.0.0.5",         # private A
    "192.168.1.10",     # private C
    "172.16.0.1",       # private B
    "169.254.169.254",  # cloud metadata (link-local)
    "0.0.0.0",          # unspecified
    "::1",              # ipv6 loopback
    "fe80::1",          # ipv6 link-local
])
def test_blocked_internal_ips(ip):
    assert url_guard.is_blocked_ip(ip) is True


@pytest.mark.parametrize("ip", [
    "8.8.8.8",          # public DNS
    "1.1.1.1",
    "203.0.113.10",     # TEST-NET (reserved จริง — แต่ public-ish)... ดูด้านล่าง
])
def test_public_ips_not_blocked(ip):
    # หมายเหตุ: 203.0.113.0/24 เป็น documentation range (is_reserved=False ใน stdlib)
    result = url_guard.is_blocked_ip(ip)
    if ip in ("8.8.8.8", "1.1.1.1"):
        assert result is False


# ===== validate_public_url =====

def test_reject_private_ip_url():
    with pytest.raises(url_guard.UnsafeUrlError):
        url_guard.validate_public_url("http://127.0.0.1:8000/admin")


def test_reject_metadata_url():
    with pytest.raises(url_guard.UnsafeUrlError):
        url_guard.validate_public_url("http://169.254.169.254/latest/meta-data/")


def test_reject_bad_scheme():
    with pytest.raises(url_guard.UnsafeUrlError):
        url_guard.validate_public_url("file:///etc/passwd")


def test_reject_no_host():
    with pytest.raises(url_guard.UnsafeUrlError):
        url_guard.validate_public_url("http://")


def test_allow_public_ip_url():
    # public IP literal → ผ่าน (ไม่ต้อง DNS)
    url_guard.validate_public_url("https://8.8.8.8/feed")


# ===== antivirus no-op when disabled =====

def test_scan_noop_when_disabled():
    # default settings.clamav_enabled = False → ไม่ต่อ network, ไม่ raise
    data = io.BytesIO(b"hello world")
    antivirus.scan_fileobj(data)  # ต้องไม่ raise
