from io import BytesIO
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from PIL import Image, ImageDraw, ImageFont

import app.routers.receipts as receipts_router
from app.auth import current_user
from app.main import app
from app.store import get_store


class MemoryStore:
    """Stands in for Supabase: same methods, rows kept in a dict, each owned by a user."""

    def __init__(self) -> None:
        self.rows: dict[str, dict] = {}

    def save(self, user_id: str, image: bytes, content_type: str, row: dict) -> dict:
        n = str(len(self.rows))
        row = {
            **row,
            "id": str(uuid4()),
            "user_id": user_id,
            "image_path": "x.png",
            "created_at": n,
        }
        self.rows[row["id"]] = row
        return row

    def list(self, user_id: str, status: str | None) -> list[dict]:
        rows = self.rows.values()
        return [r for r in rows if r["user_id"] == user_id and status in (None, r["status"])]

    def get(self, user_id: str, receipt_id: str) -> dict | None:
        row = self.rows.get(receipt_id)
        return row if row and row["user_id"] == user_id else None

    def update(self, user_id: str, receipt_id: str, changes: dict) -> dict:
        assert self.rows[receipt_id]["user_id"] == user_id
        self.rows[receipt_id].update(changes)
        return self.rows[receipt_id]

    def image_url(self, path: str) -> str:
        return f"https://signed.example/{path}"


SIGNED_IN = {"user": "user-a"}  # who the fake sign-in says is asking; tests can switch it


@pytest.fixture
def client():
    store = MemoryStore()
    SIGNED_IN["user"] = "user-a"
    app.dependency_overrides[get_store] = lambda: store
    app.dependency_overrides[current_user] = lambda: SIGNED_IN["user"]
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

    note = "Client lunch, GST added by hand"
    patched = client.patch(f"/receipts/{row['id']}", json={"category": "other", "note": note})
    assert (patched.json()["category"], patched.json()["category_source"]) == ("other", "human")
    assert client.get(f"/receipts/{row['id']}").json()["note"] == note
    too_long = client.patch(f"/receipts/{row['id']}", json={"note": "x" * 501})
    assert too_long.status_code == 422

    csv = client.get("/receipts/export.csv")
    assert csv.headers["content-type"].startswith("text/csv")
    assert "SANYU STATIONERY SDN BHD" in csv.text and "9.00" in csv.text and note in csv.text


def test_unclear_receipt_goes_to_review(client: TestClient) -> None:
    png = receipt_png("ABC HO TRADING", "TOTAL 5.00")
    row = client.post("/receipts", files={"file": ("r.png", png, "image/png")}).json()
    assert row["status"] == "needs_review"
    assert any("category" in reason for reason in row["validation_errors"])
    assert [r["id"] for r in client.get("/receipts?status=needs_review").json()] == [row["id"]]


