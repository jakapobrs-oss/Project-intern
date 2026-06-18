"""
Content media processing tasks (§22 content pipeline)

- generate_thumbnail(content_id) — สร้างรูป preview 320x180 ให้ admin
    image → Pillow / video → ffmpeg ดึง frame ที่วินาทีที่ 1
- transcode_video(content_id) — ถ้า codec ไม่ใช่ H.264/AAC หรือไฟล์ใหญ่เกิน spec
    → แปลงเป็น MP4 (H.264 + AAC), downscale ≤ 1080p

worker download ไฟล์จาก S3 → process ใน temp dir → upload กลับ → update DB
ออกแบบ best-effort: process พังไม่ทำให้ content ใช้ไม่ได้ (แค่ไม่มี thumbnail/ไม่ transcode)
"""
from __future__ import annotations

import os
import subprocess
import tempfile
import uuid

from loguru import logger

from app.core import storage
from app.models.content import Content, ContentType
from app.workers.session import get_sessionmaker


# ===== Spec สำหรับตัดสินใจ transcode (§22) =====
TARGET_VIDEO_CODEC = "h264"
TARGET_AUDIO_CODEC = "aac"
MAX_HEIGHT = 1080
TRANSCODE_SIZE_THRESHOLD = 200 * 1024 * 1024  # > 200MB → ลองบีบ

THUMB_W, THUMB_H = 320, 180


# ---------- pure helper (unit-testable, ไม่แตะ I/O) ----------

def needs_transcode(
    video_codec: str | None,
    audio_codec: str | None,
    height: int | None,
    size_bytes: int | None,
) -> bool:
    """
    ตัดสินว่าต้อง transcode ไหม — pure function เพื่อ test ง่าย
    เงื่อนไข: codec ไม่ตรง spec, สูงเกิน 1080p, หรือไฟล์ใหญ่เกิน threshold
    """
    if video_codec is not None and video_codec.lower() != TARGET_VIDEO_CODEC:
        return True
    if audio_codec is not None and audio_codec.lower() != TARGET_AUDIO_CODEC:
        return True
    if height is not None and height > MAX_HEIGHT:
        return True
    if size_bytes is not None and size_bytes > TRANSCODE_SIZE_THRESHOLD:
        return True
    return False


def _ffprobe_streams(path: str) -> dict:
    """อ่าน codec/width/height/duration ผ่าน ffprobe (คืน dict ว่างถ้า ffprobe พัง)"""
    import json

    try:
        out = subprocess.run(
            ["ffprobe", "-v", "quiet", "-print_format", "json",
             "-show_streams", "-show_format", path],
            capture_output=True, text=True, timeout=60, check=True,
        )
        data = json.loads(out.stdout or "{}")
    except (subprocess.SubprocessError, OSError, ValueError) as e:
        logger.warning(f"ffprobe failed: {e}")
        return {}

    result: dict = {"duration": None, "width": None, "height": None,
                    "video_codec": None, "audio_codec": None}
    fmt = data.get("format", {})
    if fmt.get("duration"):
        try:
            result["duration"] = float(fmt["duration"])
        except (TypeError, ValueError):
            pass
    for s in data.get("streams", []):
        if s.get("codec_type") == "video" and result["video_codec"] is None:
            result["video_codec"] = s.get("codec_name")
            result["width"] = s.get("width")
            result["height"] = s.get("height")
        elif s.get("codec_type") == "audio" and result["audio_codec"] is None:
            result["audio_codec"] = s.get("codec_name")
    return result


# ---------- thumbnail ----------

def _make_image_thumbnail(src: str, dest: str) -> tuple[int | None, int | None]:
    """resize รูป → thumbnail JPEG, คืน (orig_w, orig_h)"""
    from PIL import Image

    with Image.open(src) as im:
        ow, oh = im.size
        im = im.convert("RGB")
        im.thumbnail((THUMB_W, THUMB_H))
        im.save(dest, "JPEG", quality=82)
    return ow, oh


def _make_video_thumbnail(src: str, dest: str) -> None:
    """ดึง frame ที่วินาทีที่ 1 ด้วย ffmpeg → JPEG"""
    subprocess.run(
        ["ffmpeg", "-y", "-ss", "1", "-i", src, "-vframes", "1",
         "-vf", f"scale={THUMB_W}:-1", dest],
        capture_output=True, timeout=120, check=True,
    )


