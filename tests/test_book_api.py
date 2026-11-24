from __future__ import annotations

from pathlib import Path

import pytest

from epy_books import Book, get_design
from epy_books._core._book import BookContentError
from epy_books._core._renderer import BookRenderer
from epy_books._core._store import StoreError


def _fake_render(self, output_dir, *, formats=("pdf", "docx", "html")):
    result = {}
    for fmt in formats:
        path = Path(output_dir) / f"libro.{fmt}"
        path.parent.mkdir(parents=True, exist_ok=True)
        if fmt == "docx":
            from docx import Document

            Document().save(path)
        elif fmt == "pdf":
            import pymupdf

            document = pymupdf.open()
            document.new_page()
            document.save(path)
            document.close()
        else:
            path.write_text("x", encoding="utf-8")
        result[fmt] = path
    return result


def test_profile_and_design_helpers(project: Path):
    book = Book.from_file(project / "coordinacion" / "libro.json")
    assert book.profile("et_submission").id == "et_submission"
    assert book.design("aec_ingenieria").id == "aec_ingenieria"
    assert book.profile_id
    assert book.design_id
    assert book.render_notes("aec_ingenieria", "pdf") == []
    assert book.render_notes("aec_ingenieria", "epub") == []


def test_exports(project: Path, monkeypatch):
    book = Book.from_file(project / "coordinacion" / "libro.json")
    monkeypatch.setattr(BookRenderer, "render", _fake_render)
    assert book.to_pdf(project / "out" / "libro.pdf").suffix == ".pdf"
    assert book.to_docx(project / "out" / "libro.docx").suffix == ".docx"
    assert book.to_html(project / "out" / "libro.html").suffix == ".html"
    assert book.to_epub(project / "out" / "libro.epub").suffix == ".epub"
    assert book.to_manuscript(project / "out" / "manuscrito.docx").exists()


def test_store_archive_history_and_restore(project: Path, monkeypatch):
    book = Book.from_file(project / "coordinacion" / "libro.json")
    store = project / "coordinacion" / "Libro_Prueba.kepy"
    book.to_store(store)
    assert book.history()
    assert book.commit("segundo")
    archive = project / "coordinacion" / "Libro_Prueba.zepy"
    assert book.to_archive(archive).is_file()
    reopened = Book.from_file(store)
    assert reopened.history()
    head = reopened.history()[0]["id"]
    assert reopened.restore(head)
    with pytest.raises(StoreError):
        reopened.to_store(store)
    with pytest.raises(ValueError):
        Book.from_file(archive)


def test_book_without_store_raises(project: Path):
    book = Book.from_file(project / "coordinacion" / "libro.json")
    assert book.history() == []
    with pytest.raises(StoreError):
        book.commit("x")
    with pytest.raises(StoreError):
        book.to_archive(project / "x.zepy")
    with pytest.raises(StoreError):
        book.restore("x")


def test_design_notes_branch(project: Path):
    book = Book.from_file(project / "coordinacion" / "libro.json")
    design = get_design("aec_ingenieria")
    assert design.to_epy_docs()["design_id"] == "aec_ingenieria"
    book.apply_design(get_design("tecnologia"))
    assert book.design_id == "tecnologia"
    store = project / "coordinacion" / "Libro_Prueba.kepy"
    book.to_store(store)
    book.apply_design(get_design("salud"))
    assert Book.from_file(store).store.design()["design_id"] == "salud"


def test_pdf_check_rejects_replacement_glyph(project: Path, monkeypatch):
    book = Book.from_file(project / "coordinacion" / "libro.json")
    import pymupdf

    class Page:
        def get_text(self):
            return "\u25a1"

    class Document:
        def __enter__(self):
            return [Page()]

        def __exit__(self, *args):
            return None

    monkeypatch.setattr(pymupdf, "open", lambda path: Document())
    with pytest.raises(BookContentError):
        book._check_pdf(project / "glyph.pdf")


def test_pdf_check_skips_without_pymupdf(project: Path, monkeypatch):
    import builtins

    book = Book.from_file(project / "coordinacion" / "libro.json")
    original = builtins.__import__

    def blocked(name, *args, **kwargs):
        if name == "pymupdf":
            raise ImportError
        return original(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", blocked)
    book._check_pdf(project / "missing.pdf")
