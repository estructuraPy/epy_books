from __future__ import annotations

import zipfile
from pathlib import Path

from epy_books._core._archive import (
    ArchiveError,
    pack,
    unpack,
    verify,
)
from epy_books._core._store import BookStore


def test_archive_detects_missing_and_extra_members(tmp_path: Path):
    project = tmp_path / "p"
    project.mkdir()
    store = BookStore(project / "s.kepy", create=True)
    store.upsert_document("a.md", "A", "texto")
    store.close()
    archive = tmp_path / "s.zepy"
    pack(project / "s.kepy", archive)
    with zipfile.ZipFile(archive, "a") as handle:
        handle.writestr("extra.txt", "x")
    assert verify(archive)


def test_archive_refuses_missing_store(tmp_path: Path):
    bad = tmp_path / "bad.zepy"
    bad.write_text("no", encoding="utf-8")
    import pytest

    with pytest.raises(ArchiveError):
        pack(tmp_path / "missing.kepy", bad)


def test_unpack_refuses_existing_destination(tmp_path: Path):
    project = tmp_path / "p"
    project.mkdir()
    store = BookStore(project / "s.kepy", create=True)
    store.upsert_document("a.md", "A", "texto")
    store.close()
    archive = tmp_path / "s.zepy"
    pack(project / "s.kepy", archive)
    import pytest

    with pytest.raises(ArchiveError):
        unpack(archive, tmp_path)
