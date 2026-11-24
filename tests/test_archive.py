from __future__ import annotations

from pathlib import Path

from epy_books._core._archive import pack, read_manifest, unpack, verify
from epy_books._core._store import BookStore


def test_archive_round_trip(tmp_path: Path):
    project = tmp_path / "proyecto"
    project.mkdir()
    store = BookStore(project / "libro.kepy", create=True)
    store.upsert_document("c1.md", "Capitulo", "texto", message="import")
    attachment = project / "figura.txt"
    attachment.write_text("figura", encoding="utf-8")
    store.attach(str(attachment), role="figure")
    store.close()
    archive = tmp_path / "libro.zepy"
    manifest = pack(project / "libro.kepy", archive)
    assert manifest.store == "libro.kepy"
    assert archive.is_file()
    assert read_manifest(archive).project == "proyecto"
    assert verify(archive) == []
    restored = unpack(archive, tmp_path / "salida")
    assert restored.is_file()
    assert BookStore(restored).documents()[0]["body"] == "texto"
