"""Portable ``.zepy`` snapshots: a store plus its attachments."""

from __future__ import annotations

import hashlib
import json
import sqlite3
import tempfile
import zipfile
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from epy_books._core._store import is_store

ARCHIVE_SUFFIX = ".zepy"
MANIFEST_NAME = "zepy.json"
FORMAT_VERSION = 1
_SKIP_DIRS = frozenset(
    {"__pycache__", ".pytest_cache", ".ruff_cache", ".benchmarks", ".git"}
)


class ArchiveError(RuntimeError):
    """Raised when a ``.zepy`` cannot be written or read."""


@dataclass(frozen=True)
class Manifest:
    """What a ``.zepy`` says it holds."""

    project: str
    store: str
    written_at: str
    files: dict[str, dict[str, object]]
    format_version: int = FORMAT_VERSION

    @property
    def total_bytes(self) -> int:
        """Return the unpacked size of every member."""
        return sum(int(entry["bytes"]) for entry in self.files.values())


def _digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _backup_store(store: Path, target: Path) -> None:
    source = sqlite3.connect(f"file:{store.as_posix()}?mode=ro", uri=True)
    try:
        destination = sqlite3.connect(target)
        try:
            source.backup(destination)
        finally:
            destination.close()
    finally:
        source.close()


def _project_root(store: Path) -> Path:
    if store.parent.name == "coordinacion":
        return store.parent.parent
    return store.parent


def _stored_attachments(store: Path) -> list[Path]:
    connection = sqlite3.connect(
        f"file:{store.as_posix()}?mode=ro", uri=True
    )
    try:
        rows = connection.execute(
            "SELECT path FROM book_attachments ORDER BY path"
        ).fetchall()
    except sqlite3.DatabaseError:
        rows = []
    finally:
        connection.close()
    return [Path(str(row[0])) for row in rows if Path(str(row[0])).is_file()]


def _members(
    root: Path, store: Path, attachments: list[Path]
) -> list[tuple[Path, str]]:
    out: list[tuple[Path, str]] = []
    for path in attachments:
        if not path.is_file() or path == store:
            continue
        try:
            arcname = path.relative_to(root).as_posix()
        except ValueError:
            arcname = path.name
        if any(part in _SKIP_DIRS for part in Path(arcname).parts):
            continue
        out.append((path, arcname))
    return out


def _dump_manifest(manifest: Manifest) -> str:
    lines = [
        "{",
        '  "format": "zepy",',
        f'  "format_version": {manifest.format_version},',
        f'  "project": {json.dumps(manifest.project)},',
        f'  "store": {json.dumps(manifest.store)},',
        f'  "written_at": {json.dumps(manifest.written_at)},',
        '  "files": {',
    ]
    entries = list(manifest.files.items())
    for index, (name, entry) in enumerate(entries):
        leaf = json.dumps(entry, separators=(", ", ": "), sort_keys=True)
        comma = "," if index < len(entries) - 1 else ""
        lines.append(f"    {json.dumps(name)}: {leaf}{comma}")
    lines += ["  }", "}"]
    return "\n".join(lines) + "\n"


def pack(
    store: str | Path,
    target: str | Path,
    *,
    attachments: list[str | Path] | None = None,
) -> Manifest:
    """Seal a store and its registered attachments into one ``.zepy``."""
    store_path = Path(store).resolve()
    if not is_store(store_path):
        raise ArchiveError(f"{store_path} is not an epy_books store")
    root = _project_root(store_path)
    target_path = Path(target)
    target_path.parent.mkdir(parents=True, exist_ok=True)
    scratch = target_path.with_name(target_path.name + ".part")
    files: dict[str, dict[str, object]] = {}
    selected = (
        [Path(item) for item in attachments]
        if attachments is not None
        else _stored_attachments(store_path)
    )
    try:
        with tempfile.TemporaryDirectory() as hold:
            staged = Path(hold) / store_path.name
            _backup_store(store_path, staged)
            with zipfile.ZipFile(
                scratch, "w", zipfile.ZIP_DEFLATED
            ) as archive:
                data = staged.read_bytes()
                files[store_path.name] = {
                    "bytes": len(data),
                    "sha256": _digest(data),
                }
                archive.writestr(store_path.name, data)
                for path, arcname in _members(root, store_path, selected):
                    payload = path.read_bytes()
                    files[arcname] = {
                        "bytes": len(payload),
                        "sha256": _digest(payload),
                    }
                    archive.writestr(arcname, payload)
                manifest = Manifest(
                    project=root.name,
                    store=store_path.name,
                    written_at=datetime.now(timezone.utc).isoformat(
                        timespec="seconds"
                    ),
                    files=files,
                )
                archive.writestr(MANIFEST_NAME, _dump_manifest(manifest))
    except BaseException:
        scratch.unlink(missing_ok=True)
        raise
    scratch.replace(target_path)
    return manifest


