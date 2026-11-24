"""Book production extensions for epy_draft."""

from .apparatus import assemble as assemble_apparatus
from .book import BookQualityError, check_citations, count_crossrefs
from .book import build as build_book
from .figures import FigureSpec
from .figures import render_flow as render_figure
from .project import BookProject
from .references import Reference, context, resolve, write_bib
from .references import search as search_references
from .renderers import (
    render_docs,
    render_papers,
    render_reports,
    render_slides,
)

__all__ = [
    "BookProject",
    "BookQualityError",
    "FigureSpec",
    "Reference",
    "assemble_apparatus",
    "build_book",
    "check_citations",
    "context",
    "count_crossrefs",
    "render_docs",
    "render_figure",
    "render_papers",
    "render_reports",
    "render_slides",
    "resolve",
    "search_references",
    "write_bib",
]
