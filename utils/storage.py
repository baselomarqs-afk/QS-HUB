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


def save_raw_image_to_cache(project_id: int, filename: str, data: bytes, format: str = "PNG") -> str:
    """
    Saves raw image bytes directly to cache without PIL overhead.
    """
    provider = get_setting("STORAGE_PROVIDER", "local").lower()
    key = f"cache/{project_id}/{filename}"
    
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
        content_type = "image/png" if format.upper() == "PNG" else "image/jpeg"
        s3.put_object(Bucket=bucket, Key=key, Body=data, ContentType=content_type)
        return f"s3://{bucket}/{key}"
    else:
        root = pathlib.Path(get_setting("LOCAL_STORAGE_DIR", ".qto_storage")).parent / "_qto_cache"
        path = root / str(project_id) / filename
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
        return f"/cache/{project_id}/{filename}"


def save_image_to_cache(project_id: int, filename: str, pil_img, format: str = "PNG") -> str:
    """
    Saves an image either to the local ephemeral cache or directly to S3.
    Returns the URL or path for retrieval.
    """
    import io
    
    provider = get_setting("STORAGE_PROVIDER", "local").lower()
    key = f"cache/{project_id}/{filename}"
    
    # Save to memory buffer
    buf = io.BytesIO()
    pil_img.save(buf, format=format)
    data = buf.getvalue()
    
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
        content_type = "image/png" if format.upper() == "PNG" else "image/jpeg"
        s3.put_object(Bucket=bucket, Key=key, Body=data, ContentType=content_type)
        return f"s3://{bucket}/{key}"
    else:
        root = pathlib.Path(get_setting("LOCAL_STORAGE_DIR", ".qto_storage")).parent / "_qto_cache"
        path = root / str(project_id) / filename
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
        return f"/cache/{project_id}/{filename}"


def get_image_url(path_or_uri: str) -> str:
    """
    Given a local path or s3 URI, returns a URL accessible by the frontend.
    For S3, it generates a presigned URL.
    """
    if not path_or_uri.startswith("s3://"):
        return path_or_uri # It's a local /cache/ route
        
    try:
        import boto3
        parts = path_or_uri.replace("s3://", "").split("/", 1)
        if len(parts) != 2:
            return path_or_uri
            
        bucket, key = parts
        client_kwargs = {}
        endpoint = get_setting("S3_ENDPOINT_URL")
        if endpoint:
            client_kwargs["endpoint_url"] = endpoint
        region = get_setting("S3_REGION")
        if region:
            client_kwargs["region_name"] = region
            
        s3 = boto3.client("s3", **client_kwargs)
        url = s3.generate_presigned_url(
            'get_object',
            Params={'Bucket': bucket, 'Key': key},
            ExpiresIn=3600 # 1 hour
        )
        return url
    except Exception as e:
        print(f"Error generating presigned URL: {e}")
        return path_or_uri
