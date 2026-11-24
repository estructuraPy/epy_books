"""Render a composed book through the public epy_docs API."""

from __future__ import annotations

import importlib
import re
from pathlib import Path
from typing import Any

from epy_books._core._catalog import DesignSpec


class DocsUnavailableError(RuntimeError):
    """Raised when epy_docs is not installed or produces no file."""


def epy_docs_available() -> bool:
    """Return whether the epy_docs public API can be imported."""
    try:
        importlib.import_module("epy_docs")
    except ImportError:
        return False
    return True


def _docs() -> Any:
    try:
        return importlib.import_module("epy_docs")
    except ImportError as exc:
        raise DocsUnavailableError(
            "rendering a book needs epy_docs installed; the authoring API "
            "remains available without it"
        ) from exc


def render_book(
    markdown: str,
    output_dir: str | Path,
    *,
    title: str,
    author: str,
    language: str,
    design: DesignSpec,
    formats: tuple[str, ...],
    bibliography: Path | None = None,
    csl: Path | None = None,
) -> dict[str, Path | None]:
    """Render composed Markdown to the requested book formats."""
    docs = _docs()
    target = Path(output_dir)
    target.mkdir(parents=True, exist_ok=True)
    source = target / "libro_completo.md"
    source.write_text(markdown, encoding="utf-8")
    writer = docs.DocumentWriter(
        document_type="book",
        layout_style=design.layout_style,
        language=language,
        table_mode="native",
        output_dir=str(target),
        design=getattr(docs, "BookDesign", None)
        and docs.BookDesign.from_mapping(design.to_epy_docs()),
    )
    writer.set_author(name=author)
    writer.set_project_info(name=title, project_type="Libro")
    writer.add_markdown_file(
        str(source), convert_tables=False, fix_image_paths=False
    )
    produced = writer.generate(
        pdf="pdf" in formats,
        html="html" in formats,
        docx="docx" in formats,
        epub="epub" in formats,
        qmd=False,
        output_filename=_safe_stem(title),
        bibliography_path=str(bibliography) if bibliography else None,
        csl_path=str(csl) if csl else None,
    )
    return {
        key: Path(value) if value else None
        for key, value in produced.items()
        if key in formats
    }


def _safe_stem(title: str) -> str:
    stem = re.sub(r'[<>:"/\\|?*]+', "", title).strip()
    stem = re.sub(r"\s+", "_", stem)
    return stem or "libro"
