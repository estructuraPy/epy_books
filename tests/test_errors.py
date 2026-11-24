from __future__ import annotations

from pathlib import Path

import pytest

from epy_books import BookProfile, DesignSpec
from epy_books._core._archive import ArchiveError, read_manifest, unpack
from epy_books._core._store import BookStore, StoreError


def test_profile_validation_errors():
    with pytest.raises(ValueError):
        BookProfile.from_row(
            {"id": "", "name": "x", "output_formats": ["pdf"]}
        )
    with pytest.raises(ValueError):
        BookProfile.from_row({"id": "x", "name": "x", "output_formats": []})
    with pytest.raises(ValueError):
        BookProfile.from_row(
            {
                "id": "x",
                "name": "x",
                "output_formats": ["docx"],
                "manuscript": {},
            }
        )


def test_design_validation_errors():
    with pytest.raises(ValueError):
        DesignSpec.from_row({"id": "", "name": "x"})
    with pytest.raises(ValueError):
        DesignSpec.from_row(
            {
                "id": "x",
                "name": "x",
                "page": {"width_in": 0, "height_in": 1},
            }
        )
    with pytest.raises(ValueError):
        DesignSpec.from_row(
            {
                "id": "x",
                "name": "x",
                "page": {"width_in": 1, "height_in": 1},
                "margins": {"top_in": -1},
                "typography": {"body_size_pt": 10},
            }
        )
    with pytest.raises(ValueError):
        DesignSpec.from_row(
            {
                "id": "x",
                "name": "x",
                "page": {"width_in": 1, "height_in": 1},
                "typography": {"body_size_pt": 0},
            }
        )


def test_store_requires_existing(tmp_path: Path):
    with pytest.raises(StoreError):
        BookStore(tmp_path / "missing.kepy")


def test_archive_errors(tmp_path: Path):
    bad = tmp_path / "bad.zepy"
    bad.write_text("not a zip", encoding="utf-8")
    with pytest.raises(ArchiveError):
        read_manifest(bad)
    with pytest.raises(ArchiveError):
        unpack(bad, tmp_path)


def test_store_version_helpers(tmp_path: Path):
    store = BookStore(tmp_path / "b.kepy", create=True)
    assert store.document("missing") is None
    assert store.versions("missing") == []
    assert store.version("missing", 1) is None
    store.upsert_document("a.md", "A", "uno")
    store.upsert_document("a.md", "A", "uno")
    assert len(store.versions("a.md")) == 1
    assert store.version("a.md", 2) is None
    assert store.design() is None
    assert store.publication() == {}
    store.close()
