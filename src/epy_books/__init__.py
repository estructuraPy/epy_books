"""epy_books - book authoring, editorial design and publication.

Single public API for the suite (mirrors ``epy_papers.Paper`` /
``epy_reports.Report`` / ``epy_slides.SlideDeck``)::

    from epy_books import Book

    book = Book.from_file("coordinacion/libro.json")
    book.validate("et_submission")
    book.to_pdf("libro.pdf", design="aec_ingenieria")

The GUI application is ``epy_books.app:main``; the facade stays importable
without PySide6.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from epy_export import pin_system_icu

from epy_books._core._book import Book
from epy_books._core._catalog import (
    BookProfile,
    DesignSpec,
    available_designs,
    available_profiles,
    get_design,
    get_profile,
)
from epy_books._core._preflight import PreflightResult
from epy_books._core._validation import (
    Severity,
    ValidationResult,
    Warning,
)

__version__ = "0.1.0"
__author__ = "Ing. Angel Navarro-Mora M.Sc."

__all__ = [
    "Book",
    "BookProfile",
    "DesignSpec",
    "PreflightResult",
    "Severity",
    "ValidationResult",
    "Warning",
    "available_designs",
    "available_profiles",
    "get_design",
    "get_profile",
    "get_theme",
    "themes",
    "__version__",
]

pin_system_icu()

if TYPE_CHECKING:
    from epy_books._core import themes  # noqa: F401

_LAZY = {"get_theme", "themes"}


def __getattr__(name: str) -> object:
    """Resolve the theme surface on first use."""
    if name in _LAZY:
        from epy_books._core import themes

        return themes.get if name == "get_theme" else themes
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
