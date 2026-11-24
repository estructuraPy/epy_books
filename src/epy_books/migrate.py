"""Migrate a file-based book project into a ``.kepy`` project."""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from epy_books._core._archive import pack
from epy_books._core._book import Book
from epy_books._core._store import is_store


@dataclass(frozen=True)
class MigrationResult:
    """What one migration would do or did."""

    project: Path
    store: Path
    backup: Path | None
    documents: int
    dry_run: bool


def _manifest_path(project: str | Path) -> Path:
    root = Path(project).resolve()
    for candidate in (
        root / "coordinacion" / "libro.json",
        root / "libro.json",
    ):
        if candidate.is_file():
            return candidate
    raise FileNotFoundError(f"libro.json not found under {root}")


def migrate_project(
    project: str | Path,
    *,
    dry_run: bool = False,
) -> MigrationResult:
    """Import a book project, backing up an existing store first."""
    manifest = _manifest_path(project)
    root = (
        manifest.parent.parent
        if manifest.parent.name == "coordinacion"
        else manifest.parent
    )
    book = Book.from_file(manifest)
    store = root / "coordinacion" / f"{book.manifest.stem}.kepy"
    backup_dir = root / "coordinacion" / "respaldos"
    backup = None
    if store.exists():
        if not is_store(store):
            raise RuntimeError(f"{store} exists and is not an epy_books store")
        backup = backup_dir / (
            f"{book.manifest.stem}_"
            f"{datetime.now().strftime('%Y%m%d_%H%M%S')}.zepy"
        )
        if not dry_run:
            backup_dir.mkdir(parents=True, exist_ok=True)
            pack(store, backup)
    if dry_run:
        return MigrationResult(
            project=root,
            store=store,
            backup=backup,
            documents=len(book.manifest.source_files),
            dry_run=True,
        )
    if store.exists():
        raise RuntimeError(
            f"{store.name} already exists; open it instead of migrating again"
        )
    store.parent.mkdir(parents=True, exist_ok=True)
    book.to_store(store)
    if backup is None:
        backup_dir.mkdir(parents=True, exist_ok=True)
        backup = backup_dir / (
            f"{book.manifest.stem}_"
            f"{datetime.now().strftime('%Y%m%d_%H%M%S')}.zepy"
        )
        pack(store, backup)
    return MigrationResult(
        project=root,
        store=store,
        backup=backup,
        documents=len(book.store.documents()) if book.store else 0,
        dry_run=False,
    )


def main(argv: list[str] | None = None) -> int:
    """Run the migration command."""
    parser = argparse.ArgumentParser(prog="epy_books.migrate")
    parser.add_argument("project", help="Carpeta del libro.")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args(argv)
    result = migrate_project(args.project, dry_run=args.dry_run)
    print(f"proyecto: {result.project}")
    print(f"store: {result.store}")
    print(f"respaldo: {result.backup}")
    print(f"documentos: {result.documents}")
    print("dry run" if result.dry_run else "migrado")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
