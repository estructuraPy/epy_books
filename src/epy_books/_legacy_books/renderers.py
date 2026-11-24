"""Adapters for the ePy rendering engines."""

# pyright: reportMissingImports=false, reportUnknownVariableType=false, reportUnknownArgumentType=false, reportUnknownMemberType=false
from __future__ import annotations

import re
import shutil
from pathlib import Path


def render_docs(
    markdown: str,
    output: str | Path,
    *,
    title: str = "Documento",
    author: str = "",
    bibliography: str | Path | None = None,
    csl: str | Path | None = None,
    assets_dir: str | Path | None = None,
    document_type: str = "report",
    layout_style: str = "corporate",
) -> Path:
    """Render Markdown with ePy_docs."""
    from epy_docs.writers import DocumentWriter

    target = Path(output)
    target.parent.mkdir(parents=True, exist_ok=True)
    markdown = re.sub(r"\\[^\x00-\x7F]", r"\\text{CRC} ", markdown)
    markdown = re.sub(r"\\\?(\d)", r"\\text{CRC }\1", markdown)
    if bibliography and Path(bibliography).is_file():
        markdown = re.sub(
            r"\n#{1,6}\s+Referencias\s*\n.*\Z",
            "",
            markdown,
            flags=re.IGNORECASE | re.DOTALL,
        )
    if assets_dir:
        figures = target.parent / "figuras"
        figures.mkdir(exist_ok=True)
        for item in Path(assets_dir).iterdir():
            if item.is_file() and item.suffix.lower() in {
                ".png",
                ".jpg",
                ".jpeg",
            }:
                shutil.copy2(item, figures / item.name)
    figures_dir = target.parent / "figuras"
    if figures_dir.is_dir():

        def drop_missing(match: re.Match[str]) -> str:
            name = Path(match.group(1)).name
            return match.group(0) if (figures_dir / name).is_file() else ""

        markdown = re.sub(
            r"!\[[^\]]*\]\((figuras/[^)]+)\)[^\n]*\n?",
            drop_missing,
            markdown,
        )
    source = target.with_suffix(".md")
    source.write_text(markdown, encoding="utf-8")
    writer = DocumentWriter(
        document_type=document_type, layout_style=layout_style, language="es"
    )
    writer.output_dir = str(target.parent)
    if author:
        writer.set_author(name=author)
    writer.set_project_info(
        code="",
        name=title,
        project_type="",
        status="Documento",
        created_date="",
        location="",
    )
    writer.add_markdown_file(
        str(source), convert_tables=False, fix_image_paths=False
    )
    writer.generate(
        pdf=True,
        html=False,
        docx=False,
        qmd=False,
        markdown=False,
        tex=False,
        output_filename=target.stem,
        bibliography_path=str(bibliography) if bibliography else "",
        csl_path=str(csl) if csl else "",
    )
    if not target.is_file():
        raise RuntimeError(f"ePy_docs no gener? {target}")
    return target


def render_slides(
    source: str | Path, output: str | Path, *, theme: str = "academic"
) -> Path:
    """Render an ePy_slides deck."""
    from epy_slides import SlideDeck

    target = Path(output)
    target.parent.mkdir(parents=True, exist_ok=True)
    deck = SlideDeck.from_file(Path(source), theme=theme)
    deck.to_pdf(target)
    return target


def render_reports(
    markdown: str,
    output: str | Path,
    *,
    title: str = "Informe",
    assets_dir: str | Path | None = None,
) -> Path:
    """Render Markdown with ePy_reports."""
    try:
        from epy_reports import Report
    except ImportError as exc:
        raise ImportError(
            "epy_reports no est? instalado en este entorno"
        ) from exc
    target = Path(output)
    target.parent.mkdir(parents=True, exist_ok=True)
    if assets_dir:
        figures = target.parent / "figuras"
        figures.mkdir(exist_ok=True)
        for item in Path(assets_dir).iterdir():
            if item.is_file() and item.suffix.lower() in {
                ".png",
                ".jpg",
                ".jpeg",
            }:
                shutil.copy2(item, figures / item.name)
    figures_dir = target.parent / "figuras"
    if figures_dir.is_dir():

        def drop_missing(match: re.Match[str]) -> str:
            name = Path(match.group(1)).name
            return match.group(0) if (figures_dir / name).is_file() else ""

        markdown = re.sub(
            r"!\[[^\]]*\]\((figuras/[^)]+)\)[^\n]*\n?",
            drop_missing,
            markdown,
        )
    source = target.with_suffix(".md")
    source.write_text(markdown, encoding="utf-8")
    report = Report.from_file(source)
    report.to_pdf(str(target))
    return target


def render_papers(
    markdown: str,
    output: str | Path,
    *,
    title: str = "Art?culo",
    assets_dir: str | Path | None = None,
) -> Path:
    """Render Markdown with ePy_papers."""
    try:
        from epy_papers import Paper
    except ImportError as exc:
        raise ImportError(
            "epy_papers no est? instalado en este entorno"
        ) from exc
    target = Path(output)
    target.parent.mkdir(parents=True, exist_ok=True)
    if assets_dir:
        figures = target.parent / "figuras"
        figures.mkdir(exist_ok=True)
        for item in Path(assets_dir).iterdir():
            if item.is_file() and item.suffix.lower() in {
                ".png",
                ".jpg",
                ".jpeg",
            }:
                shutil.copy2(item, figures / item.name)
    figures_dir = target.parent / "figuras"
    if figures_dir.is_dir():

        def drop_missing(match: re.Match[str]) -> str:
            name = Path(match.group(1)).name
            return match.group(0) if (figures_dir / name).is_file() else ""

        markdown = re.sub(
            r"!\[[^\]]*\]\((figuras/[^)]+)\)[^\n]*\n?",
            drop_missing,
            markdown,
        )
    source = target.with_suffix(".md")
    source.write_text(markdown, encoding="utf-8")
    paper = Paper.from_file(source)
    paper.to_draft("asce-jse", target, fmt="pdf")
    return target
