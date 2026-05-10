"""
Supabase Storage via el SDK oficial de Python.
"""

from core.supabase_client import get_supabase

BUCKET = "prescriptions"


async def ensure_bucket_exists() -> None:
    client = get_supabase()
    try:
        await client.storage.create_bucket(BUCKET, options={"public": False})
    except Exception as e:
        if "already exists" not in str(e).lower():
            print(f"[storage] bucket check warning: {e}")


async def upload_prescription(
    user_id: str, filename: str, file_bytes: bytes, content_type: str
) -> str:
    client = get_supabase()
    path = f"{user_id}/{filename}"
    await client.storage.from_(BUCKET).upload(
        path=path,
        file=file_bytes,
        file_options={"content-type": content_type, "upsert": "true"},
    )
    return path


async def get_prescription_url(storage_path: str, expires_in: int = 3600) -> str:
    client = get_supabase()
    res = await client.storage.from_(BUCKET).create_signed_url(storage_path, expires_in)
    return res["signedURL"]
