"""Storage: the receipts table and the private photo bucket in Supabase. Server-side only."""

from functools import lru_cache
from uuid import uuid4

from supabase import Client, create_client

from app.config import get_settings

BUCKET = "receipts"
LIST_COLUMNS = (
    "id, created_at, confirmed_at, status, merchant, receipt_date, currency, "
    "net_amount, tax_amount, total_amount, category, validation_errors"
)
EXTENSIONS = {"image/jpeg": ".jpg", "image/png": ".png", "image/webp": ".webp"}
PAGE = 1000  # Supabase returns at most this many rows per request


@lru_cache
def _client() -> Client:
    settings = get_settings()
    if not settings.supabase_url or not settings.supabase_service_role_key:
        raise RuntimeError("Set SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY in apps/api/.env")
    return create_client(settings.supabase_url, settings.supabase_service_role_key)


class Store:
    """Every method takes the signed-in user's id, and only ever touches that user's rows."""

    def save(self, user_id: str, image: bytes, content_type: str, row: dict) -> dict:
        path = f"{user_id}/{uuid4()}{EXTENSIONS[content_type]}"  # each user's photos in one folder
        _client().storage.from_(BUCKET).upload(path, image, {"content-type": content_type})
        # If the insert fails, the photo is deliberately left in place: an interrupted insert can
        # still commit afterwards, so deleting now could leave a receipt pointing at nothing. A
        # stray photo is harmless; a later sweep can remove photos no receipt references.
        row = {**row, "user_id": user_id, "image_path": path}
        return _client().table("receipts").insert(row).execute().data[0]

    def list(self, user_id: str, status: str | None) -> list[dict]:
        rows: list[dict] = []
        # Page through oldest first, so the list and the CSV export never stop at PAGE rows. New
        # uploads land at the end, so earlier pages can't shift and repeat a row; id breaks ties.
        while True:
            query = _client().table("receipts").select(LIST_COLUMNS).eq("user_id", user_id)
            query = query.order("created_at").order("id")
            query = query.eq("status", status) if status else query
            batch = query.range(len(rows), len(rows) + PAGE - 1).execute().data
            rows += batch
            if len(batch) < PAGE:
                return rows[::-1]  # newest first

    def get(self, user_id: str, receipt_id: str) -> dict | None:
        query = _client().table("receipts").select("*").eq("id", receipt_id)
        rows = query.eq("user_id", user_id).execute().data
        return rows[0] if rows else None

    def update(self, user_id: str, receipt_id: str, changes: dict) -> dict:
        query = _client().table("receipts").update(changes).eq("id", receipt_id)
        return query.eq("user_id", user_id).execute().data[0]

    def image_url(self, path: str) -> str:
        return _client().storage.from_(BUCKET).create_signed_url(path, 600)["signedUrl"]  # 10 min


def get_store() -> Store:
    return Store()
