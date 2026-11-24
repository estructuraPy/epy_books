"""Small handoff contract used by ePy Studio."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


class StudioConnectError(RuntimeError):
    """Raised when a Studio handoff is malformed."""


@dataclass(frozen=True)
class Handoff:
    """One Studio request to open a project path."""

    path: str
    as_default: bool = False


def handoff(payload: dict[str, Any] | None = None) -> Handoff:
    """Build a handoff from Studio's JSON payload."""
    data = payload or {}
    path = str(data.get("path") or "")
    if not path:
        raise StudioConnectError("Studio handoff has no path")
    return Handoff(path=path, as_default=bool(data.get("as_default")))


def command(entry_point: str = "epy_books.app") -> list[str]:
    """Return the executable command Studio should launch."""
    return ["epy_books", "--entry", entry_point]


def available() -> bool:
    """Return whether the launcher contract is importable."""
    return True


def open_app() -> Handoff | None:
    """Return no implicit handoff; Studio supplies the path."""
    return None
