from __future__ import annotations

import json
import runpy
import sys
import types
import zipfile
from dataclasses import replace
from pathlib import Path

import pymupdf
import pytest
from docx import Document
from PIL import Image

from epy_books import Book, BookProfile, DesignSpec, get_design, get_profile
from epy_books import epy_studio_connect as studio
from epy_books._config import _loader
from epy_books._core import (
    _archive,
    _book,
    _catalog,
    _cover,
    _manifest,
    _renderer,
)
from epy_books._core._archive import (
    ArchiveError,
    Manifest,
    _members,
    _rebase_manifest,
    _stored_attachments,
    pack,
    read_manifest,
    unpack,
    verify,
)
from epy_books._core._book import BookContentError, _default_design, _deliver
from epy_books._core._manifest import BookManifest
from epy_books._core._manuscript import format_manuscript
from epy_books._core._preflight import preflight_pdf
from epy_books._core._renderer import BookRenderer, RenderError
from epy_books._core._store import BookStore, StoreError
from epy_books._core._validation import Warning, validate_book


def test_dunder_main(monkeypatch):
    import epy_books.app

    monkeypatch.setattr(epy_books.app, "main", lambda: 0)
    with pytest.raises(SystemExit) as exc:
        runpy.run_module("epy_books.__main__", run_name="__main__")
    assert exc.value.code == 0


def test_loader_missing_asset_branch():
    with pytest.raises(FileNotFoundError):
        _loader.read_asset_text("no-existe.txt")


def test_manifest_helpers_and_errors(tmp_path):
    assert _manifest.Chapter(1, "x", Path("a.md")).name == "a.md"
    path = tmp_path / "x.json"
    path.write_text('{"libro": "x"}', encoding="utf-8")
    with pytest.raises(ValueError):
        BookManifest.from_file(path)
    assert _manifest._int_or_none("no") is None


def test_manifest_from_dict_and_fallbacks(tmp_path):
    content = tmp_path / "libro" / "contenido"
    content.mkdir(parents=True)
    source = content / "Cap01_x.md"
    source.write_text("# Uno\n", encoding="utf-8")
    manifest = BookManifest.from_dict(
        {
            "book_id": "B",
            "title": "T",
            "subtitle": "",
            "author": "A",
            "affiliation": "",
            "language": "es",
            "stem": "S",
            "project_root": str(tmp_path),
            "source_path": str(tmp_path / "libro.json"),
            "chapters": [
                {"number": "x", "title": "Uno", "source": str(source)}
            ],
            "parts": [{"id": "P", "title": "P", "chapters": [1]}],
            "front_matter": str(source),
            "back_matter": [str(source)],
        }
    )
    assert manifest.chapters[0].number == "x"
    assert manifest.parts[0].chapters == (1,)
    assert manifest.front_matter == source


def test_catalog_validation_and_rows(monkeypatch):
    with pytest.raises(ValueError):
        BookProfile.from_row(
            {"id": "x", "name": " ", "output_formats": ["pdf"]}
        )
    profile = get_profile("et_submission")
    assert profile.get("missing", "d") == "d"
    with pytest.raises(ValueError):
        DesignSpec.from_row(
            {
                "id": "x",
                "name": " ",
                "page": {"width_in": 1, "height_in": 1},
                "typography": {"body_size_pt": 10},
            }
        )
    monkeypatch.setattr(_catalog, "read_epyson", lambda name: {"profiles": {}})
    with pytest.raises(ValueError):
        _catalog.list_profiles()


def test_archive_manifest_and_member_branches(tmp_path):
    manifest = Manifest("P", "s.kepy", "now", {"a": {"bytes": 2}})
    assert manifest.total_bytes == 2
    root = tmp_path / "root"
    root.mkdir()
    store = root / "s.kepy"
    store.write_text("x", encoding="utf-8")
    outside = tmp_path / "outside.txt"
    outside.write_text("x", encoding="utf-8")
    hidden = root / ".git" / "x"
    hidden.parent.mkdir()
    hidden.write_text("x", encoding="utf-8")
    found = _members(root, store, [store, outside, hidden])
    assert found == [(outside, "outside.txt")]
    bad = tmp_path / "bad.db"
    bad.write_bytes(b"not sqlite")
    assert _stored_attachments(bad) == []