def test_rejects_bad_uploads_and_unknown_ids(client: TestClient) -> None:
    def post(name: str, data: bytes, content_type: str = "image/png", query: str = ""):
        return client.post(f"/receipts{query}", files={"file": (name, data, content_type)})

    gif = BytesIO()
    Image.new("RGB", (10, 10)).save(gif, format="GIF")
    png = receipt_png("A")
    assert post("a.txt", b"hello", "text/plain").status_code == 422  # not an image at all
    assert post("b.png", b"hello").status_code == 422  # labelled PNG, isn't one
    assert post("c.png", png[: len(png) // 2]).status_code == 422  # cut off halfway
    bad_checksum = bytearray(png)
    idat = bad_checksum.find(b"IDAT")
    bad_checksum[idat + 4 + int.from_bytes(bad_checksum[idat - 4 : idat], "big")] ^= 0xFF
    assert post("g.png", bytes(bad_checksum)).status_code == 422  # damaged PNG checksum
    assert post("d.gif", gif.getvalue(), "image/gif").status_code == 415  # real image, wrong format
    assert post("e.png", b"0" * (10 * 1024 * 1024 + 1)).status_code == 413
    assert post("f.png", png, query="?profile=xx").status_code == 422
    assert client.get(f"/receipts/{uuid4()}").status_code == 404
    assert client.patch(f"/receipts/{uuid4()}", json={}).status_code == 404


def test_category_cannot_be_cleared(client: TestClient) -> None:
    png = receipt_png("ABC HO TRADING", "TOTAL 5.00")
    row = client.post("/receipts", files={"file": ("r.png", png, "image/png")}).json()
    assert client.patch(f"/receipts/{row['id']}", json={"category": None}).status_code == 422
    store = app.dependency_overrides[get_store]()
    store.rows[row["id"]]["category"] = None  # e.g. a row edited by hand in the dashboard
    assert client.patch(f"/receipts/{row['id']}", json={}).status_code == 422


def test_export_neutralises_spreadsheet_formulas(client: TestClient) -> None:
    store = app.dependency_overrides[get_store]()
    store.rows["1"] = {
        "id": "1",
        "user_id": "user-a",
        "status": "confirmed",
        "merchant": "=HYPERLINK(evil)",
    }
    store.rows["2"] = {
        "id": "2",
        "user_id": "user-a",
        "status": "confirmed",
        "merchant": "",
        "total_amount": "-5.00",
    }
    store.rows["3"] = {"id": "3", "user_id": "user-a", "status": "confirmed", "merchant": "\tcmd"}
    store.rows["4"] = {"id": "4", "user_id": "user-a", "status": "confirmed", "note": "@SUM(A1)"}
    text = client.get("/receipts/export.csv").text
    assert "'=HYPERLINK(evil)" in text and "'\tcmd" in text and "'@SUM(A1)" in text
    assert "-5.00" in text and "'-5.00" not in text  # refunds stay numbers


def test_each_user_sees_only_their_own_receipts(client: TestClient) -> None:
    png = receipt_png("SANYU STATIONERY SDN BHD", "TOTAL RM 9.00")
    mine = client.post("/receipts", files={"file": ("r.png", png, "image/png")}).json()
    client.patch(f"/receipts/{mine['id']}", json={"category": "other"})

    SIGNED_IN["user"] = "user-b"
    assert client.get("/receipts/export.csv").text.count("\n") == 1  # header row only
    theirs = client.post("/receipts", files={"file": ("r.png", png, "image/png")}).json()

    for user, own, other in (("user-a", mine, theirs), ("user-b", theirs, mine)):
        SIGNED_IN["user"] = user
        assert [r["id"] for r in client.get("/receipts").json()] == [own["id"]]
        assert client.get(f"/receipts/{own['id']}").status_code == 200
        assert client.get(f"/receipts/{other['id']}").status_code == 404  # not 403: don't reveal it
        assert (
            client.patch(f"/receipts/{other['id']}", json={"category": "meals"}).status_code == 404
        )


def test_receipts_need_a_sign_in() -> None:
    client = TestClient(app)  # no fake sign-in: the real token check runs
    assert client.get("/receipts").status_code == 401
    assert client.get("/receipts", headers={"Authorization": "Bearer nonsense"}).status_code == 401
    assert client.get("/health").status_code == 200  # stays open for the hosting health check


def test_images_over_the_pixel_limit_are_refused(client: TestClient, monkeypatch) -> None:
    # A small file can still decode into a huge image (PNG compresses well); the limit is checked
    # from the header, before decoding. Lowered here so the test image stays small.
    monkeypatch.setitem(receipts_router.MAX_PIXELS, "PNG", 10_000)
    big = Image.new("RGB", (200, 100), "white")  # 20,000 pixels
    buffer = BytesIO()
    big.save(buffer, "PNG")
    res = client.post("/receipts", files={"file": ("big.png", buffer.getvalue(), "image/png")})
    assert res.status_code == 413
    assert "MP" in res.json()["detail"]
