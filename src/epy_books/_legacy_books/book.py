"""Assemble and compile a book under a quality gate."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import pymupdf

from . import apparatus, contract, encoding, references
from .renderers import render_docs


class BookQualityError(RuntimeError):
    """Raised when a book does not meet the quality gate."""

    pass


def splice(apparatus_md: str, sessions: list[Path]) -> str:
    """Join apparatus and sessions into one Markdown body."""
    parts = [apparatus_md]
    for session in sessions:
        text = session.read_text(encoding="utf-8")
        text = encoding.repair_spanish(text)
        text = re.sub(r"\n## Referencias\s*\n[\s\S]*$", "", text).strip()
        parts.append(text)
    return "\n\n\\newpage\n\n".join(parts)


def count_crossrefs(text: str) -> dict[str, int]:
    """Count table, figure, equation and citation mentions."""
    tables = re.findall(r"\*\*Tabla\s+(\d+)\.", text)
    figures = re.findall(r"Figura\s+(\d+)", text)
    equations = re.findall(r"Ecuaci[oó]n\s+(\d+)", text)
    return {
        "tables": len(tables),
        "figures": len(figures),
        "equations": len(equations),
        "citations": len(re.findall(r"\[@([^\]]+)\]", text)),
    }


def check_citations(text: str) -> list[str]:
    """Return citation keys that do not resolve."""
    keys = set(re.findall(r"\[@([^\]]+)\]", text))
    return [key for key in sorted(keys) if references.resolve(key) is None]


def build(
    *,
    title: str,
    sessions: list[Path],
    output_dir: Path,
    stem: str,
    bibliography: Path,
    csl: Path,
    chapter_titles: list[str],
    author: str = "",
    min_pages: int = 200,
) -> Path:
    """Compile the book and enforce the quality gate."""
    output_dir.mkdir(parents=True, exist_ok=True)
    body = contract.normalize_markdown(
        splice(apparatus.assemble(title, chapter_titles), sessions)
    )
    problems = contract.issues(body)
    if problems:
        raise BookQualityError(f"contrato Markdown: {problems}")
    missing = check_citations(body)
    if missing:
        raise BookQualityError(
            f"citas no resueltas contra references.db: {missing}"
        )
    encoding.assert_clean(body)
    body_path = output_dir / f"{stem}_body.md"
    body_path.write_text(body, encoding="utf-8")
    pdf = render_docs(
        body,
        output_dir / f"{stem}.pdf",
        title=title,
        author=author,
        bibliography=bibliography,
        csl=csl,
        document_type="book",
        layout_style="academic",
    )
    pdf = output_dir / f"{stem}.pdf"
    doc: Any = pymupdf.open(pdf)
    pages = doc.page_count
    rendered: str = "\n".join(str(page.get_text()) for page in doc)
    broken = re.findall(r"[A-Za-z???????????]\?[A-Za-z???????????]", rendered)
    if broken or "\ufffd" in rendered:
        raise BookQualityError(
            f"{stem}: tildes rotas en el PDF: {sorted(set(broken))[:8]}"
        )
    if pages < min_pages:
        raise BookQualityError(f"{stem}: {pages} páginas; mínimo {min_pages}")
    return pdf
