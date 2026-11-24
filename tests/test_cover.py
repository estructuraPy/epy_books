from __future__ import annotations

from pathlib import Path

from PIL import Image

from epy_books import Book, get_design
from epy_books._core._cover import render_cover


def test_cover_png(project: Path):
    book = Book.from_file(project / "coordinacion" / "libro.json")
    target = project / "out" / "portada.png"
    result = book.to_cover(target)
    assert result.is_file()
    with Image.open(result) as image:
        assert image.size == (2550, 3300)


def test_cover_pdf(project: Path):
    book = Book.from_file(project / "coordinacion" / "libro.json")
    result = render_cover(
        book.manifest,
        get_design("et_manuscrito"),
        project / "out" / "portada.pdf",
    )
    assert result.is_file()
    assert result.suffix == ".pdf"