async def generate_thumbnail_for(content: Content) -> bool:
    """
    download content → สร้าง thumbnail → upload → set content.thumbnail_key
    (caller commit เอง) คืน True ถ้าสำเร็จ
    """
    if not content.storage_key:
        return False
    tmpdir = tempfile.mkdtemp(prefix="thumb_")
    src = os.path.join(tmpdir, "src")
    dest = os.path.join(tmpdir, "thumb.jpg")
    try:
        storage.download_to_path(content.storage_key, src)
        if content.type == ContentType.IMAGE:
            ow, oh = _make_image_thumbnail(src, dest)
            content.width, content.height = ow, oh
        elif content.type == ContentType.VIDEO:
            probe = _ffprobe_streams(src)
            content.width = probe.get("width") or content.width
            content.height = probe.get("height") or content.height
            content.duration_sec = probe.get("duration") or content.duration_sec
            _make_video_thumbnail(src, dest)
        else:
            return False

        thumb_key = f"thumbnails/{content.sha256 or content.id}/thumb.jpg"
        storage.upload_path(dest, thumb_key, content_type="image/jpeg")
        content.thumbnail_key = thumb_key
        return True
    except Exception as e:  # noqa: BLE001 — best-effort
        logger.warning(f"generate_thumbnail failed content={content.id}: {e}")
        return False
    finally:
        _cleanup(tmpdir)


# ---------- transcode ----------

async def transcode_video_for(content: Content) -> bool:
    """probe → ถ้า needs_transcode → แปลง → upload key ใหม่ → update storage_key"""
    if not content.storage_key or content.type != ContentType.VIDEO:
        return False
    tmpdir = tempfile.mkdtemp(prefix="trans_")
    src = os.path.join(tmpdir, "src.mp4")
    out = os.path.join(tmpdir, "out.mp4")
    try:
        storage.download_to_path(content.storage_key, src)
        probe = _ffprobe_streams(src)
        if not needs_transcode(probe.get("video_codec"), probe.get("audio_codec"),
                               probe.get("height"), content.file_size):
            logger.info(f"transcode skip (already in spec) content={content.id}")
            return False

        subprocess.run(
            ["ffmpeg", "-y", "-i", src,
             "-c:v", "libx264", "-preset", "medium", "-crf", "23",
             "-vf", f"scale=-2:min({MAX_HEIGHT}\\,ih)",
             "-c:a", "aac", "-b:a", "128k", "-movflags", "+faststart", out],
            capture_output=True, timeout=1800, check=True,
        )
        new_key = f"contents/{content.sha256 or content.id}/transcoded.mp4"
        storage.upload_path(out, new_key, content_type="video/mp4")
        content.storage_key = new_key
        content.mime_type = "video/mp4"
        content.file_size = os.path.getsize(out)
        logger.info(f"transcoded content={content.id} → {new_key}")
        return True
    except Exception as e:  # noqa: BLE001 — best-effort
        logger.warning(f"transcode failed content={content.id}: {e}")
        return False
    finally:
        _cleanup(tmpdir)


def _cleanup(tmpdir: str) -> None:
    import shutil
    try:
        shutil.rmtree(tmpdir, ignore_errors=True)
    except OSError:
        pass


# ---------- Arq entrypoints ----------

async def _load(db, content_id: str) -> Content | None:
    return await db.get(Content, uuid.UUID(str(content_id)))


async def generate_thumbnail(ctx, content_id: str) -> bool:
    """Arq entry — สร้าง thumbnail แล้ว commit"""
    async with get_sessionmaker()() as db:
        content = await _load(db, content_id)
        if content is None:
            logger.warning(f"generate_thumbnail: content not found {content_id}")
            return False
        ok = await generate_thumbnail_for(content)
        if ok:
            await db.commit()
        return ok


async def transcode_video(ctx, content_id: str) -> bool:
    """Arq entry — transcode ถ้าจำเป็น แล้ว commit"""
    async with get_sessionmaker()() as db:
        content = await _load(db, content_id)
        if content is None:
            logger.warning(f"transcode_video: content not found {content_id}")
            return False
        ok = await transcode_video_for(content)
        if ok:
            await db.commit()
        return ok
