from __future__ import annotations

from pathlib import Path

import pytest

from epy_books import Book, get_design
from epy_books._core._renderer import BookRenderer, compose_book


def test_text_for_disk_and_missing(project: Path):
    book = Book.from_file(project / "coordinacion" / "libro.json")
    chapter = book.manifest.chapters[0].source
    assert "Texto del capitulo" in book.text_for(chapter)
    with pytest.raises(FileNotFoundError):
        book.text_for(project / "missing.md")


def test_render_uses_store_bodies(project: Path):
    book = Book.from_file(project / "coordinacion" / "libro.json")
    store_path = project / "coordinacion" / "Libro_Prueba.kepy"
    book.to_store(store_path)
    reopened = Book.from_file(store_path)
    bodies = reopened._bodies()
    assert bodies is not None
    reopened.manifest.chapters[0].source.unlink()
    text = compose_book(reopened.manifest, bodies)
    assert "Texto del capitulo" in text
    assert "Texto del capitulo" in reopened.text_for(
        reopened.manifest.chapters[0].source
    )
    renderer = BookRenderer(
        reopened.manifest, get_design("et_manuscrito"), bodies=bodies
    )
    assert renderer.bodies is bodies
