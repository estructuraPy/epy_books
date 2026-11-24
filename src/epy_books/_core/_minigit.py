"""A small, database-backed version history for book projects."""

from __future__ import annotations

import difflib
import hashlib
import uuid
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from epy_books._core._store import BookStore


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


class MiniGit:
    """Commit, inspect and restore document versions inside a ``kepy``."""

    def __init__(self, store: BookStore) -> None:
        """Bind the version history to one store."""
        self.store = store

    @property
    def head(self) -> str:
        """Return the current head commit id."""
        row = self.store.connection.execute(
            "SELECT commit_id FROM minigit_refs WHERE name='head'"
        ).fetchone()
        return "" if row is None else str(row["commit_id"])

    def commit(self, message: str) -> str:
        """Snapshot every current document and return the commit id."""
        clean = message.strip() or "snapshot"
        entries = [
            (int(row["id"]), int(row["version"]))
            for row in self.store.documents()
        ]
        parent = self.head or None
        seed = f"{_now()}|{clean}|{parent}|{entries}|{uuid.uuid4().hex}"
        commit_id = hashlib.sha256(seed.encode("utf-8")).hexdigest()[:16]
        with self.store.connection:
            self.store.connection.execute(
                "INSERT INTO minigit_commits(id, parent, message, created_at) "
                "VALUES(?, ?, ?, ?)",
                (commit_id, parent, clean, _now()),
            )
            self.store.connection.executemany(
                "INSERT INTO minigit_commit_entries"
                "(commit_id, document_id, version) VALUES(?, ?, ?)",
                [
                    (commit_id, document_id, version)
                    for document_id, version in entries
                ],
            )
            self.store.connection.execute(
                "INSERT INTO minigit_refs(name, commit_id) VALUES('head', ?) "
                "ON CONFLICT(name) DO UPDATE SET commit_id=excluded.commit_id",
                (commit_id,),
            )
        return commit_id

    def log(self, limit: int = 20) -> list[dict[str, Any]]:
        """Return the most recent commits."""
        rows = self.store.connection.execute(
            "SELECT id, parent, message, created_at "
            "FROM minigit_commits ORDER BY created_at DESC LIMIT ?",
            (limit,),
        ).fetchall()
        return [dict(row) for row in rows]

    def entries(self, commit_id: str) -> list[dict[str, Any]]:
        """Return the document versions recorded in a commit."""
        rows = self.store.connection.execute(
            "SELECT e.document_id, d.path, e.version "
            "FROM minigit_commit_entries e "
            "JOIN book_documents d ON d.id=e.document_id "
            "WHERE e.commit_id=? ORDER BY d.path",
            (commit_id,),
        ).fetchall()
        return [dict(row) for row in rows]

    def diff(self, path: str, from_version: int, to_version: int) -> str:
        """Return a unified diff between two versions of one document."""
        first = self.store.version(path, from_version)
        second = self.store.version(path, to_version)
        if first is None or second is None:
            raise KeyError(f"{path}: version not found")
        return "".join(
            difflib.unified_diff(
                str(first["body"]).splitlines(keepends=True),
                str(second["body"]).splitlines(keepends=True),
                fromfile=f"{path}@{from_version}",
                tofile=f"{path}@{to_version}",
            )
        )

    def restore(self, commit_id: str) -> list[str]:
        """Restore every document in ``commit_id`` as a new version."""
        restored: list[str] = []
        for entry in self.entries(commit_id):
            record = self.store.version(
                str(entry["path"]), int(entry["version"])
            )
            if record is None:
                raise KeyError(f"{entry['path']}@{entry['version']} not found")
            self.store.upsert_document(
                str(entry["path"]),
                str(entry["path"]),
                str(record["body"]),
                message=f"restore {commit_id}",
            )
            restored.append(str(entry["path"]))
        self.commit(f"restore {commit_id}")
        return restored

    def tag(self, name: str, commit_id: str | None = None) -> None:
        """Tag the head or a named commit."""
        target = commit_id or self.head
        if not target:
            raise ValueError("there is no commit to tag")
        with self.store.connection:
            self.store.connection.execute(
                "INSERT INTO minigit_tags(name, commit_id) VALUES(?, ?) "
                "ON CONFLICT(name) DO UPDATE SET commit_id=excluded.commit_id",
                (name, target),
            )
