"""
Phase 7 polish — Sentry PII scrubber tests

ทดสอบ pure functions ใน core/sentry.py โดยตรง
ไม่ต้องการ sentry_sdk ติดตั้ง (test logic เท่านั้น)
"""

from app.core.sentry import _before_send, _mask_email, _mask_phone, _scrub_value

# ─── Helpers ─────────────────────────────────────────────────────────

def test_mask_email():
    assert _mask_email("admin@example.com") == "a***@example.com"
    assert _mask_email("user.name+tag@sub.co.th") == "u***@sub.co.th"
    assert _mask_email("plain text no email") == "plain text no email"


def test_mask_phone():
    assert _mask_phone("call 0812345678 now") == "call 081****678 now"
    assert _mask_phone("0987654321") == "098****321"
    # ไม่ใช่ Thai format (no leading 0) → ไม่แตะ
    assert _mask_phone("9999") == "9999"


# ─── Scrub recursive ─────────────────────────────────────────────────

def test_scrub_value_redacts_sensitive_keys():
    payload = {
        "username": "admin",
        "password": "supersecret",
        "data": {"api_key": "xxx", "items": [1, 2]},
    }
    out = _scrub_value(payload)
    assert out["username"] == "admin"
    assert out["password"] == "[Filtered]"
    assert out["data"]["api_key"] == "[Filtered]"
    assert out["data"]["items"] == [1, 2]


def test_scrub_value_handles_token_variants():
    payload = {
        "device_token": "abc",
        "DeviceTokenHash": "xyz",        # case-insensitive
        "REFRESH_TOKEN": "ref",
        "csrf_token": "csrf",
        "pairing_code": "ABC123",
        "normal_field": "ok",
    }
    out = _scrub_value(payload)
    assert out["device_token"] == "[Filtered]"
    assert out["DeviceTokenHash"] == "[Filtered]"
    assert out["REFRESH_TOKEN"] == "[Filtered]"
    assert out["csrf_token"] == "[Filtered]"
    assert out["pairing_code"] == "[Filtered]"
    assert out["normal_field"] == "ok"


def test_scrub_value_recursive_list_of_dicts():
    payload = {
        "users": [
            {"name": "a", "password": "p1"},
            {"name": "b", "secret": "s2"},
        ],
    }
    out = _scrub_value(payload)
    assert out["users"][0]["password"] == "[Filtered]"
    assert out["users"][1]["secret"] == "[Filtered]"
    assert out["users"][0]["name"] == "a"


def test_scrub_value_masks_email_in_strings():
    out = _scrub_value({"msg": "contact admin@example.com please"})
    assert "admin@example.com" not in out["msg"]
    assert "a***@example.com" in out["msg"]


# ─── before_send hook ────────────────────────────────────────────────

def test_before_send_scrubs_request_data():
    event = {
        "request": {
            "data": {"username": "admin", "password": "secret"},
            "headers": {"Authorization": "Bearer xxx", "User-Agent": "test"},
            "cookies": "session=abc",
            "query_string": "token=xxx&keep=ok",
        }
    }
    out = _before_send(event, hint={})
    assert out is not None
    assert out["request"]["data"]["password"] == "[Filtered]"
    assert out["request"]["data"]["username"] == "admin"
    assert out["request"]["headers"]["Authorization"] == "[Filtered]"
    assert out["request"]["headers"]["User-Agent"] == "test"
    assert out["request"]["cookies"] == "[Filtered]"
    assert "token=[Filtered]" in out["request"]["query_string"]
    assert "keep=ok" in out["request"]["query_string"]


def test_before_send_masks_user_email():
    event = {"user": {"id": "u-1", "email": "admin@example.com"}}
    out = _before_send(event, hint={})
    assert out is not None
    assert out["user"]["email"] == "a***@example.com"


def test_before_send_scrubs_breadcrumbs():
    event = {
        "breadcrumbs": {
            "values": [
                {"type": "http", "data": {"method": "POST", "Authorization": "Bearer xx"}},
            ],
        },
    }
    out = _before_send(event, hint={})
    crumb = out["breadcrumbs"]["values"][0]
    assert crumb["data"]["Authorization"] == "[Filtered]"
    assert crumb["data"]["method"] == "POST"


def test_before_send_handles_missing_fields_gracefully():
    """event ที่ไม่มี request / user / breadcrumbs → ต้องไม่ raise"""
    event = {"message": "hello world"}
    out = _before_send(event, hint={})
    assert out is not None
    assert out["message"] == "hello world"


def test_before_send_masks_email_in_message():
    event = {"message": "error: contact admin@example.com"}
    out = _before_send(event, hint={})
    assert "admin@example.com" not in out["message"]
    assert "a***@example.com" in out["message"]
