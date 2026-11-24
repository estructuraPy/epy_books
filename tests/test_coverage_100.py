from __future__ import annotations

import json
import runpy
import sys
import zipfile
from pathlib import Path

import pymupdf
import pytest
from docx import Document

from epy_books import Book, get_design
from epy_books._core import _archive, _renderer, _validation
from epy_books._core._archive import pack, unpack, verify
from epy_books._core._manifest import BookManifest
from epy_books._core._renderer import BookRenderer, RenderError
from epy_books._core._store import BookStore
from epy_books.epy_suite_connect._adapters.docs_bridge import (
    DocsUnavailableError,
)


def test_archive_digest_and_corrupt_unpack(tmp_path):
    project = tmp_path / "p"
    project.mkdir()
    store = BookStore(project / "s.kepy", create=True)
    store.upsert_document("a.md", "A", "uno")
    attachment = project / "x.txt"
    attachment.write_text("x", encoding="utf-8")
    store.attach(str(attachment), role="figure")
    store.close()
    archive = tmp_path / "s.zepy"
    pack(project / "s.kepy", archive)
    with zipfile.ZipFile(archive) as handle:
        entries = {name: handle.read(name) for name in handle.namelist()}
    corrupt = tmp_path / "corrupt.zepy"
    with zipfile.ZipFile(corrupt, "w") as handle:
        for name, data in entries.items():
            if name == "x.txt":
                data = b"y" + data[1:]
            handle.writestr(name, data)
    assert verify(corrupt)
    with pytest.raises(_archive.ArchiveError):
        unpack(corrupt, tmp_path / "restored")


def test_rebase_empty_root(tmp_path):
    store = BookStore(tmp_path / "s.kepy", create=True)
    store.set_meta("manifest_json", json.dumps({"project_root": ""}))
    store.close()
    _archive._rebase_manifest(tmp_path / "s.kepy", tmp_path)


def test_manifest_source_fallback_to_content(tmp_path):
    content = tmp_path / "libro" / "contenido"
    content.mkdir(parents=True)
    (content / "Cap01_x.md").write_text("# X\n", encoding="utf-8")
    manifest = tmp_path / "coordinacion" / "libro.json"
    manifest.parent.mkdir()
    manifest.write_text(
        json.dumps(
            {
                "libro": {"titulo": "T", "stem": "S"},
                "capitulos": [{"n": 1, "titulo": "X", "fuente": "Cap01_x.md"}],
            }
        ),
        encoding="utf-8",
    )
    assert BookManifest.from_file(manifest).chapters[0].source.is_file()


def test_manifest_source_fallbacks(tmp_path):
    content = tmp_path / "libro" / "contenido"
    content.mkdir(parents=True)
    (content / "Cap01_x.md").write_text("# X\n", encoding="utf-8")
    manifest = tmp_path / "coordinacion" / "libro.json"
    manifest.parent.mkdir()
    manifest.write_text(
        json.dumps(
            {
                "libro": {"titulo": "T", "stem": "S"},
                "capitulos": [{"n": 1, "titulo": "X"}],
            }
        ),
        encoding="utf-8",
    )
    parsed = BookManifest.from_file(manifest)
    assert parsed.chapters[0].source.name == "Cap01_x.md"
    no_source = tmp_path / "no_source" / "libro.json"
    no_source.parent.mkdir()
    no_source.write_text(
        json.dumps(
            {
                "libro": {"titulo": "T"},
                "capitulos": [{"n": 1, "titulo": "X"}],
            }
        ),
        encoding="utf-8",
    )
    assert BookManifest.from_file(no_source).chapters == []


def test_book_bodies_relative_and_preflight(project: Path, monkeypatch):
    book = Book.from_file(project / "coordinacion" / "libro.json")
    target = project / "coordinacion" / "Libro_Prueba.kepy"
    book.to_store(target)
    outside = project.parent / "outside.md"
    outside.write_text("# X\n", encoding="utf-8")
    class FakeManifest:
        project_root = book.manifest.project_root
        source_files = [outside]

    original = book.manifest
    book.manifest = FakeManifest()  # type: ignore[assignment]
    try:
        assert book._bodies() == {}
    finally:
        book.manifest = original  # type: ignore[assignment]
    pdf = project / "p.pdf"
    document = pymupdf.open()
    page = document.new_page(width=612, height=792)
    page.insert_text((72, 72), "x")
    document.save(pdf)
    document.close()
    assert book.preflight(pdf, design="et_manuscrito").pages == 1
    book.close()


def test_manuscript_paragraph_and_validation_text(tmp_path):
    path = tmp_path / "m.docx"
    document = Document()
    run = document.add_paragraph().add_run("x")
    run.font.name = None
    document.save(path)
    from epy_books._core._manuscript import format_manuscript

    format_manuscript(path)
    assert _validation._text(tmp_path) == ""


def test_minigit_tag_without_head(tmp_path):
    store = BookStore(tmp_path / "s.kepy", create=True)
    with pytest.raises(ValueError):
        store.minigit.tag("x")
    store.close()


def test_renderer_bibliography_and_index(project: Path, monkeypatch):
    chapter = project / "libro" / "contenido" / "Cap01_Book01.md"
    chapter.write_text("# C\n\nCita [@k].\n", encoding="utf-8")
    (project / "libro" / "references.bib").write_text(
        "@book{k, author={A, B}, title={T}, year={2024}}",
        encoding="utf-8",
    )
    book = Book.from_file(project / "coordinacion" / "libro.json")
    captured = {}

    def fake(markdown, *args, **kwargs):
        captured["markdown"] = markdown
        return {"pdf": Path("x.pdf")}

    monkeypatch.setattr(_renderer, "render_book", fake)
    renderer = BookRenderer(
        book.manifest,
        get_design("aec_ingenieria"),
    )
    renderer.render(project / "out", formats=("pdf",))
    assert "Referencias" in captured["markdown"]
    assert "printindex" in captured["markdown"]


def test_renderer_docs_unavailable(project: Path, monkeypatch):
    book = Book.from_file(project / "coordinacion" / "libro.json")
    renderer = BookRenderer(book.manifest, get_design("aec_ingenieria"))

    def fail(*args, **kwargs):
        raise DocsUnavailableError("x")

    monkeypatch.setattr(_renderer, "render_book", fail)
    with pytest.raises(RenderError):
        renderer.render(project / "out", formats=("docx",))


def test_compose_back_matter_bodies(project: Path):
    book = Book.from_file(project / "coordinacion" / "libro.json")
    body = project / "libro" / "contenido" / "Apendice_X.md"
    body.write_text("# Apendice\n", encoding="utf-8")
    book.manifest.back_matter.append(body)
    try:
        text = _renderer.compose_book(
            book.manifest, {str(body): "desde memoria"}
        )
        assert "desde memoria" in text
        text = _renderer.compose_book(book.manifest, {})
        assert "Apendice" in text
    finally:
        book.manifest.back_matter.remove(body)


def test_migrate_main(project: Path, monkeypatch):
    import epy_books.migrate as migrate

    monkeypatch.setattr(
        migrate,
        "migrate_project",
        lambda *a, **k: migrate.MigrationResult(
            project, project, None, 1, True
        ),
    )
    monkeypatch.setattr(
        sys, "argv", ["epy_books.migrate", str(project), "--dry-run"]
    )
    with pytest.raises(SystemExit) as exc:
        runpy.run_module("epy_books.migrate", run_name="__main__")
    assert exc.value.code == 0
