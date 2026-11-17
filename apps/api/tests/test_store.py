import pytest

import app.store as store_module
from app.routers.receipts import CSV_COLUMNS
from app.store import PAGE, Store


class FakeQuery:
    """Just enough of the Supabase query builder to test paging, saving and owner filters."""

    def __init__(self, db: "FakeClient") -> None:
        self.db = db
        self.rows = db.rows
        self.changes: dict | None = None
        self.columns = "*"

    def select(self, columns: str):  # like Supabase, return only the named columns
        self.columns = columns
        return self

    def order(self, *_, **__):
        return self

    def eq(self, field: str, value):
        self.rows = [r for r in self.rows if r.get(field) == value]
        return self

    def update(self, changes: dict):
        self.changes = changes
        return self

    def range(self, start: int, end: int):
        self.db.ranges.append((start, end))
        self.rows = self.rows[start : end + 1]
        return self

    def insert(self, row: dict):
        if self.db.insert_error == "before_save":
            raise RuntimeError("insert failed")
        self.db.rows.append(row)
        if self.db.insert_error == "after_save":
            raise RuntimeError("connection dropped")
        self.rows = [row]
        return self

    def execute(self):
        for row in self.rows if self.changes else ():
            row.update(self.changes)
        names = None if self.columns == "*" else self.columns.split(", ")
        self.data = [{k: r.get(k) for k in names} if names else r for r in self.rows]
        return self


class FakeBucket:
    def __init__(self, db: "FakeClient") -> None:
        self.db = db

    def upload(self, path, *_):
        self.db.photos.add(path)


class FakeClient:
    def __init__(self, rows: int = 0, insert_error: str | None = None) -> None:
        self.rows = [
            {"id": str(i), "user_id": "user-a", "status": "confirmed"} for i in range(rows)
        ]
        self.insert_error = insert_error
        self.ranges: list[tuple[int, int]] = []
        self.photos: set[str] = set()
        self.storage = self

    def table(self, _):
        return FakeQuery(self)

    def from_(self, _):
        return FakeBucket(self)


def test_list_pages_past_the_supabase_row_limit_newest_first(monkeypatch) -> None:
    fake = FakeClient(rows=PAGE * 2 + 5)
    monkeypatch.setattr(store_module, "_client", lambda: fake)
    rows = Store().list("user-a", "confirmed")
    assert len(rows) == PAGE * 2 + 5 and rows[0]["id"] == str(PAGE * 2 + 4)  # newest first
    assert fake.ranges == [(0, PAGE - 1), (PAGE, 2 * PAGE - 1), (2 * PAGE, 3 * PAGE - 1)]


def test_failed_insert_keeps_the_photo_and_reports_the_error(monkeypatch) -> None:
    for error in ("before_save", "after_save"):  # from outside, these look the same
        fake = FakeClient(insert_error=error)
        monkeypatch.setattr(store_module, "_client", lambda fake=fake: fake)
        with pytest.raises(RuntimeError):
            Store().save("user-a", b"img", "image/png", {"status": "confirmed"})
        assert len(fake.photos) == 1, error


def test_every_query_is_limited_to_the_signed_in_user(monkeypatch) -> None:
    fake = FakeClient()
    fake.rows = [
        {"id": "1", "user_id": "user-a", "status": "confirmed"},
        {"id": "2", "user_id": "user-b", "status": "confirmed"},
    ]
    monkeypatch.setattr(store_module, "_client", lambda: fake)
    store = Store()
    assert [r["id"] for r in store.list("user-a", "confirmed")] == ["1"]
    assert store.get("user-a", "1") is not None
    assert store.get("user-a", "2") is None  # user-b's receipt
    with pytest.raises(IndexError):  # nothing of user-a's matches, so nothing changes
        store.update("user-a", "2", {"category": "meals"})
    assert "category" not in fake.rows[1]


def test_list_returns_every_column_the_export_needs(monkeypatch) -> None:
    fake = FakeClient()
    fake.rows = [{"id": "1", "user_id": "user-a", "status": "confirmed", "note": "Client lunch"}]
    monkeypatch.setattr(store_module, "_client", lambda: fake)
    [row] = Store().list("user-a", "confirmed")
    assert set(CSV_COLUMNS) <= set(row) and row["note"] == "Client lunch"
