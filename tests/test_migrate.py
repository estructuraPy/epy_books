from __future__ import annotations

from pathlib import Path

from epy_books import Book
from epy_books.migrate import main, migrate_project


def test_migration_dry_run_and_apply(project: Path):
    dry = migrate_project(project, dry_run=True)
    assert dry.dry_run is True
    assert dry.store.exists() is False

    result = migrate_project(project)
    assert result.dry_run is False
    assert result.store.is_file()
    assert result.backup is not None and result.backup.is_file()
    assert result.documents >= 1
    reopened = Book.from_file(result.store)
    assert reopened.manifest.title == "Libro de prueba"


def test_migration_from_direct_manifest(tmp_path: Path):
    content = tmp_path / "libro" / "contenido"
    content.mkdir(parents=True)
    (content / "Cap01_x.md").write_text("# C\n\nTexto\n", encoding="utf-8")
    (tmp_path / "libro.json").write_text(
        '{"libro": {"titulo": "T", "autor": "A", "stem": "T"}, '
        '"capitulos": [{"n": 1, "fuente": "libro/contenido/Cap01_x.md"}]}',
        encoding="utf-8",
    )
    result = migrate_project(tmp_path, dry_run=True)
    assert result.documents == 1
    assert main([str(tmp_path), "--dry-run"]) == 0
