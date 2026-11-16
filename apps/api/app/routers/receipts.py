import csv
from datetime import UTC, date, datetime
from decimal import Decimal
from functools import lru_cache
from io import BytesIO, StringIO
from typing import Annotated, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Response, UploadFile
from PIL import Image, UnidentifiedImageError
from pydantic import BaseModel, Field, field_validator

from app.auth import UserDep
from app.categorise import CATEGORIES
from app.config import get_settings
from app.pipeline import process
from app.store import Store, get_store
from app.tax_profiles import load_tax_profiles

router = APIRouter(prefix="/receipts", tags=["receipts"])
StoreDep = Annotated[Store, Depends(get_store)]
MAX_BYTES = 10 * 1024 * 1024  # 10 MB, plenty for a phone photo
FORMATS = {"JPEG": "image/jpeg", "PNG": "image/png", "WEBP": "image/webp"}  # what Pillow detects
# Largest image to decode, in pixels. 10 MB of PNG can hold a huge image (it compresses well), and
# only JPEG can be decoded at a reduced size, so PNG and WebP get less. Measured with
# eval/memory_check.py, whole API: a 50 MP progressive JPEG (the hungriest kind) peaks at 415 MB
# (60 MP: 443 MB), a 20 MP PNG with transparency at 401 MB (40 MP: 569 MB, over a 512 MB server).
MAX_PIXELS = {"JPEG": 50_000_000, "PNG": 20_000_000, "WEBP": 20_000_000}
CSV_COLUMNS = ["id", "receipt_date", "merchant", "category", "currency"]
CSV_COLUMNS += ["net_amount", "tax_amount", "total_amount"]


@lru_cache
def _profiles():
    return load_tax_profiles(get_settings().tax_profiles_path)


class ReceiptUpdate(BaseModel):
    """What a reviewer can correct. Saving confirms the receipt."""

    merchant: str | None = None
    receipt_date: date | None = None
    currency: str | None = Field(None, pattern="^[A-Z]{3}$")
    net_amount: Decimal | None = None
    tax_amount: Decimal | None = None
    total_amount: Decimal | None = None
    category: Literal[tuple(CATEGORIES)] | None = None  # type: ignore[valid-type]

    @field_validator("category")
    @classmethod
    def category_not_cleared(cls, v: str | None) -> str:
        if v is None:
            raise ValueError("a confirmed receipt needs a category; use 'other' if none fits")
        return v


@router.post("", status_code=201)
def upload(file: UploadFile, store: StoreDep, user: UserDep, profile: str | None = None) -> dict:
    image = file.file.read(MAX_BYTES + 1)
    if len(image) > MAX_BYTES:
        raise HTTPException(413, "Image is larger than 10 MB")
    # Trust the bytes, not the browser's label: check what the file really is.
    try:
        with Image.open(BytesIO(image)) as img:
            detected, pixels = (
                img.format,
                img.width * img.height,
            )  # read from the header, not decoded
            img.verify()
    except (UnidentifiedImageError, OSError, SyntaxError, Image.DecompressionBombError):
        # SyntaxError: Pillow's signal for a damaged PNG chunk, e.g. a bad checksum
        raise HTTPException(422, "That file isn't a readable image") from None
    if detected not in FORMATS:
        raise HTTPException(415, f"Upload a JPEG, PNG or WebP image, not {detected}")
    if pixels > MAX_PIXELS[detected]:
        limit = MAX_PIXELS[detected] // 1_000_000
        raise HTTPException(
            413, f"Image is too large ({pixels // 1_000_000} MP); the limit is {limit} MP"
        )
    code = profile or get_settings().default_profile
    if code not in _profiles():
        raise HTTPException(422, f"Unknown profile '{code}'; known: {', '.join(_profiles())}")
    try:
        row = process(image, _profiles()[code])
    except (UnidentifiedImageError, OSError):  # damaged data that only fails on a full decode
        raise HTTPException(422, "That file isn't a readable image") from None
    return store.save(user, image, FORMATS[detected], row)


@router.get("")
def list_receipts(
    store: StoreDep, user: UserDep, status: Literal["needs_review", "confirmed"] | None = None
) -> list[dict]:
    return store.list(user, status)


@router.get("/export.csv")  # declared before /{receipt_id} so the path isn't read as an id
def export_csv(store: StoreDep, user: UserDep) -> Response:
    out = StringIO()
    writer = csv.DictWriter(out, CSV_COLUMNS, extrasaction="ignore")
    writer.writeheader()
    for row in store.list(user, "confirmed"):
        merchant = row.get("merchant") or ""
        if merchant[:1] in (
            "=",
            "+",
            "-",
            "@",
            "\t",
            "\r",
        ):  # spreadsheets could run it as a formula
            merchant = f"'{merchant}"
        writer.writerow({**row, "merchant": merchant})
    headers = {"Content-Disposition": 'attachment; filename="receipts.csv"'}
    return Response(out.getvalue(), media_type="text/csv", headers=headers)


@router.get("/{receipt_id}")
def get_receipt(receipt_id: UUID, store: StoreDep, user: UserDep) -> dict:
    row = store.get(user, str(receipt_id))
    if row is None:  # also someone else's receipt: don't reveal that it exists
        raise HTTPException(404, "Receipt not found")
    return {**row, "image_url": store.image_url(row["image_path"])}


@router.patch("/{receipt_id}")
def confirm(receipt_id: UUID, update: ReceiptUpdate, store: StoreDep, user: UserDep) -> dict:
    row = store.get(user, str(receipt_id))
    if row is None:
        raise HTTPException(404, "Receipt not found")
    changes = update.model_dump(mode="json", exclude_unset=True)
    if changes.get("category", row["category"]) is None:  # what the receipt ends up with
        raise HTTPException(422, "A confirmed receipt needs a category; use 'other' if none fits")
    if changes.get("category", row["category"]) != row["category"]:
        changes["category_source"] = "human"
    now = datetime.now(UTC).isoformat()
    changes |= {"status": "confirmed", "confirmed_at": now, "updated_at": now}
    return store.update(user, str(receipt_id), changes)
