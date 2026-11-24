"""Structured validation of a book against an editorial profile."""

from __future__ import annotations

import re
from collections.abc import Mapping
from dataclasses import dataclass, field
from pathlib import Path

from epy_books._core._catalog import BookProfile, DesignSpec

UNSAFE_GLYPHS = frozenset("✓✗◐►□�•▪▫●○─═│┌┐└┘├┤┬┴┼")

FORBIDDEN_SOURCE = re.compile(
    r"(?im)(?:^\s*:\s+[^\n]*|Fuente:\s*)[^\n]*?(?:"
    r"s[ií]ntesis\s+(?:del?\s+cap[ií]tulo|de\s+los\s+cap[ií]tulos)"
    r"|elaboraci[oó]n\s+propia"
    r"|archivo\s+del\s+autor"
    r")\b"
)


class Severity:
    """Severity levels for a validation finding."""

    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


@dataclass(frozen=True)
class Warning:
    """One validation finding."""

    code: str
    severity: str
    message: str

    def __str__(self) -> str:
        """Return ``[severity] message`` for plain-text display."""
        return f"[{self.severity}] {self.message}"


@dataclass
class ValidationResult:
    """The collected findings for one book and profile."""

    profile_id: str
    profile_name: str
    warnings: list[Warning] = field(default_factory=list)

    def add(self, code: str, severity: str, message: str) -> None:
        """Append one finding."""
        self.warnings.append(Warning(code, severity, message))

    @property
    def ok(self) -> bool:
        """Whether no error-severity finding was reported."""
        return not any(
            item.severity == Severity.ERROR for item in self.warnings
        )

    def messages(self) -> list[str]:
        """Return findings as plain strings."""
        return [str(item) for item in self.warnings]

    def __iter__(self):
        """Iterate over findings."""
        return iter(self.warnings)

    def __len__(self) -> int:
        """Number of findings."""
        return len(self.warnings)

    def __bool__(self) -> bool:
        """Truthy when at least one finding exists."""
        return bool(self.warnings)


HEADING_RE = re.compile(r"^(#{1,6})\s+")
MANUAL_NUMBER_RE = re.compile(
    r"^(#{1,6})\s+(?:§\s*)?(?:(?:Capítulo|Apéndice|Sección)\s+[0-9A-F]"
    r"|[0-9]+(?:\.[0-9]+)+|[A-F]\.[0-9]+)\b"
)


def _empty_heading(text: str) -> str:
    """Return the first heading with no prose before the next heading."""
    lines = text.splitlines()
    headings = [
        index for index, line in enumerate(lines) if HEADING_RE.match(line)
    ]
    for position, index in enumerate(headings):
        end = (
            headings[position + 1]
            if position + 1 < len(headings)
            else len(lines)
        )
        if not any(item.strip() for item in lines[index + 1 : end]):
            return lines[index].strip()
    return ""


def _text(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except OSError:
        return ""


def validate_book(
    *,
    profile: BookProfile,
    design: DesignSpec,
    root: Path,
    title: str,
    author: str,
    chapters: list[Path],
    front_matter: Path | None,
    back_matter: list[Path],
    publication: dict[str, object] | None = None,
    documents: Mapping[str, str] | None = None,
) -> ValidationResult:
    """Validate a book's structure and editorial requirements."""
    result = ValidationResult(profile.id, profile.name)
    if not title.strip():
        result.add(
            "title.missing", Severity.ERROR, "El libro no tiene titulo."
        )
    if not author.strip():
        result.add(
            "author.missing", Severity.ERROR, "El libro no tiene autor."
        )
    if not chapters:
        result.add(
            "chapters.missing",
            Severity.ERROR,
            "El libro no tiene capitulos.",
        )
    for chapter in chapters:
        stored = documents.get(str(chapter)) if documents else None
        if not chapter.is_file() and stored is None:
            result.add(
                "chapter.missing",
                Severity.ERROR,
                f"Falta el capitulo: {chapter}",
            )
            continue
        text = stored if stored is not None else _text(chapter)
        if not text.strip():
            result.add(
                "chapter.empty",
                Severity.ERROR,
                f"El capitulo esta vacio: {chapter.name}",
            )
        if "TODO" in text or "TBD" in text:
            result.add(
                "chapter.placeholder",
                Severity.ERROR,
                f"Placeholder sin resolver en {chapter.name}",
            )
        if FORBIDDEN_SOURCE.search(text):
            result.add(
                "caption.forbidden_source",
                Severity.ERROR,
                f"Fuente de figura o tabla prohibida en {chapter.name}",
            )
        unsafe = "".join(sorted(set(text) & UNSAFE_GLYPHS))
        if unsafe:
            result.add(
                "glyph.unsafe",
                Severity.ERROR,
                f"Glifos no renderizables en {chapter.name}: {unsafe}",
            )
        empty_heading = _empty_heading(text)
        if empty_heading:
            result.add(
                "heading.empty",
                Severity.ERROR,
                f"Subtitulo sin contenido en {chapter.name}: {empty_heading}",
            )
        for line in text.splitlines():
            if MANUAL_NUMBER_RE.match(line):
                result.add(
                    "heading.manual_number",
                    Severity.ERROR,
                    f"Numeracion manual en {chapter.name}: {line.strip()}",
                )
                break
    if (
        front_matter is not None
        and not front_matter.is_file()
        and (documents is None or str(front_matter) not in documents)
    ):
        result.add(
            "front_matter.missing",
            Severity.ERROR,
            f"Falta el material preliminar: {front_matter}",
        )
    for path in back_matter:
        if not path.is_file() and (
            documents is None or str(path) not in documents
        ):
            result.add(
                "back_matter.missing",
                Severity.ERROR,
                f"Falta el material final: {path}",
            )
    if design.mirrored and not design.margins.get("mirror"):
        result.add(
            "design.mirror",
            Severity.WARNING,
            "El diseno declara margenes espejados pero no los activa.",
        )
    publication = publication or {}
    requirements = profile.validation
    if requirements.get("require_ai_declaration") and not publication.get(
        "ai_declaration"
    ):
        result.add(
            "publication.ai_declaration",
            Severity.ERROR,
            "Falta la declaracion de uso de IA.",
        )
    if requirements.get("require_permissions") and not publication.get(
        "permissions"
    ):
        result.add(
            "publication.permissions",
            Severity.ERROR,
            "Faltan los permisos de material de terceros.",
        )
    if requirements.get("require_isbn") and not publication.get("isbn_print"):
        result.add(
            "publication.isbn",
            Severity.ERROR,
            "El perfil exige ISBN impreso y no esta asignado.",
        )
    if requirements.get("require_index") and not design.components.get(
        "index", False
    ):
        result.add(
            "publication.index",
            Severity.WARNING,
            "El perfil pide indice analitico.",
        )
    if not root.is_dir():
        result.add(
            "project.root",
            Severity.ERROR,
            f"La raiz del proyecto no existe: {root}",
        )
    return result
