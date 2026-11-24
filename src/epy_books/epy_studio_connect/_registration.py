"""Registration and launch hints for ePy Studio."""

from __future__ import annotations

from typing import Any

from epy_books.epy_studio_connect._manifest import manifest


def register(argv: list[str] | None = None) -> list[str]:
    """Register the application, or state that it claims no extension."""
    entry = manifest()
    if entry.register == "none":
        return [
            f"{entry.app_id}: claims no document type; registered in Studio "
            "as an application."
        ]
    mode = "default" if "--as-default" in list(argv or []) else "openwith"
    return [
        f"{entry.app_id}: registers "
        f"{','.join(entry.document_types)} as {mode}."
    ]


def unregister() -> list[str]:
    """Return the registration-removal line."""
    entry = manifest()
    if entry.register == "none":
        return [f"{entry.app_id}: no document type registration to remove."]
    return [f"{entry.app_id}: registration removed."]


def launch_hint() -> dict[str, Any]:
    """Return the hint Studio passes to the application."""
    entry = manifest()
    return {"app_id": entry.app_id, "entry_point": entry.entry_point}
