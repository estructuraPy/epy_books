from __future__ import annotations

from pathlib import Path

import pytest

from epy_books import get_design
from epy_books.epy_suite_connect._adapters import docs_bridge


class _Writer:
    def __init__(self, **kwargs):
        self.kwargs = kwargs
        self.generated = {}
        self.markdown = None

    def set_author(self, **kwargs):
        return self

    def set_project_info(self, **kwargs):
        return self

    def add_markdown_file(self, path, **kwargs):
        self.markdown = path
        return self

    def generate(self, **kwargs):
        self.generated = kwargs
        return {"pdf": "libro.pdf", "docx": "libro.docx"}


class _FakeDocs:
    DocumentWriter = _Writer


def test_docs_available(monkeypatch):
    from types import SimpleNamespace

    monkeypatch.setattr(
        docs_bridge,
        "importlib",
        SimpleNamespace(import_module=lambda name: object()),
    )
    assert docs_bridge.epy_docs_available() is True


def test_docs_not_available(monkeypatch):
    from types import SimpleNamespace

    def _raise(name):
        raise ImportError(name)

    monkeypatch.setattr(
        docs_bridge,
        "importlib",
        SimpleNamespace(import_module=_raise),
    )
    assert docs_bridge.epy_docs_available() is False


def test_render_book_delegates(project: Path, monkeypatch):
    monkeypatch.setattr(docs_bridge, "_docs", lambda: _FakeDocs)
    result = docs_bridge.render_book(
        "# Libro",
        project / "out",
        title="Libro",
        author="Autor",
        language="es",
        design=get_design("aec_ingenieria"),
        formats=("pdf", "docx"),
    )
    assert result["pdf"].name == "libro.pdf"
    assert (project / "out" / "libro_completo.md").is_file()


def test_docs_unavailable_branch(monkeypatch):
    import importlib

    real = importlib.import_module

    def fake(name):
        if name == "epy_docs":
            raise ImportError("blocked")
        return real(name)

    monkeypatch.setattr(importlib, "import_module", fake)
    assert docs_bridge.epy_docs_available() is False
    with pytest.raises(docs_bridge.DocsUnavailableError):
        docs_bridge._docs()


def test_render_book_reports_missing_docs(project: Path, monkeypatch):
    def fail():
        raise docs_bridge.DocsUnavailableError("missing")

    monkeypatch.setattr(docs_bridge, "_docs", fail)
    with pytest.raises(docs_bridge.DocsUnavailableError):
        docs_bridge.render_book(
            "# Libro",
            project / "out",
            title="Libro",
            author="Autor",
            language="es",
            design=get_design("aec_ingenieria"),
            formats=("pdf",),
        )
