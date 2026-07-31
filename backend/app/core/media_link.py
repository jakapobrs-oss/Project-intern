"""
ลิงก์ไฟล์สื่อสำหรับเครื่องเล่น (§22 signed URL)

ปัญหาที่โมดูลนี้แก้:
    เดิม manifest ส่ง pre-signed URL ของ MinIO ที่ sign ด้วย `S3_ENDPOINT` = http://minio:9000
    ซึ่งเป็นชื่อ service ภายใน docker network — เครื่องเล่นจริง (Raspberry Pi / Android TV /
    เบราว์เซอร์บน LAN) แปลชื่อ `minio` ไม่ออก → โหลดไฟล์ไม่ได้ → จอดำ

วิธีแก้ (2 โหมด):
    1. โหมด proxy (default, ไม่ต้องตั้งค่าอะไร) — manifest ส่ง URL ชี้กลับมาที่ backend เอง
       (`/api/v1/media?...`) โดยประกอบ host จาก request ที่เครื่องเล่นยิงเข้ามา
       → host นั้น "เครื่องเล่นเรียกถึงได้แน่นอน" เพราะเพิ่งเรียกสำเร็จมาหมาดๆ
    2. โหมด direct — ถ้าตั้ง `S3_PUBLIC_ENDPOINT` (เช่น http://192.168.1.10:9000 หรือ CDN)
       จะ sign URL ด้วย host นั้นให้ player โหลดจาก MinIO ตรงๆ (ลดภาระ backend)

ความปลอดภัย: URL แนบลายเซ็น HMAC-SHA256 ของ (key, เวลาหมดอายุ) — ระดับเดียวกับ pre-signed URL
เดิม (ใครถือลิงก์ก็โหลดได้จนกว่าจะหมดอายุ) จำเป็นต้องเป็นแบบนี้เพราะ <img>/<video> แนบ
Authorization header ไม่ได้
"""
import base64
import hashlib
import hmac
import time
from urllib.parse import urlencode

from fastapi import Request

from app.config import settings


def _sign(key: str, expires_at: int) -> str:
    """ลายเซ็นของ (storage key + เวลาหมดอายุ) — ผูกกับ secret ของ device token"""
    msg = f"{key}|{expires_at}".encode()
    digest = hmac.new(settings.device_token_secret.encode(), msg, hashlib.sha256).digest()
    return base64.urlsafe_b64encode(digest).decode().rstrip("=")[:43]


def _bucket_expiry(ttl: int, now: float | None = None) -> int:
    """
    เวลาหมดอายุแบบ "ปัดเป็นช่วง" ไม่ใช่ now+ttl ตรงๆ

    เหตุผล: manifest version คำนวณจาก hash ของ body ทั้งก้อน (รวม URL สื่อ) ถ้าลายเซ็น
    เปลี่ยนทุกครั้งที่สร้าง manifest → version เปลี่ยนทุก request → heartbeat จะตอบ
    manifest_outdated=True ตลอด เครื่องเล่นก็ดึงใหม่/เรนเดอร์ใหม่ไม่จบ
    ปัดเป็นช่วงแล้ว URL จะคงที่ตลอดช่วง (และเหลืออายุอย่างน้อย 1 ttl เสมอ)
    """
    n = int(now if now is not None else time.time())
    return (n // ttl + 2) * ttl


def public_media_base(request: Request) -> str:
    """
    URL ฐานของ endpoint สื่อ ที่เครื่องเล่น "เรียกถึงได้จริง"

    สร้างจาก request ที่วิ่งเข้ามา แล้วเคารพ X-Forwarded-* เผื่ออยู่หลัง nginx
    (nginx/signage.conf ส่ง X-Forwarded-Proto / X-Forwarded-Host ให้อยู่แล้ว)
    """
    url = request.url_for("get_media")
    proto = request.headers.get("x-forwarded-proto")
    host = request.headers.get("x-forwarded-host")
    if proto:
        url = url.replace(scheme=proto.split(",")[0].strip())
    if host:
        url = url.replace(netloc=host.split(",")[0].strip())
    return str(url)


def build_media_url(storage_key: str, media_base: str = "", ttl: int | None = None) -> str:
    """
    URL ของไฟล์สื่อที่จะใส่ลง manifest

    media_base = ผลจาก public_media_base(request); ถ้าไม่ส่งมา (เช่นถูกเรียกจาก worker
    ที่ไม่มี request) จะคืน path แบบ relative ให้ client ต่อกับ server URL ของตัวเอง
    """
    ttl = ttl or settings.media_url_ttl_sec
    if settings.s3_public_endpoint:
        # โหมด direct — sign ด้วย host สาธารณะ ให้ player คุย MinIO/CDN ตรงๆ
        from app.core.storage import presigned_get_url

        return presigned_get_url(storage_key, expires_in=ttl, public=True)

    expires_at = _bucket_expiry(ttl)
    query = urlencode({"k": storage_key, "e": expires_at, "s": _sign(storage_key, expires_at)})
    return f"{media_base or '/api/v1/media'}?{query}"


def verify_media_token(storage_key: str, expires_at: int, signature: str) -> bool:
    """ตรวจลายเซ็น + วันหมดอายุ (เทียบแบบ constant-time กัน timing attack)"""
    if expires_at < int(time.time()):
        return False
    return hmac.compare_digest(_sign(storage_key, expires_at), signature)
