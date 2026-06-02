"""File storage abstraction for uploaded drawings and generated artifacts."""
from __future__ import annotations

import hashlib
import os
import pathlib
from dataclasses import dataclass

from utils.db import safe_execute
from utils.settings import get_setting


@dataclass(frozen=True)
class StoredFile:
    provider: str
    key: str
    checksum_sha256: str
    size_bytes: int


def _checksum(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def save_file(
    user_id: int,
    original_name: str,
    data: bytes,
    content_type: str = "application/octet-stream",
    project_id: int | None = None,
) -> StoredFile:
    provider = get_setting("STORAGE_PROVIDER", "local").lower()
    checksum = _checksum(data)
    ext = pathlib.Path(original_name).suffix.lower()
    key = f"users/{user_id}/{checksum}{ext}"

    if provider == "s3":
        import boto3

        bucket = get_setting("S3_BUCKET", required=True)
        client_kwargs = {}
        endpoint = get_setting("S3_ENDPOINT_URL")
        if endpoint:
            client_kwargs["endpoint_url"] = endpoint
        region = get_setting("S3_REGION")
        if region:
            client_kwargs["region_name"] = region
        s3 = boto3.client("s3", **client_kwargs)
        s3.put_object(Bucket=bucket, Key=key, Body=data, ContentType=content_type)
    else:
        provider = "local"
        root = pathlib.Path(get_setting("LOCAL_STORAGE_DIR", ".qto_storage"))
        path = root / key
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)

    safe_execute(
        """
        INSERT INTO qto_files
            (user_id, project_id, original_name, storage_provider, storage_key,
             content_type, size_bytes, checksum_sha256)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """,
        (user_id, project_id, original_name, provider, key, content_type, len(data), checksum),
    )
    return StoredFile(provider, key, checksum, len(data))
