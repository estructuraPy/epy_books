"""Minimal book-theme surface shared with the ePy document family."""

from __future__ import annotations

from epy_books._core._catalog import list_designs


def get(design_id: str = "aec_ingenieria") -> dict[str, object]:
    """Return one design as a theme mapping."""
    for design in list_designs():
        if design.id == design_id:
            return design.to_epy_docs()
    raise KeyError(f"unknown theme {design_id!r}")


def names() -> list[str]:
    """Return every theme id."""
    return [design.id for design in list_designs()]
