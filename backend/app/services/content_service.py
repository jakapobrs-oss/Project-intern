"""
Content service — upload pipeline (§22)
- Validate magic bytes (ตรวจจากเนื้อไฟล์จริง ไม่ใช่ extension)
- SHA-256 dedupe (ถ้า hash ซ้ำ → return content เดิม)
- Upload ไป S3/MinIO ด้วย key format: contents/{sha256}/{filename}
"""
import uuid
from typing import BinaryIO
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.storage import upload_fileobj, sha256_stream, ensure_bucket
from app.models.content import Content, ContentType


# Magic bytes — ส่วนต้นของไฟล์ที่บ่งบอก type จริง (§22)
# format: (magic_bytes, mime_type, content_type)
_MAGIC_SIGNATURES = [
    # Image
    (b"\xFF\xD8\xFF", "image/jpeg", ContentType.IMAGE),
    (b"\x89PNG\r\n\x1a\n", "image/png", ContentType.IMAGE),
    (b"RIFF", "image/webp", ContentType.IMAGE),  # RIFF...WEBP
    (b"GIF87a", "image/gif", ContentType.IMAGE),
    (b"GIF89a", "image/gif", ContentType.IMAGE),
    # Video
    (b"\x00\x00\x00\x18ftypmp4", "video/mp4", ContentType.VIDEO),
    (b"\x00\x00\x00\x1cftypmp4", "video/mp4", ContentType.VIDEO),
    (b"\x00\x00\x00\x20ftyp", "video/mp4", ContentType.VIDEO),
    (b"\x1a\x45\xdf\xa3", "video/webm", ContentType.VIDEO),  # EBML — WebM/MKV
]

# Max file size per type (bytes) — ดู §22
MAX_SIZE = {
    ContentType.IMAGE: 20 * 1024 * 1024,   # 20 MB
    ContentType.VIDEO: 500 * 1024 * 1024,  # 500 MB
}


class ContentServiceError(Exception):
    def __init__(self, code: str, message: str):
        self.code = code
        self.message = message
        super().__init__(message)


def detect_mime_from_magic(head: bytes) -> tuple[str | None, ContentType | None]:
    """ตรวจ mime + content type จาก magic bytes (อ่านส่วนต้นไฟล์)"""
    for magic, mime, ctype in _MAGIC_SIGNATURES:
        if head.startswith(magic):
            return mime, ctype
    # Special: WebP มี "RIFF????WEBP"
    if head.startswith(b"RIFF") and len(head) >= 12 and head[8:12] == b"WEBP":
        return "image/webp", ContentType.IMAGE
    # Special: MP4 ftyp อยู่ที่ offset 4
    if len(head) >= 12 and head[4:8] == b"ftyp":
        return "video/mp4", ContentType.VIDEO
    return None, None


async def upload_content_file(
    db: AsyncSession,
    *,
    file: BinaryIO,
    filename: str,
    name: str,
    description: str,
    created_by: uuid.UUID,
) -> Content:
    """
    Pipeline:
      1. อ่าน head 64 bytes → detect type
      2. คำนวณ SHA-256 + size (streaming)
      3. dedupe — ถ้า hash ซ้ำ คืน content เดิม
      4. validate size
      5. upload ไป S3 key = contents/{hash}/{filename}
      6. INSERT row ใน DB
    """
    # 1. magic bytes
    head = file.read(64)
    mime, ctype = detect_mime_from_magic(head)
    if not ctype:
        raise ContentServiceError("UNSUPPORTED_TYPE", "ไม่รองรับ format ของไฟล์นี้ (magic bytes ไม่ match)")

    # 2. SHA-256 — กลับไปต้นไฟล์ก่อน
    file.seek(0)
    digest, size = sha256_stream(file)

    # 3. dedupe
    res = await db.execute(select(Content).where(Content.sha256 == digest))
    existing = res.scalar_one_or_none()
    if existing:
        return existing

    # 4. size limit
    limit = MAX_SIZE.get(ctype)
    if limit and size > limit:
        raise ContentServiceError(
            "FILE_TOO_LARGE",
            f"ไฟล์ขนาด {size} เกินขีดจำกัด {limit} bytes สำหรับ {ctype.value}",
        )

    # 5. upload
    file.seek(0)
    safe_filename = filename.replace("/", "_").replace("\\", "_")[:200]
    key = f"contents/{digest[:2]}/{digest}/{safe_filename}"
    ensure_bucket()
    upload_fileobj(file, key, content_type=mime)

    # 6. DB
    content = Content(
        name=name,
        description=description,
        type=ctype,
        storage_key=key,
        mime_type=mime,
        file_size=size,
        sha256=digest,
        created_by=created_by,
    )
    db.add(content)
    await db.commit()
    await db.refresh(content)
    return content
