from __future__ import annotations

from pathlib import Path

from epy_books import Book, get_design
from epy_books._core._renderer import BookRenderer


def test_stage_figures(project: Path):
    figures = project / "libro" / "figuras"
    figures.mkdir(parents=True)
    (figures / "x.png").write_bytes(b"image")
    book = Book.from_file(project / "coordinacion" / "libro.json")
    renderer = BookRenderer(book.manifest, get_design("aec_ingenieria"))
    output = project / "out"
    staged = renderer._stage_figures("![x](../figuras/x.png)", output)
    assert staged == "![x](figuras/x.png)"
    assert (output / "figuras" / "x.png").is_file()