def test_archive_pack_cleanup_and_verify_branches(tmp_path, monkeypatch):
    project = tmp_path / "p"
    project.mkdir()
    store = BookStore(project / "s.kepy", create=True)
    store.upsert_document("a.md", "A", "uno")
    store.close()
    archive = tmp_path / "s.zepy"
    pack(project / "s.kepy", archive)
    manifest = read_manifest(archive)
    assert manifest.total_bytes > 0

    original = _archive._members

    def explode(*args):
        raise RuntimeError("x")

    monkeypatch.setattr(_archive, "_members", explode)
    with pytest.raises(RuntimeError):
        pack(project / "s.kepy", tmp_path / "bad.zepy")
    assert not (tmp_path / "bad.zepy.part").exists()
    monkeypatch.setattr(_archive, "_members", original)

    with zipfile.ZipFile(archive) as handle:
        entries = {name: handle.read(name) for name in handle.namelist()}
    extra = tmp_path / "extra.zepy"
    with zipfile.ZipFile(extra, "w") as handle:
        for name, data in entries.items():
            handle.writestr(name, data)
        handle.writestr("extra.txt", "x")
    assert verify(extra)
    missing = tmp_path / "missing.zepy"
    with zipfile.ZipFile(missing, "w") as handle:
        for name, data in entries.items():
            if name != "s.kepy":
                handle.writestr(name, data)
    assert verify(missing)
    corrupted = tmp_path / "corrupt.zepy"
    with zipfile.ZipFile(corrupted, "w") as handle:
        for name, data in entries.items():
            handle.writestr(name, b"x" if name == "s.kepy" else data)
    assert verify(corrupted)


def test_archive_unpack_errors_and_rebase(tmp_path):
    archive = tmp_path / "bad.zepy"
    with zipfile.ZipFile(archive, "w") as handle:
        handle.writestr(
            "zepy.json",
            json.dumps(
                {
                    "project": "P",
                    "store": "missing.kepy",
                    "written_at": "now",
                    "files": {},
                }
            ),
        )
    with pytest.raises(ArchiveError):
        unpack(archive, tmp_path)
    store = BookStore(tmp_path / "s.kepy", create=True)
    store.set_meta("manifest_json", "{}")
    store.close()
    _rebase_manifest(tmp_path / "s.kepy", tmp_path)
    store = BookStore(tmp_path / "s.kepy")
    store.set_meta(
        "manifest_json",
        json.dumps({"project_root": str(tmp_path / "old"), "chapters": []}),
    )
    store.close()
    _rebase_manifest(tmp_path / "s.kepy", tmp_path)


def test_book_helpers_and_errors(project: Path, monkeypatch):
    book = Book.from_file(project / "coordinacion" / "libro.json")
    monkeypatch.setattr(_book, "_settings", lambda: {})
    assert _default_design() == "aec_ingenieria"
    target = project / "same.txt"
    target.write_text("x", encoding="utf-8")
    assert _deliver(target, target) == target

    empty = BookStore(project / "empty.kepy", create=True)
    empty.close()
    with pytest.raises(StoreError):
        Book.from_file(project / "empty.kepy")

    manifest = book.manifest
    outside = project / "outside.md"
    outside.write_text("# X\n", encoding="utf-8")
    monkeypatch.setattr(
        type(manifest), "source_files", property(lambda self: [outside])
    )
    with pytest.raises(FileNotFoundError):
        book.text_for(project / "missing.md")
    assert book._bodies() is None