def read_manifest(archive: str | Path) -> Manifest:
    """Read an archive manifest without unpacking it."""
    try:
        with zipfile.ZipFile(archive) as handle:
            raw = handle.read(MANIFEST_NAME).decode("utf-8")
    except (OSError, KeyError, zipfile.BadZipFile) as exc:
        raise ArchiveError(
            f"{Path(archive).name} is not a .zepy: {exc}"
        ) from exc
    body = json.loads(raw)
    return Manifest(
        project=str(body["project"]),
        store=str(body["store"]),
        written_at=str(body["written_at"]),
        files=dict(body["files"]),
        format_version=int(body.get("format_version", 1)),
    )


def verify(archive: str | Path) -> list[str]:
    """Return every way an archive disagrees with its manifest."""
    manifest = read_manifest(archive)
    problems: list[str] = []
    with zipfile.ZipFile(archive) as handle:
        present = set(handle.namelist()) - {MANIFEST_NAME}
        for name, entry in manifest.files.items():
            if name not in present:
                problems.append(f"{name}: missing from archive")
                continue
            data = handle.read(name)
            if len(data) != int(entry["bytes"]):
                problems.append(f"{name}: size differs from manifest")
            elif _digest(data) != str(entry["sha256"]):
                problems.append(f"{name}: contents differ from manifest")
        for name in sorted(present - set(manifest.files)):
            problems.append(f"{name}: in archive, not in manifest")
    return problems


def unpack(
    archive: str | Path,
    parent: str | Path,
    name: str | None = None,
) -> Path:
    """Materialize a ``.zepy`` into a real folder and return its store."""
    manifest = read_manifest(archive)
    problems = verify(archive)
    if problems:
        raise ArchiveError(
            f"{Path(archive).name} is not intact: " + "; ".join(problems[:5])
        )
    root = Path(parent) / (name or manifest.project)
    if root.exists():
        raise ArchiveError(f"{root} already exists; choose another name")
    root.mkdir(parents=True)
    with zipfile.ZipFile(archive) as handle:
        for member in manifest.files:
            target = root / member
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(handle.read(member))
    store = root / manifest.store
    if not is_store(store):
        raise ArchiveError(f"{archive} did not contain an epy_books store")
    _rebase_manifest(store, root)
    return store


def _rebase_manifest(store: Path, root: Path) -> None:
    connection = sqlite3.connect(store)
    try:
        row = connection.execute(
            "SELECT value FROM book_meta WHERE key='manifest_json'"
        ).fetchone()
        if row is None:
            return
        data = json.loads(str(row[0]))
        raw_root = str(data.get("project_root") or "")
        if not raw_root.strip():
            return
        old_root = Path(raw_root)

        def rebase(value: str) -> str:
            path = Path(value)
            try:
                return str(root / path.relative_to(old_root))
            except ValueError:
                return value

        data["project_root"] = str(root)
        data["source_path"] = rebase(str(data.get("source_path") or ""))
        for chapter in data.get("chapters") or []:
            chapter["source"] = rebase(str(chapter["source"]))
        if data.get("front_matter"):
            data["front_matter"] = rebase(str(data["front_matter"]))
        data["back_matter"] = [
            rebase(str(item)) for item in data.get("back_matter") or []
        ]
        connection.execute(
            "UPDATE book_meta SET value=? WHERE key='manifest_json'",
            (json.dumps(data, ensure_ascii=False),),
        )
        connection.commit()
    finally:
        connection.close()
