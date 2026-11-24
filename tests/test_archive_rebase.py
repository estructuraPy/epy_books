from __future__ import annotations

from pathlib import Path

from epy_books import Book
from epy_books._core._archive import pack, unpack


def test_unpack_rebases_manifest(project: Path, tmp_path: Path):
    book = Book.from_file(project / "coordinacion" / "libro.json")
    store = project / "coordinacion" / "Libro_Prueba.kepy"
    book.to_store(store)
    archive = tmp_path / "Libro_Prueba.zepy"
    pack(store, archive)
    unpacked = unpack(archive, tmp_path / "restored")
    reopened = Book.from_file(unpacked)
    assert reopened.manifest.project_root == unpacked.parent
    assert "Texto del capitulo" in str(reopened._bodies())
