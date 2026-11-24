"""ePy Books identity as ePy Studio reads it."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

_REGISTER_MODES = frozenset({"default", "openwith", "none"})


@dataclass(frozen=True)
class StudioManifest:
    """What Studio needs to know about one application."""

    app_id: str
    display: str
    description: str
    component: str
    register: str
    document_types: tuple[str, ...] = ()
    icon: str = ""
    entry_point: str = ""

    def __post_init__(self) -> None:
        """Refuse an impossible registration claim."""
        if self.register not in _REGISTER_MODES:
            raise ValueError(f"{self.app_id}: unknown register mode")
        if self.register == "none" and self.document_types:
            raise ValueError(f"{self.app_id}: register none claims types")

    def as_dict(self) -> dict[str, Any]:
        """Return the JSON-ready mapping."""
        return {
            "id": self.app_id,
            "display": self.display,
            "description": self.description,
            "component": self.component,
            "register": self.register,
            "document_types": list(self.document_types),
            "icon": self.icon,
            "entry_point": self.entry_point,
        }


MANIFEST = StudioManifest(
    app_id="epy_books",
    display="ePy Books",
    description=(
        "Book authoring and editorial design - project history, "
        "AEC layouts, PDF, Word and manuscript exports"
    ),
    component="books",
    register="none",
    document_types=(),
    icon="_core/_packaging/assets_build/epy_books.ico",
    entry_point="epy_books.app",
)


def manifest() -> StudioManifest:
    """Return this application's Studio manifest."""
    return MANIFEST
