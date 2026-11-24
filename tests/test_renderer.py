from __future__ import annotations

from pathlib import Path

import pytest

from epy_books import Book, get_design
from epy_books._core import _renderer
from epy_books._core._renderer import RenderError, compose_book


def test_compose_book_order(project: Path):
    book = Book.from_file(project / "coordinacion" / "libro.json")
    text = compose_book(book.manifest)
    assert text.index("Prologo") < text.index("Capitulo uno")
    assert "Texto del capitulo" in text


def test_renderer_notes_and_missing_chapter(project: Path):
    book = Book.from_file(project / "coordinacion" / "libro.json")
    renderer = _renderer.BookRenderer(
        book.manifest, get_design("et_manuscrito")
    )
    assert renderer.notes == []
    book.manifest.chapters[0].source.unlink()
    with pytest.raises(RenderError):
        compose_book(book.manifest)


def test_renderer_delegates(project: Path, monkeypatch):
    book = Book.from_file(project / "coordinacion" / "libro.json")
    renderer = _renderer.BookRenderer(
        book.manifest, get_design("et_manuscrito")
    )

    def fake(*args, **kwargs):
        return {"pdf": Path("ok.pdf")}

    monkeypatch.setattr(_renderer, "render_book", fake)
    assert renderer.render(project / "out", formats=("pdf",)) == {
        "pdf": Path("ok.pdf")
    }
