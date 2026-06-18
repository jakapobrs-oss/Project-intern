"""
ทดสอบ content pipeline — magic bytes detection (ไม่แตะ S3)
ทดสอบ S3 upload ใน integration test (Phase ถัดไป)
"""
from app.models.content import ContentType
from app.services.content_service import detect_mime_from_magic


def test_detect_jpeg():
    head = b"\xFF\xD8\xFF\xE0" + b"\x00" * 60
    mime, ctype = detect_mime_from_magic(head)
    assert mime == "image/jpeg"
    assert ctype == ContentType.IMAGE


def test_detect_png():
    head = b"\x89PNG\r\n\x1a\n" + b"\x00" * 60
    mime, ctype = detect_mime_from_magic(head)
    assert mime == "image/png"
    assert ctype == ContentType.IMAGE


def test_detect_webp():
    head = b"RIFF\x00\x00\x00\x00WEBP" + b"\x00" * 50
    mime, ctype = detect_mime_from_magic(head)
    assert mime == "image/webp"
    assert ctype == ContentType.IMAGE


def test_detect_gif():
    head = b"GIF89a" + b"\x00" * 60
    mime, ctype = detect_mime_from_magic(head)
    assert mime == "image/gif"


def test_detect_mp4():
    """MP4 มี 'ftyp' offset 4"""
    head = b"\x00\x00\x00\x20ftypisom" + b"\x00" * 50
    mime, ctype = detect_mime_from_magic(head)
    assert ctype == ContentType.VIDEO


def test_detect_unknown_returns_none():
    head = b"this is not a real file" + b"\x00" * 40
    mime, ctype = detect_mime_from_magic(head)
    assert mime is None
    assert ctype is None
