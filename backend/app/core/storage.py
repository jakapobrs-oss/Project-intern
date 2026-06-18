"""
S3/MinIO storage helper — wrap boto3
ใช้ stream upload/download (memory-efficient)
"""
import hashlib
from typing import BinaryIO
import boto3
from botocore.client import Config
from botocore.exceptions import ClientError

from app.config import settings


def get_s3_client():
    """boto3 client ที่ชี้ไป MinIO/S3"""
    return boto3.client(
        "s3",
        endpoint_url=settings.s3_endpoint,
        aws_access_key_id=settings.s3_access_key,
        aws_secret_access_key=settings.s3_secret_key,
        region_name=settings.s3_region,
        config=Config(signature_version="s3v4"),
    )


def ensure_bucket(bucket: str | None = None) -> None:
    """สร้าง bucket ถ้ายังไม่มี (idempotent)"""
    bucket = bucket or settings.s3_bucket
    s3 = get_s3_client()
    try:
        s3.head_bucket(Bucket=bucket)
    except ClientError as e:
        code = e.response.get("Error", {}).get("Code")
        if code in ("404", "NoSuchBucket"):
            s3.create_bucket(Bucket=bucket)
        else:
            raise


def upload_fileobj(
    file: BinaryIO,
    key: str,
    content_type: str | None = None,
    bucket: str | None = None,
) -> None:
    """อัปโหลดจาก file-like object"""
    bucket = bucket or settings.s3_bucket
    extra = {"ContentType": content_type} if content_type else {}
    get_s3_client().upload_fileobj(file, bucket, key, ExtraArgs=extra)


def delete_object(key: str, bucket: str | None = None) -> None:
    bucket = bucket or settings.s3_bucket
    get_s3_client().delete_object(Bucket=bucket, Key=key)


def download_to_path(key: str, dest_path: str, bucket: str | None = None) -> None:
    """ดาวน์โหลด object จาก S3 ลงไฟล์ใน local (ใช้ใน worker transcode/thumbnail)"""
    bucket = bucket or settings.s3_bucket
    get_s3_client().download_file(bucket, key, dest_path)


def upload_path(local_path: str, key: str, content_type: str | None = None, bucket: str | None = None) -> None:
    """อัปโหลดไฟล์จาก local path ขึ้น S3 (ใช้หลัง worker สร้าง thumbnail/transcoded เสร็จ)"""
    bucket = bucket or settings.s3_bucket
    extra = {"ContentType": content_type} if content_type else {}
    get_s3_client().upload_file(local_path, bucket, key, ExtraArgs=extra)


def presigned_get_url(key: str, expires_in: int = 3600, bucket: str | None = None) -> str:
    """สร้าง pre-signed URL ให้ player ใช้ download (§22 signed URL)"""
    bucket = bucket or settings.s3_bucket
    return get_s3_client().generate_presigned_url(
        "get_object",
        Params={"Bucket": bucket, "Key": key},
        ExpiresIn=expires_in,
    )


# ===== utility: hash file streaming =====

def sha256_stream(file: BinaryIO, chunk_size: int = 65536) -> tuple[str, int]:
    """
    คำนวณ SHA-256 + ขนาดไฟล์ โดยอ่านเป็น chunk (ไม่ load ทั้งไฟล์เข้า memory)
    คืน (hex_digest, size_bytes) — ตำแหน่ง pointer จะอยู่ท้ายไฟล์ — caller ต้อง seek(0)
    """
    h = hashlib.sha256()
    size = 0
    while True:
        chunk = file.read(chunk_size)
        if not chunk:
            break
        h.update(chunk)
        size += len(chunk)
    return h.hexdigest(), size
