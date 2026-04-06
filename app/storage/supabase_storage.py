from __future__ import annotations

from functools import lru_cache

from supabase import Client, create_client

from app.config import settings


@lru_cache
def _service_client() -> Client:
    if not settings.supabase_url or not settings.supabase_service_role_key:
        raise RuntimeError("supabase_url and supabase_service_role_key must be configured")
    return create_client(settings.supabase_url, settings.supabase_service_role_key)


def upload_file(bucket: str, path: str, data: bytes, content_type: str) -> str:
    client = _service_client()
    client.storage.from_(bucket).upload(
        path,
        data,
        file_options={"content-type": content_type, "upsert": "true"},
    )
    return client.storage.from_(bucket).get_public_url(path)


def download_file(bucket: str, path: str) -> bytes:
    client = _service_client()
    raw = client.storage.from_(bucket).download(path)
    if isinstance(raw, bytes):
        return raw
    if isinstance(raw, memoryview):
        return raw.tobytes()
    return bytes(raw)


def delete_file(bucket: str, path: str) -> bool:
    client = _service_client()
    client.storage.from_(bucket).remove([path])
    return True


def create_signed_upload_url(bucket: str, path: str) -> str:
    client = _service_client()
    sb = client.storage.from_(bucket)
    res = sb.create_signed_upload_url(path)
    if isinstance(res, dict):
        for key in ("signed_url", "signedUrl", "url"):
            v = res.get(key)
            if isinstance(v, str) and v:
                return v
        return str(res)
    if isinstance(res, str):
        return res
    signed = getattr(res, "signed_url", None) or getattr(res, "signedUrl", None)
    if isinstance(signed, str) and signed:
        return signed
    return str(res)
