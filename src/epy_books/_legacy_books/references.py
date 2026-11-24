"""Resolve and format references from the local reference database."""

from __future__ import annotations

import os
import sqlite3
from dataclasses import dataclass
from pathlib import Path

DB = Path(os.environ.get("EPY_REFERENCES_DB", "references.db"))


@dataclass(frozen=True)
class Reference:
    """One reference record from the local database."""

    id: int
    title: str
    year: int | None
    organization: str
    filename: str

    @property
    def key(self) -> str:
        """Return the citation key."""
        return f"ref{self.id}"

    def bibtex(self) -> str:
        """Return the BibTeX entry."""
        author = self.organization or "Referencia"
        year = self.year or "s.f."
        return (
            f"@techreport{{{self.key},\n"
            f"  author = {{{{{author}}}}},\n"
            f"  title = {{{self.title}}},\n"
            f"  year = {{{year}}},\n"
            f"  note = {{Doc #{self.id} / {self.filename}}}\n"
            f"}}"
        )


def search(query: str, limit: int = 12) -> list[Reference]:
    """Search the reference database."""
    con = sqlite3.connect(DB)
    con.row_factory = sqlite3.Row
    like = f"%{query}%"
    rows = con.execute(
        "select id,title,year,organization,filename from documents "
        "where title like ? or filename like ? or tags like ? "
        "order by year desc, title limit ?",
        (like, like, like, limit),
    ).fetchall()
    con.close()
    return [
        Reference(
            id=int(row["id"]),
            title=str(row["title"] or ""),
            year=row["year"],
            organization=str(row["organization"] or ""),
            filename=str(row["filename"] or ""),
        )
        for row in rows
    ]


def context(query: str, limit: int = 12) -> str:
    """Return a compact reference context."""
    found = search(query, limit)
    if not found:
        return "No hay documentos coincidentes en references.db."
    return "\n".join(
        f"- {ref.key}: {ref.title} ({ref.year or 's.f.'}), {ref.filename}"
        for ref in found
    )


def write_bib(refs: list[Reference], path: Path) -> None:
    """Write BibTeX entries."""
    path.write_text(
        "\n\n".join(ref.bibtex() for ref in refs) + "\n", encoding="utf-8"
    )


def resolve(key: str) -> Reference | None:
    """Resolve a reference key."""
    if not key.startswith("ref") or not key[3:].isdigit():
        return None
    con = sqlite3.connect(DB)
    con.row_factory = sqlite3.Row
    row = con.execute(
        "select id,title,year,organization,filename from documents where id=?",
        (int(key[3:]),),
    ).fetchone()
    con.close()
    if row is None:
        return None
    return Reference(
        id=int(row["id"]),
        title=str(row["title"] or ""),
        year=row["year"],
        organization=str(row["organization"] or ""),
        filename=str(row["filename"] or ""),
    )