def test_book_render_error_branches(project: Path, monkeypatch):
    book = Book.from_file(project / "coordinacion" / "libro.json")
    monkeypatch.setattr(book, "_render_to", lambda *a, **k: {})
    for method in (book.to_pdf, book.to_docx, book.to_html, book.to_epub):
        with pytest.raises(RuntimeError):
            method(project / "out.bin")
    with pytest.raises(RuntimeError):
        book.to_manuscript(project / "out.docx")


def test_book_figures_store_and_context(project: Path):
    figures = project / "libro" / "figuras"
    figures.mkdir(parents=True)
    (figures / "f.png").write_bytes(b"x")
    book = Book.from_file(project / "coordinacion" / "libro.json")
    target = project / "coordinacion" / "Libro_Prueba.kepy"
    book.to_store(target)
    assert book.store is not None
    book.close()
    with Book.from_file(target) as reopened:
        assert reopened.store is not None
    book.close()


def test_book_history_commit_restore_empty(project: Path):
    book = Book.from_file(project / "coordinacion" / "libro.json")
    assert book.history() == []
    with pytest.raises(StoreError):
        book.commit("x")
    with pytest.raises(StoreError):
        book.restore("x")
    with pytest.raises(StoreError):
        book.to_archive(project / "x.zepy")


def test_book_history_tag_and_missing_version(project: Path):
    book = Book.from_file(project / "coordinacion" / "libro.json")
    target = project / "coordinacion" / "Libro_Prueba.kepy"
    book.to_store(target)
    commit = book.commit("x")
    book.store.minigit.tag("v1", commit)
    with pytest.raises(KeyError):
        book.store.minigit.diff("missing.md", 1, 2)
    book.store.connection.execute(
        "DELETE FROM book_document_versions WHERE version=1"
    )
    book.store.connection.commit()
    with pytest.raises(KeyError):
        book.restore(commit)
    book.close()


def test_content_gate_and_pdf_glyph_check(project: Path):
    book = Book.from_file(project / "coordinacion" / "libro.json")
    book.validate = lambda *args, **kwargs: [  # type: ignore[method-assign]
        Warning("glyph.unsafe", "error", "x")
    ]
    with pytest.raises(BookContentError):
        book.to_pdf(project / "blocked.pdf")

    check = Book.from_file(project / "coordinacion" / "libro.json")
    pdf = project / "bad.pdf"
    document = pymupdf.open()
    page = document.new_page()
    page.insert_text((72, 72), "??")
    document.save(pdf)
    document.close()
    with pytest.raises(BookContentError):
        check._check_pdf(pdf)
    check.close()


def test_book_draft_branches(project: Path, monkeypatch):
    book = Book.from_file(project / "coordinacion" / "libro.json")
    fake = types.ModuleType("epy_draft")

    class FakeDraft:
        def __init__(self, root):
            self.root = root

        def run(self, prompt, inputs, **kwargs):
            target = Path(kwargs["output"])
            target.mkdir(parents=True, exist_ok=True)
            (target / "draft.md").write_text("# D\n", encoding="utf-8")
            return {"ok": 1}

    fake.DraftProject = FakeDraft
    monkeypatch.setitem(sys.modules, "epy_draft", fake)
    output = project / "coordinacion" / "draft"
    assert book.draft(provider="p", model="m", output=output)

    fake.DraftProject = lambda root: types.SimpleNamespace(
        run=lambda *a, **k: {"ok": 0}
    )
    with pytest.raises(RuntimeError):
        book.draft(provider="p", model="m", output=output)

    monkeypatch.setitem(sys.modules, "epy_draft", None)
    with pytest.raises(RuntimeError):
        book.draft()


def test_cover_fallback_and_wrap(tmp_path, monkeypatch):
    monkeypatch.setattr(_cover, "_FONT_CANDIDATES", ())
    monkeypatch.setattr(Path, "is_file", lambda self: False)
    assert _cover._font(10) is not None
    draw = Image.new("RGB", (100, 100))
    from PIL import ImageDraw

    lines = _cover._wrap(
        ImageDraw.Draw(draw), "uno dos tres", _cover._font(10), 10
    )
    assert lines


