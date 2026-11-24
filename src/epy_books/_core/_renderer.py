"""Compose a book and hand it to the suite document backend."""

from __future__ import annotations

import shutil
from collections.abc import Mapping
from pathlib import Path

from epy_books._core._catalog import DesignSpec
from epy_books._core._index import annotate_headings
from epy_books._core._manifest import BookManifest
from epy_books.epy_suite_connect._adapters.docs_bridge import (
    DocsUnavailableError,
    render_book,
)


class RenderError(RuntimeError):
    """Raised when a book cannot be rendered."""


def _read(path: Path, bodies: Mapping[str, str] | None) -> str:
    if bodies is not None and str(path) in bodies:
        return bodies[str(path)]
    if not path.is_file():
        raise RenderError(f"missing chapter: {path}")
    return path.read_text(encoding="utf-8")


def compose_book(
    manifest: BookManifest,
    bodies: Mapping[str, str] | None = None,
) -> str:
    """Return the Markdown body in reading order."""
    parts: list[str] = []
    if manifest.front_matter is not None:
        parts.append(_read(manifest.front_matter, bodies))
    for chapter in manifest.chapters:
        parts.append(_read(chapter.source, bodies))
    for path in manifest.back_matter:
        if path.stem.lower() == "referencias":
            continue
        if bodies is not None and str(path) in bodies:
            parts.append(bodies[str(path)])
        elif path.is_file():
            parts.append(path.read_text(encoding="utf-8"))
    return "\n\n\\newpage\n\n".join(part.strip() for part in parts) + "\n"


def _bibliography(manifest: BookManifest) -> Path | None:
    candidates = (
        manifest.project_root / "referencias" / "references.bib",
        manifest.project_root / "libro" / "references.bib",
        manifest.project_root / "libro" / "referencias.bib",
        manifest.project_root / "references.bib",
    )
    return next((path for path in candidates if path.is_file()), None)


def _csl() -> Path | None:
    path = (
        Path(__file__).resolve().parent.parent
        / "_config"
        / "_assets"
        / "csl"
        / "apa.csl"
    )
    return path if path.is_file() else None


class BookRenderer:
    """Render one book through epy_docs."""

    def __init__(
        self,
        manifest: BookManifest,
        design: DesignSpec,
        bodies: Mapping[str, str] | None = None,
    ) -> None:
        """Bind the manifest, design and optional stored bodies."""
        self.manifest = manifest
        self.design = design
        self.bodies = bodies
        self.notes: list[str] = []

    def render(
        self,
        output_dir: str | Path,
        *,
        formats: tuple[str, ...] = ("pdf", "docx", "html"),
    ) -> dict[str, Path | None]:
        """Render the requested formats."""
        supported = tuple(
            item
            for item in formats
            if item in {"pdf", "docx", "html", "epub"}
        )
        if not supported:
            raise RenderError("no supported output format requested")
        title = self.manifest.title
        author = self.manifest.author
        markdown = compose_book(self.manifest, self.bodies)
        markdown = self._stage_figures(markdown, Path(output_dir))
        bibliography = _bibliography(self.manifest)
        if bibliography is not None and "[@" in markdown:
            markdown += (
                "\n\n# Referencias {.unnumbered}\n\n::: {#refs}\n:::\n"
            )
        if (
            self.design.components.get("index", False)
            and "pdf" in supported
        ):
            markdown = annotate_headings(markdown)
            markdown += "\n\n\\printindex\n"
        passes = 3 if "pdf" in supported else 1
        produced: dict[str, Path | None] = {}
        try:
            for _ in range(passes):
                produced = render_book(
                    markdown,
                    output_dir,
                    title=title,
                    author=author,
                    language=self.manifest.language,
                    design=self.design,
                    formats=supported,
                    bibliography=_bibliography(self.manifest),
                    csl=_csl(),
                )
            return produced
        except DocsUnavailableError as exc:
            raise RenderError(str(exc)) from exc

    def _stage_figures(self, markdown: str, output_dir: Path) -> str:
        figures = self.manifest.figures_dir
        if figures is None or not figures.is_dir():
            return markdown
        destination = output_dir / "figuras"
        destination.mkdir(parents=True, exist_ok=True)
        shutil.copytree(figures, destination, dirs_exist_ok=True)
        return markdown.replace("../figuras/", "figuras/")
