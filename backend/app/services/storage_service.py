"""
Storage for private files (doctors' licences).

Development uses a local folder. Production uses any S3-compatible service
(Amazon S3, Cloudflare R2, Supabase Storage), chosen with STORAGE_BACKEND=s3.

Private files are never served by /static: the local folder is outside uploads/,
and they are only read through endpoints that check who is asking.
"""
import asyncio
import os
from functools import lru_cache
from pathlib import Path, PurePosixPath

from app.core.config import settings


def _check_key(key: str) -> str:
    """Keys are built by our own code, but must never be able to leave the storage folder."""
    path = PurePosixPath(key)
    if not key or path.is_absolute() or ".." in path.parts or "\\" in key:
        raise ValueError(f"Invalid storage key: {key}")
    return key


class LocalStorage:
    def __init__(self, root: str):
        self.root = Path(root)

    def _path(self, key: str) -> Path:
        return self.root / _check_key(key)

    async def save(self, key: str, data: bytes, content_type: str) -> str:
        path = self._path(key)
        path.parent.mkdir(parents=True, exist_ok=True)
        await asyncio.to_thread(path.write_bytes, data)
        return key

    async def read(self, key: str) -> bytes | None:
        path = self._path(key)
        if not path.is_file():
            return None
        return await asyncio.to_thread(path.read_bytes)

    async def delete(self, key: str) -> None:
        self._path(key).unlink(missing_ok=True)


class S3Storage:
    def __init__(self, client, bucket: str):
        self.client = client
        self.bucket = bucket

    async def save(self, key: str, data: bytes, content_type: str) -> str:
        await asyncio.to_thread(
            self.client.put_object,
            Bucket=self.bucket, Key=_check_key(key), Body=data, ContentType=content_type,
        )
        return key

    async def read(self, key: str) -> bytes | None:
        def _read():
            try:
                return self.client.get_object(Bucket=self.bucket, Key=_check_key(key))["Body"].read()
            except self.client.exceptions.NoSuchKey:
                return None
        return await asyncio.to_thread(_read)

    async def delete(self, key: str) -> None:
        await asyncio.to_thread(self.client.delete_object, Bucket=self.bucket, Key=_check_key(key))


@lru_cache
def get_private_storage() -> LocalStorage | S3Storage:
    if settings.storage_backend == "s3":
        import boto3  # Only needed when S3 storage is switched on

        if not settings.s3_bucket:
            raise RuntimeError("STORAGE_BACKEND=s3 requires S3_BUCKET")
        client = boto3.client(
            "s3",
            endpoint_url=settings.s3_endpoint_url or None,
            region_name=settings.s3_region or None,
            aws_access_key_id=settings.s3_access_key_id or None,
            aws_secret_access_key=settings.s3_secret_access_key or None,
        )
        return S3Storage(client, settings.s3_bucket)
    os.makedirs(settings.private_uploads_dir, exist_ok=True)
    return LocalStorage(settings.private_uploads_dir)