def test_manuscript_table(tmp_path):
    path = tmp_path / "m.docx"
    document = Document()
    table = document.add_table(rows=1, cols=1)
    cell = table.cell(0, 0)
    run = cell.paragraphs[0].add_run("x")
    run.font.name = "Times New Roman"
    document.save(path)
    format_manuscript(path)
    assert Document(path).styles["Normal"].font.name == "Arial"


def test_preflight_branches(tmp_path):
    empty = tmp_path / "empty.pdf"

    class FakeDoc:
        page_count = 0

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return None

    with pytest.MonkeyPatch.context() as patch:
        patch.setattr(pymupdf, "open", lambda p: FakeDoc())
        result = preflight_pdf(empty, get_design("aec_ingenieria"))
    assert not result.ok
    blank = tmp_path / "blank.pdf"
    doc = pymupdf.open()
    doc.new_page(width=612, height=700)
    doc.save(blank)
    doc.close()
    result = preflight_pdf(blank, get_design("aec_ingenieria"))
    assert any("alto" in item for item in result.failures)
    doc = pymupdf.open()
    doc.new_page(width=612, height=792)
    doc.save(blank)
    doc.close()
    result = preflight_pdf(blank, get_design("aec_ingenieria"))
    assert any("blanco" in item for item in result.failures)
    assert result.warnings


def test_renderer_error_and_bibliography(project: Path, monkeypatch):
    book = Book.from_file(project / "coordinacion" / "libro.json")
    renderer = BookRenderer(book.manifest, get_design("aec_ingenieria"))
    with pytest.raises(RenderError):
        renderer.render(project / "out", formats=("x",))
    with pytest.raises(RenderError):
        _renderer._read(project / "missing.md", None)
    monkeypatch.setattr(
        _book.BookRenderer, "render", lambda *a, **k: {}
    )
    assert (
        book._render_to(
            project / "x.pdf", design_id=None, formats=("pdf",)
        )
        == {}
    )


def test_store_schema_and_attachment_errors(tmp_path):
    path = tmp_path / "s.kepy"
    store = BookStore(path, create=True)
    store.set_meta("kind", "other")
    store.close()
    with pytest.raises(StoreError):
        BookStore(path)
    path2 = tmp_path / "s2.kepy"
    store = BookStore(path2, create=True)
    store.set_meta("schema_version", "99")
    store.close()
    with pytest.raises(StoreError):
        BookStore(path2)
    store = BookStore(tmp_path / "s3.kepy", create=True)
    with pytest.raises(StoreError):
        store.attach(tmp_path / "missing.txt")
    with store:
        assert store is not None
    store.close()


