"""Read the user's ``libro.json`` into a typed book manifest."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class Chapter:
    """One chapter of a book."""

    number: int | None
    title: str
    source: Path
    part: str | None = None

    @property
    def name(self) -> str:
        """Return the source filename."""
        return self.source.name


@dataclass(frozen=True)
class Part:
    """One editorial part."""

    id: str
    title: str
    chapters: tuple[int, ...]


@dataclass
class BookManifest:
    """The content model read from ``libro.json``."""

    book_id: str
    title: str
    subtitle: str
    author: str
    affiliation: str
    language: str
    stem: str
    project_root: Path
    source_path: Path
    chapters: list[Chapter] = field(default_factory=list)
    parts: list[Part] = field(default_factory=list)
    front_matter: Path | None = None
    back_matter: list[Path] = field(default_factory=list)
    figures_dir: Path | None = None
    finals_dir: Path | None = None

    @classmethod
    def from_file(cls, path: str | Path) -> BookManifest:
        """Read a ``libro.json`` file and resolve its content paths."""
        source = Path(path).resolve()
        if source.suffix.lower() != ".json":
            raise ValueError(f"expected a libro.json file, got {source.name}")
        data = json.loads(source.read_text(encoding="utf-8"))
        book = data.get("libro") or {}
        if not isinstance(book, dict):
            raise ValueError(f"{source.name}: 'libro' must be an object")
        root = (
            source.parent.parent
            if source.parent.name.lower() == "coordinacion"
            else source.parent
        )
        stem = str(book.get("stem") or source.stem).strip()
        chapters = [
            _chapter(row, root, index)
            for index, row in enumerate(data.get("capitulos") or [], 1)
        ]
        parts = [
            Part(
                id=str(row.get("id") or f"P{index}"),
                title=str(row.get("titulo") or ""),
                chapters=tuple(
                    int(item) for item in row.get("capitulos") or ()
                ),
            )
            for index, row in enumerate(data.get("partes") or [], 1)
        ]
        content_dir = root / "libro" / "contenido"
        front = content_dir / "Frontmatter.md"
        back = sorted(content_dir.glob("Apendice_*.md"))
        references = content_dir / "Referencias.md"
        if references.is_file():
            back.append(references)
        return cls(
            book_id=str(book.get("codigo") or stem),
            title=str(book.get("titulo") or stem),
            subtitle=str(book.get("subtitulo") or ""),
            author=str(book.get("autor") or ""),
            affiliation=str(book.get("afiliacion") or ""),
            language=str(book.get("idioma") or "es"),
            stem=stem,
            project_root=root,
            source_path=source,
            chapters=[item for item in chapters if item is not None],
            parts=parts,
            front_matter=front if front.is_file() else None,
            back_matter=back,
            figures_dir=(root / "libro" / "figuras"),
            finals_dir=(root / "libro" / "finales"),
        )

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> BookManifest:
        """Rebuild a manifest stored in a ``.kepy``."""
        root = Path(str(data["project_root"]))
        chapters = [
            Chapter(
                number=item.get("number"),
                title=str(item.get("title") or ""),
                source=Path(str(item["source"])),
                part=item.get("part"),
            )
            for item in data.get("chapters") or []
        ]
        parts = [
            Part(
                id=str(item["id"]),
                title=str(item.get("title") or ""),
                chapters=tuple(int(n) for n in item.get("chapters") or ()),
            )
            for item in data.get("parts") or []
        ]
        front = data.get("front_matter")
        return cls(
            book_id=str(data.get("book_id") or ""),
            title=str(data.get("title") or ""),
            subtitle=str(data.get("subtitle") or ""),
            author=str(data.get("author") or ""),
            affiliation=str(data.get("affiliation") or ""),
            language=str(data.get("language") or "es"),
            stem=str(data.get("stem") or ""),
            project_root=root,
            source_path=Path(str(data.get("source_path") or root)),
            chapters=chapters,
            parts=parts,
            front_matter=Path(front) if front else None,
            back_matter=[
                Path(str(item)) for item in data.get("back_matter") or []
            ],
            figures_dir=root / "libro" / "figuras",
            finals_dir=root / "libro" / "finales",
        )

    @property
    def source_files(self) -> list[Path]:
        """Return every content file in reading order."""
        files: list[Path] = []
        if self.front_matter is not None:
            files.append(self.front_matter)
        files.extend(chapter.source for chapter in self.chapters)
        files.extend(self.back_matter)
        return files

    def chapter_for(self, number: int) -> Chapter:
        """Return the chapter with ``number``."""
        for chapter in self.chapters:
            if chapter.number == number:
                return chapter
        raise KeyError(f"chapter {number} not found in {self.title}")

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-ready representation."""
        return {
            "book_id": self.book_id,
            "title": self.title,
            "subtitle": self.subtitle,
            "author": self.author,
            "affiliation": self.affiliation,
            "language": self.language,
            "stem": self.stem,
            "project_root": str(self.project_root),
            "source_path": str(self.source_path),
            "chapters": [
                {
                    "number": chapter.number,
                    "title": chapter.title,
                    "source": str(chapter.source),
                    "part": chapter.part,
                }
                for chapter in self.chapters
            ],
            "parts": [
                {
                    "id": part.id,
                    "title": part.title,
                    "chapters": list(part.chapters),
                }
                for part in self.parts
            ],
            "front_matter": (
                str(self.front_matter) if self.front_matter else None
            ),
            "back_matter": [str(path) for path in self.back_matter],
        }


def _chapter(row: dict[str, Any], root: Path, index: int) -> Chapter | None:
    source = _resolve_source(row, root, index)
    if source is None:
        return None
    return Chapter(
        number=_int_or_none(row.get("n")),
        title=str(row.get("titulo") or source.stem),
        source=source,
        part=str(row["parte"]) if row.get("parte") else None,
    )


def _resolve_source(
    row: dict[str, Any], root: Path, index: int
) -> Path | None:
    raw = row.get("fuente")
    if raw:
        candidate = root / str(raw).replace("\\", "/")
        if candidate.is_file():
            return candidate
        candidate = root / "libro" / "contenido" / Path(str(raw)).name
        if candidate.is_file():
            return candidate
    content = root / "libro" / "contenido"
    for candidate in sorted(content.glob(f"Cap{index:02d}_*.md")):
        return candidate
    return None


def _int_or_none(value: Any) -> int | None:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None
