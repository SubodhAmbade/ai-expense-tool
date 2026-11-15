import pytest

import app.store as store_module
from app.store import PAGE, Store


class FakeQuery:
    """Just enough of the Supabase query builder to test paging and cleanup."""

    def __init__(self, db: "FakeClient") -> None:
        self.db = db

    def select(self, *_):
        return self

    def order(self, *_, **__):
        return self

    def eq(self, *_):
        return self

    def range(self, start: int, end: int):
        self.db.ranges.append((start, end))
        self.rows = self.db.rows[start : end + 1]
        return self

    def insert(self, row: dict):
        if self.db.fail_insert:
            raise RuntimeError("insert failed")
        self.rows = [row]
        return self

    def execute(self):
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
    def __init__(self, rows=0, fail_insert=False) -> None:
        self.rows = [{"id": str(i)} for i in range(rows)]
        self.fail_insert = fail_insert
        self.ranges: list[tuple[int, int]] = []
        self.photos: set[str] = set()
        self.storage = self

    def table(self, _):
        return FakeQuery(self)

    def from_(self, _):
        return FakeBucket(self)


def test_list_pages_past_the_supabase_row_limit(monkeypatch) -> None:
    fake = FakeClient(rows=PAGE * 2 + 5)
    monkeypatch.setattr(store_module, "_client", lambda: fake)
    assert len(Store().list("confirmed")) == PAGE * 2 + 5
    assert fake.ranges == [(0, PAGE - 1), (PAGE, 2 * PAGE - 1), (2 * PAGE, 3 * PAGE - 1)]


def test_failed_insert_removes_the_uploaded_photo(monkeypatch) -> None:
    fake = FakeClient(fail_insert=True)
    monkeypatch.setattr(store_module, "_client", lambda: fake)
    with pytest.raises(RuntimeError, match="insert failed"):
        Store().save(b"img", "image/png", {"status": "confirmed"})
    assert fake.photos == set()
