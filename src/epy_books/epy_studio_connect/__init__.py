"""The per-application contract with ePy Studio."""

from epy_books.epy_studio_connect._connect import (
    Handoff,
    StudioConnectError,
    available,
    command,
    handoff,
    open_app,
)
from epy_books.epy_studio_connect._manifest import StudioManifest, manifest
from epy_books.epy_studio_connect._registration import (
    launch_hint,
    register,
    unregister,
)

__all__ = [
    "Handoff",
    "StudioConnectError",
    "StudioManifest",
    "available",
    "command",
    "handoff",
    "launch_hint",
    "manifest",
    "open_app",
    "register",
    "unregister",
]
