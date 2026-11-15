import pytest

import app.store as store_module
from app.store import PAGE, Store


class FakeQuery:
    """Just enough of the Supabase query builder to test paging and cleanup."""

    def __init__(self, db: "FakeClient") -> None:
        self.db, self.filters, self.rows = db, {}, None

    def select(self, *_):
        return self

    def order(self, *_, **__):
        return self

    def eq(self, column, value):
        self.filters[column] = value
        return self

    def range(self, start: int, end: int):
        self.db.ranges.append((start, end))
        self.rows = self.db.rows[start : end + 1]
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
        if self.rows is None:  # a lookup such as select("id").eq("image_path", path)
            self.rows = [
                r for r in self.db.rows if all(r.get(k) == v for k, v in self.filters.items())
            ]
        self.data = self.rows
        return self


class FakeBucket:
    def __init__(self, db: "FakeClient") -> None:
        self.db = db

    def upload(self, path, *_):
        self.db.photos.add(path)

    def remove(self, paths):
        self.db.photos -= set(paths)


class FakeClient:
    def __init__(self, rows: int = 0, insert_error: str | None = None) -> None:
        self.rows = [{"id": str(i)} for i in range(rows)]
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
    rows = Store().list("confirmed")
    assert len(rows) == PAGE * 2 + 5 and rows[0]["id"] == str(PAGE * 2 + 4)  # newest first
    assert fake.ranges == [(0, PAGE - 1), (PAGE, 2 * PAGE - 1), (2 * PAGE, 3 * PAGE - 1)]


def test_failed_insert_removes_the_photo_only_when_no_receipt_uses_it(monkeypatch) -> None:
    for error, photo_kept in (("before_save", False), ("after_save", True)):
        fake = FakeClient(insert_error=error)
        monkeypatch.setattr(store_module, "_client", lambda fake=fake: fake)
        with pytest.raises(RuntimeError):
            Store().save(b"img", "image/png", {"status": "confirmed"})
        assert bool(fake.photos) is photo_kept, error
