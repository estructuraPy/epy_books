"""Small translation surface for the GUI shell."""

from __future__ import annotations

import os

_LANGUAGE = os.environ.get("EPY_BOOKS_LANGUAGE", "es").lower()
_STRINGS = {
    "es": {
        "app": "ePy Books",
        "open": "Abrir libro",
        "save": "Guardar",
        "export": "Exportar",
        "history": "Historial",
        "design": "Diseno",
        "validate": "Validar",
    },
    "en": {
        "app": "ePy Books",
        "open": "Open book",
        "save": "Save",
        "export": "Export",
        "history": "History",
        "design": "Design",
        "validate": "Validate",
    },
}


def current_language() -> str:
    """Return the active UI language."""
    return "es" if _LANGUAGE.startswith("es") else "en"


def text(key: str) -> str:
    """Return one localized string."""
    return _STRINGS[current_language()].get(key, key)
