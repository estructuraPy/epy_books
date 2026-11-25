"""Small translation surface for the GUI shell and the guide."""

from __future__ import annotations

import os
from collections.abc import Callable

__all__ = [
    "LANGUAGES",
    "current_language",
    "on_language_changed",
    "set_language",
    "text",
    "tr",
]

LANGUAGES = {"en": "English", "es": "Español"}

_lang = (
    "es"
    if os.environ.get("EPY_BOOKS_LANGUAGE", "es").lower().startswith("es")
    else "en"
)
_callbacks: list[Callable[[], None]] = []

_EN = {
    "app": "ePy Books",
    "open": "Open book",
    "save": "Save",
    "export": "Export",
    "history": "History",
    "design": "Design",
    "validate": "Validate",
}


_ES = {
    "app": "ePy Books",
    "open": "Abrir libro",
    "save": "Guardar",
    "export": "Exportar",
    "history": "Historial",
    "design": "Diseño",
    "validate": "Validar",
    "File": "Archivo",
    "View": "Ver",
    "Help": "Ayuda",
    "Language": "Idioma",
    "Guide": "Guía",
    "Demo": "Demo",
    "Quit": "Salir",
    "Open book...": "Abrir libro...",
    "Open book": "Abrir libro",
    "Main": "Principal",
    "Ready": "Listo",
    "About ePy Books": "Acerca de ePy Books",
    "Step by step": "Paso a paso",
    "Book (*.json *.kepy);;All files (*)":
        "Libro (*.json *.kepy);;Todos los archivos (*)",
    "Could not open: {error}": "No se pudo abrir: {error}",
    "Profile": "Perfil",
    "Design": "Diseño",
    "Chapter": "Capítulo",
    "Export PDF": "Exportar PDF",
    "Design...": "Diseño...",
    "Validation": "Validación",
    "The book passes.": "El libro cumple.",
    "No content.": "Sin contenido.",
    "Design updated.": "Diseno actualizado.",
    "PDF generated.": "PDF generado.",
    "Books: editorial design, history and export.":
        "Libros: diseño editorial, historial y exportación.",
    "Open": "Abrir",
    "Open a book project.": "Abra un proyecto de libro.",
    "Choose the profile and the design.":
        "Elija el perfil y el diseño.",
    "Write": "Escribir",
    "Edit the chapters.": "Edite los capítulos.",
    "Review": "Revisar",
    "Validate the manuscript.": "Valide el manuscrito.",
    "Export": "Exportar",
    "Render the PDF.": "Genere el PDF.",
    "Prepare": "Preparar",
    "Deliver": "Entregar",
    "GUIDED WORKFLOW": "FLUJO GUIADO",
    "Follow the workflow from start to finish.":
        "Siga el flujo de principio a fin.",
    "Step {current} of {total}": "Paso {current} de {total}",
    "Next: {step}": "Siguiente: {step}",
    "Back": "Atrás",
}


def current_language() -> str:
    """Return the active UI language."""
    return _lang


def set_language(code: str) -> None:
    """Switch the active language and relabel every registered widget."""
    global _lang
    if code not in LANGUAGES or code == _lang:
        return
    _lang = code
    for callback in tuple(_callbacks):
        callback()


def on_language_changed(callback: Callable[[], None]) -> None:
    """Register a relabel callback."""
    _callbacks.append(callback)


def tr(key: str, **values: object) -> str:
    """Return one localized string, formatted with the given values."""
    table = _ES if _lang == "es" else _EN
    label = table.get(key, key)
    return label.format(**values) if values else label


def text(key: str) -> str:
    """Backward-compatible alias for ``tr``."""
    return tr(key)
