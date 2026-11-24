from __future__ import annotations

from pathlib import Path

from epy_books import Book


def test_open_manifest(project: Path):
    book = Book.from_file(project / "coordinacion" / "libro.json")
    assert book.manifest.title == "Libro de prueba"
    assert len(book.manifest.chapters) == 1
    assert book.manifest.front_matter is not None


def test_validate_reports_missing_publication_fields(project: Path):
    book = Book.from_file(project / "coordinacion" / "libro.json")
    result = book.validate("et_submission")
    assert result.ok is False
    assert any(item.code == "publication.ai_declaration" for item in result)


def test_store_round_trip(project: Path):
    book = Book.from_file(project / "coordinacion" / "libro.json")
    store_path = project / "coordinacion" / "Libro_Prueba.kepy"
    book.to_store(store_path)
    assert store_path.is_file()
    reopened = Book.from_file(store_path)
    assert reopened.manifest.title == "Libro de prueba"
    assert len(reopened.store.documents()) == 3
    assert reopened.store.minigit.head