def test_validation_extra_branches(tmp_path):
    profile = get_profile("et_submission")
    design = get_design("aec_ingenieria")
    chapter = tmp_path / "c.md"
    chapter.write_text("TODO", encoding="utf-8")
    result = validate_book(
        profile=profile,
        design=design,
        root=tmp_path,
        title="T",
        author="A",
        chapters=[chapter],
        front_matter=tmp_path,
        back_matter=[],
        publication={"ai_declaration": "x", "permissions": ["x"]},
    )
    assert any(item.code == "chapter.placeholder" for item in result)
    assert any(item.code == "front_matter.missing" for item in result)
    fake_design = type(
        "D",
        (),
        {"mirrored": True, "margins": {}, "components": {"index": False}},
    )()
    result = validate_book(
        profile=profile,
        design=fake_design,
        root=tmp_path / "missing",
        title="T",
        author="A",
        chapters=[],
        front_matter=None,
        back_matter=[],
        publication={},
    )
    assert any(item.code == "design.mirror" for item in result)
    assert any(item.code == "project.root" for item in result)
    require = replace(
        profile,
        validation={"require_isbn": True, "require_index": True},
    )
    result = validate_book(
        profile=require,
        design=get_design("et_manuscrito"),
        root=tmp_path,
        title="T",
        author="A",
        chapters=[chapter],
        front_matter=None,
        back_matter=[],
        publication={"ai_declaration": "x", "permissions": ["x"]},
    )
    assert any(item.code == "publication.isbn" for item in result)
    assert any(item.code == "publication.index" for item in result)
    bad = tmp_path / "bad.md"
    bad.write_text("Fuente: elaboración propia", encoding="utf-8")
    result = validate_book(
        profile=profile,
        design=design,
        root=tmp_path,
        title="T",
        author="A",
        chapters=[bad],
        front_matter=None,
        back_matter=[],
        publication={"ai_declaration": "x", "permissions": ["x"]},
    )
    assert any(item.code == "caption.forbidden_source" for item in result)
    glyphs = tmp_path / "glyphs.md"
    glyphs.write_text("Estado: ✓", encoding="utf-8")
    result = validate_book(
        profile=profile,
        design=design,
        root=tmp_path,
        title="T",
        author="A",
        chapters=[glyphs],
        front_matter=None,
        back_matter=[],
        publication={"ai_declaration": "x", "permissions": ["x"]},
    )
    assert any(item.code == "glyph.unsafe" for item in result)
    heading = tmp_path / "heading.md"
    heading.write_text("## Vacío\n\n## Lleno\n\nTexto.\n", encoding="utf-8")
    result = validate_book(
        profile=profile,
        design=design,
        root=tmp_path,
        title="T",
        author="A",
        chapters=[heading],
        front_matter=None,
        back_matter=[],
        publication={"ai_declaration": "x", "permissions": ["x"]},
    )
    assert any(item.code == "heading.empty" for item in result)
    numbered = tmp_path / "numbered.md"
    numbered.write_text("## 1.1 Manual\n\nTexto.\n", encoding="utf-8")
    result = validate_book(
        profile=profile,
        design=design,
        root=tmp_path,
        title="T",
        author="A",
        chapters=[numbered],
        front_matter=None,
        back_matter=[],
        publication={"ai_declaration": "x", "permissions": ["x"]},
    )
    assert any(item.code == "heading.manual_number" for item in result)
    numbered.write_text(
        "### §17.1.1 Planteamiento\n\nTexto.\n",
        encoding="utf-8",
    )
    result = validate_book(
        profile=profile,
        design=design,
        root=tmp_path,
        title="T",
        author="A",
        chapters=[numbered],
        front_matter=None,
        back_matter=[],
        publication={"ai_declaration": "x", "permissions": ["x"]},
    )
    assert any(item.code == "heading.manual_number" for item in result)


def test_studio_manifest_and_registration_branches(monkeypatch):
    with pytest.raises(ValueError):
        studio.StudioManifest("x", "X", "", "", "bad")
    with pytest.raises(ValueError):
        studio.StudioManifest("x", "X", "", "", "none", ("md",))
    entry = studio.manifest()
    assert entry.as_dict()["id"] == "epy_books"
    fake = type(
        "M",
        (),
        {
            "register": "openwith",
            "document_types": ("md",),
            "app_id": "x",
        },
    )()
    monkeypatch.setattr(
        "epy_books.epy_studio_connect._registration.manifest",
        lambda: fake,
    )
    from epy_books.epy_studio_connect import _registration

    assert "openwith" in _registration.register([])[0]
    assert "default" in _registration.register(["--as-default"])[0]
    assert "removed" in _registration.unregister()[0]


def test_migrate_errors_and_existing_store(project: Path):
    from epy_books.migrate import _manifest_path, migrate_project

    with pytest.raises(FileNotFoundError):
        _manifest_path(project / "missing")
    store = project / "coordinacion" / "Libro_Prueba.kepy"
    store.write_text("x", encoding="utf-8")
    with pytest.raises(RuntimeError):
        migrate_project(project)
    store.unlink()
    first = migrate_project(project, dry_run=True)
    assert first.backup is None
    migrate_project(project)
    with pytest.raises(RuntimeError):
        migrate_project(project)
