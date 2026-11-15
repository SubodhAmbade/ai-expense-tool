from io import BytesIO
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from PIL import Image, ImageDraw, ImageFont

from app.main import app
from app.store import get_store


class MemoryStore:
    """Stands in for Supabase: same methods, rows kept in a dict."""

    def __init__(self) -> None:
        self.rows: dict[str, dict] = {}

    def save(self, image: bytes, content_type: str, row: dict) -> dict:
        row = {**row, "id": str(uuid4()), "image_path": "x.png", "created_at": str(len(self.rows))}
        self.rows[row["id"]] = row
        return row

    def list(self, status: str | None) -> list[dict]:
        return [r for r in self.rows.values() if status in (None, r["status"])]

    def get(self, receipt_id: str) -> dict | None:
        return self.rows.get(receipt_id)

    def update(self, receipt_id: str, changes: dict) -> dict:
        self.rows[receipt_id].update(changes)
        return self.rows[receipt_id]

    def image_url(self, path: str) -> str:
        return f"https://signed.example/{path}"


@pytest.fixture
def client():
    store = MemoryStore()
    app.dependency_overrides[get_store] = lambda: store
    yield TestClient(app)
    app.dependency_overrides.clear()


def receipt_png(*lines: str) -> bytes:
    image = Image.new("RGB", (1000, 90 + 90 * len(lines)), "white")
    draw = ImageDraw.Draw(image)
    for i, line in enumerate(lines):
        draw.text((40, 40 + 90 * i), line, fill="black", font=ImageFont.load_default(size=44))
    buf = BytesIO()
    image.save(buf, format="PNG")
    return buf.getvalue()


def test_upload_review_confirm_export(client: TestClient) -> None:
    png = receipt_png(
        "SANYU STATIONERY SDN BHD", "Date: 25/12/2018", "SUBTOTAL 8.49", "GST 0.51", "TOTAL RM 9.00"
    )
    created = client.post("/receipts?profile=my", files={"file": ("r.png", png, "image/png")})
    assert created.status_code == 201
    row = created.json()
    assert (row["total_amount"], row["currency"], row["category"]) == (
        "9.00",
        "MYR",
        "office_supplies",
    )
    assert row["status"] == "confirmed", row["validation_errors"]  # every check agreed

    fetched = client.get(f"/receipts/{row['id']}").json()
    assert fetched["image_url"].startswith("https://")

    patched = client.patch(f"/receipts/{row['id']}", json={"category": "other"}).json()
    assert (patched["category"], patched["category_source"]) == ("other", "human")

    csv = client.get("/receipts/export.csv")
    assert csv.headers["content-type"].startswith("text/csv")
    assert "SANYU STATIONERY SDN BHD" in csv.text and "9.00" in csv.text


def test_unclear_receipt_goes_to_review(client: TestClient) -> None:
    png = receipt_png("ABC HO TRADING", "TOTAL 5.00")
    row = client.post("/receipts", files={"file": ("r.png", png, "image/png")}).json()
    assert row["status"] == "needs_review"
    assert any("category" in reason for reason in row["validation_errors"])
    assert [r["id"] for r in client.get("/receipts?status=needs_review").json()] == [row["id"]]


def test_rejects_bad_uploads_and_unknown_ids(client: TestClient) -> None:
    text = client.post("/receipts", files={"file": ("a.txt", b"hello", "text/plain")})
    huge = client.post(
        "/receipts", files={"file": ("b.png", b"0" * (10 * 1024 * 1024 + 1), "image/png")}
    )
    profile = client.post(
        "/receipts?profile=xx", files={"file": ("c.png", receipt_png("A"), "image/png")}
    )
    assert (text.status_code, huge.status_code, profile.status_code) == (415, 413, 422)
    assert client.get(f"/receipts/{uuid4()}").status_code == 404
    assert client.patch(f"/receipts/{uuid4()}", json={}).status_code == 404


def test_export_neutralises_spreadsheet_formulas(client: TestClient) -> None:
    store = app.dependency_overrides[get_store]()
    store.rows["1"] = {"id": "1", "status": "confirmed", "merchant": "=HYPERLINK(evil)"}
    store.rows["2"] = {"id": "2", "status": "confirmed", "merchant": "", "total_amount": "-5.00"}
    text = client.get("/receipts/export.csv").text
    assert "'=HYPERLINK(evil)" in text
    assert "-5.00" in text and "'-5.00" not in text  # refunds stay numbers
