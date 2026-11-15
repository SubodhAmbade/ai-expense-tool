"""Storage: the receipts table and the private photo bucket in Supabase. Server-side only."""

from functools import lru_cache
from uuid import uuid4

from supabase import Client, create_client

from app.config import get_settings

BUCKET = "receipts"
LIST_COLUMNS = (
    "id, created_at, status, merchant, receipt_date, currency, "
    "net_amount, tax_amount, total_amount, category, validation_errors"
)
EXTENSIONS = {"image/jpeg": ".jpg", "image/png": ".png", "image/webp": ".webp"}


@lru_cache
def _client() -> Client:
    settings = get_settings()
    if not settings.supabase_url or not settings.supabase_service_role_key:
        raise RuntimeError("Set SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY in apps/api/.env")
    return create_client(settings.supabase_url, settings.supabase_service_role_key)


class Store:
    def save(self, image: bytes, content_type: str, row: dict) -> dict:
        path = f"{uuid4()}{EXTENSIONS[content_type]}"
        _client().storage.from_(BUCKET).upload(path, image, {"content-type": content_type})
        return _client().table("receipts").insert({**row, "image_path": path}).execute().data[0]

    def list(self, status: str | None) -> list[dict]:
        query = _client().table("receipts").select(LIST_COLUMNS).order("created_at", desc=True)
        return (query.eq("status", status) if status else query).execute().data

    def get(self, receipt_id: str) -> dict | None:
        rows = _client().table("receipts").select("*").eq("id", receipt_id).execute().data
        return rows[0] if rows else None

    def update(self, receipt_id: str, changes: dict) -> dict:
        return _client().table("receipts").update(changes).eq("id", receipt_id).execute().data[0]

    def image_url(self, path: str) -> str:
        return _client().storage.from_(BUCKET).create_signed_url(path, 600)["signedUrl"]  # 10 min


def get_store() -> Store:
    return Store()
