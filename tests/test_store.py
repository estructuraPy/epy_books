from __future__ import annotations

from pathlib import Path

import pytest

from epy_books._core._store import BookStore, StoreError, is_store


def test_store_rejects_foreign_file(tmp_path: Path):
    foreign = tmp_path / "foreign.kepy"
    foreign.write_bytes(b"not a database")
    assert is_store(foreign) is False
    with pytest.raises(StoreError):
        BookStore(foreign)


def test_minigit_commit_diff_and_restore(tmp_path: Path):
    store = BookStore(tmp_path / "book.kepy", create=True)
    store.upsert_document("c1.md", "Capitulo", "uno", message="import")
    first = store.minigit.commit("primera")
    store.upsert_document("c1.md", "Capitulo", "dos", message="edit")
    second = store.minigit.commit("segunda")
    assert first != second
    assert len(store.minigit.log()) == 2
    assert "uno" in store.minigit.diff("c1.md", 1, 2)
    store.minigit.restore(first)
    assert store.document("c1.md")["body"] == "uno"
    store.close()


def test_attachment_and_design_round_trip(tmp_path: Path):
    store = BookStore(tmp_path / "book.kepy", create=True)
    figure = tmp_path / "fig.png"
    figure.write_bytes(b"image")
    store.attach(str(figure), role="figure")
    assert store.attachments()[0]["role"] == "figure"
    store.set_design("aec_ingenieria", {"page": {}})
    assert store.design()["design_id"] == "aec_ingenieria"
    store.set_publication({"isbn_print": None})
    assert store.publication()["isbn_print"] is None
    store.close()
