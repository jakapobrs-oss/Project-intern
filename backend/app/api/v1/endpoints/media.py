"""
Media endpoint — ส่งไฟล์สื่อให้เครื่องเล่น (§22)

ทำไมต้องมี: <img>/<video> ในเครื่องเล่นแนบ Authorization header ไม่ได้ และ URL ของ MinIO
ที่ sign ด้วยชื่อ service ในdocker (http://minio:9000) เครื่องเล่นข้างนอกเรียกไม่ถึง
→ ให้ backend เป็นคนส่งไฟล์แทน โดยตรวจสิทธิ์จาก "ลายเซ็นในลิงก์" (ดู core/media_link.py)

รองรับ Range request เพื่อให้วิดีโอเลื่อนเวลา/เล่นต่อได้
"""
from botocore.exceptions import ClientError
from fastapi import APIRouter, HTTPException, Query, Request, status
from fastapi.responses import StreamingResponse
from starlette.concurrency import iterate_in_threadpool, run_in_threadpool

from app.config import settings
from app.core import storage
from app.core.media_link import verify_media_token

router = APIRouter()

CHUNK_SIZE = 64 * 1024


def _stream(body):
    """อ่าน StreamingBody ของ boto3 เป็น chunk (ไม่โหลดทั้งไฟล์เข้า memory)"""
    try:
        while True:
            chunk = body.read(CHUNK_SIZE)
            if not chunk:
                break
            yield chunk
    finally:
        body.close()


@router.get("/media", name="get_media")
async def get_media(
    request: Request,
    k: str = Query(..., description="storage key ของไฟล์"),
    e: int = Query(..., description="เวลาหมดอายุของลิงก์ (unix time)"),
    s: str = Query(..., description="ลายเซ็น HMAC ของ (k, e)"),
):
    """ส่งไฟล์สื่อตามลิงก์ที่ backend เซ็นไว้ใน manifest — ลิงก์ผิด/หมดอายุ = 403"""
    if not verify_media_token(k, e, s):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "ลิงก์สื่อไม่ถูกต้องหรือหมดอายุ")

    byte_range = request.headers.get("range")
    try:
        # boto3 เป็น blocking → โยนลง threadpool ไม่ให้บล็อก event loop
        obj = await run_in_threadpool(storage.get_object, k, byte_range)
    except ClientError as exc:
        code = exc.response.get("Error", {}).get("Code")
        if code in ("NoSuchKey", "404", "InvalidRange"):
            raise HTTPException(status.HTTP_404_NOT_FOUND, "ไม่พบไฟล์สื่อ") from exc
        raise

    headers = {
        "Accept-Ranges": "bytes",
        # ลิงก์มีอายุจำกัดอยู่แล้ว ให้เครื่องเล่น cache ได้ตลอดอายุลิงก์ (ลดโหลดตอนวนเล่นซ้ำ)
        "Cache-Control": f"private, max-age={settings.media_url_ttl_sec}",
    }
    # บอก cache ให้แยกรายการตาม Origin — ถ้าไม่ใส่ เคสนี้จะพัง: <img> โหลดก่อน (ไม่ส่ง Origin
    # → คำตอบไม่มี CORS header) แล้วถูกเก็บ cache ไว้ พอ preCacheMedia ยิง fetch(mode:'cors')
    # มาใช้ของเดิมใน cache เบราว์เซอร์จะฟ้อง "No 'Access-Control-Allow-Origin' header"
    # (ถ้ามี Origin เข้ามา CORSMiddleware จะเติม Vary ให้เองอยู่แล้ว)
    if "origin" not in request.headers:
        headers["Vary"] = "Origin"
    if obj.get("ContentLength") is not None:
        headers["Content-Length"] = str(obj["ContentLength"])
    if obj.get("ContentRange"):
        headers["Content-Range"] = obj["ContentRange"]

    return StreamingResponse(
        iterate_in_threadpool(_stream(obj["Body"])),
        status_code=status.HTTP_206_PARTIAL_CONTENT if obj.get("ContentRange") else status.HTTP_200_OK,
        media_type=obj.get("ContentType") or "application/octet-stream",
        headers=headers,
    )
