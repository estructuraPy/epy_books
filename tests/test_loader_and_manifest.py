from __future__ import annotations

import json
from pathlib import Path

import pytest

from epy_books._config._loader import read_asset_text, read_epyson
from epy_books._core._manifest import BookManifest


def test_read_bundled_epyson():
    data = read_epyson("settings")
    assert data["default_profile"] == "aec_ingenieria"
    assert "epy_books" in read_asset_text("settings.epyson")


def test_manifest_parts_and_fallbacks(tmp_path: Path):
    content = tmp_path / "libro" / "contenido"
    content.mkdir(parents=True)
    (content / "Cap01_x.md").write_text("# Uno\n", encoding="utf-8")
    (content / "Cap02_y.md").write_text("# Dos\n", encoding="utf-8")
    manifest_path = tmp_path / "coordinacion" / "libro.json"
    manifest_path.parent.mkdir()
    manifest_path.write_text(
        json.dumps(
            {
                "libro": {"titulo": "T", "stem": "S"},
                "partes": [
                    {"id": "P1", "titulo": "Parte", "capitulos": [1, 2]}
                ],
                "capitulos": [
                    {"n": 1, "titulo": "Uno", "parte": "P1"},
                    {"n": 2, "titulo": "Dos", "parte": "P1"},
                ],
            }
        ),
        encoding="utf-8",
    )
    manifest = BookManifest.from_file(manifest_path)
    assert len(manifest.chapters) == 2
    assert manifest.parts[0].chapters == (1, 2)
    assert manifest.chapter_for(2).title == "Dos"
    assert manifest.to_dict()["source_path"] == str(manifest_path.resolve())
    with pytest.raises(KeyError):
        manifest.chapter_for(9)


def test_manifest_rejects_wrong_suffix(tmp_path: Path):
    path = tmp_path / "libro.yaml"
    path.write_text("{}", encoding="utf-8")
    with pytest.raises(ValueError):
        BookManifest.from_file(path)


def test_manifest_rejects_missing_book_object(tmp_path: Path):
    path = tmp_path / "libro.json"
    path.write_text('{"capitulos": []}', encoding="utf-8")
    manifest = BookManifest.from_file(path)
    assert manifest.title == "libro"
