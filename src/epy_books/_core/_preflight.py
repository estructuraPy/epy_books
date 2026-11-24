"""Print-oriented checks for a rendered book PDF."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pymupdf

from epy_books._core._catalog import DesignSpec


@dataclass(frozen=True)
class PreflightResult:
    """What a PDF must satisfy before it is called print-ready."""

    path: Path
    pages: int
    failures: tuple[str, ...]
    warnings: tuple[str, ...]

    @property
    def ok(self) -> bool:
        """Whether no blocking finding was reported."""
        return not self.failures


def preflight_pdf(
    path: str | Path,
    design: DesignSpec,
    *,
    allowed_blank: set[int] | None = None,
) -> PreflightResult:
    """Check page geometry, blank pages and embedded fonts."""
    target = Path(path)
    allowed = allowed_blank or set()
    failures: list[str] = []
    warnings: list[str] = []
    with pymupdf.open(target) as document:
        pages = document.page_count
        if pages == 0:
            return PreflightResult(target, 0, ("el PDF no tiene paginas",), ())
        expected = (design.page_size[0] * 72, design.page_size[1] * 72)
        for index, page in enumerate(document, 1):
            actual = (round(page.rect.width, 1), round(page.rect.height, 1))
            if abs(actual[0] - expected[0]) > 1:
                failures.append(
                    f"pagina {index}: ancho {actual[0]} pt, esperado "
                    f"{expected[0]:.1f} pt"
                )
                break
            if abs(actual[1] - expected[1]) > 1:
                failures.append(
                    f"pagina {index}: alto {actual[1]} pt, esperado "
                    f"{expected[1]:.1f} pt"
                )
                break
        blank = [
            index
            for index, page in enumerate(document, 1)
            if not page.get_text().strip() and not page.get_images(full=True)
        ]
        unexpected = [index for index in blank if index not in allowed]
        if unexpected:
            failures.append(f"paginas en blanco no previstas: {unexpected}")
        for index, page in enumerate(document, 1):
            if not page.get_fonts():
                warnings.append(f"pagina {index}: sin fuentes embebidas")
                break
    return PreflightResult(target, pages, tuple(failures), tuple(warnings))
