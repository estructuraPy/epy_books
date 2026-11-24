"""SQLite ``.kepy`` project store for epy_books."""

from __future__ import annotations

import hashlib
import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

STORE_SUFFIX = ".kepy"
SCHEMA_VERSION = 1
KIND = "epy_books"
_REQUIRED_TABLES = frozenset(
    {"book_meta", "book_documents", "minigit_commits"}
)


class StoreError(RuntimeError):
    """Raised when a file is not this application's store."""


def _digest(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def is_store(path: str | Path) -> bool:
    """Return whether ``path`` is an epy_books ``.kepy`` store."""
    target = Path(path)
    if not target.is_file():
        return False
    try:
        connection = sqlite3.connect(
            f"file:{target.as_posix()}?mode=ro", uri=True
        )
        try:
            rows = connection.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ).fetchall()
        finally:
            connection.close()
    except sqlite3.DatabaseError:
        return False
    names = {str(row[0]) for row in rows}
    return _REQUIRED_TABLES.issubset(names)


class BookStore:
    """A live book project backed by one SQLite file."""

    def __init__(self, path: str | Path, *, create: bool = False) -> None:
        """Open or create a ``.kepy`` store."""
        self.path = Path(path)
        if self.path.exists() and not is_store(self.path):
            raise StoreError(
                f"{self.path.name} is not an epy_books store; "
                "open a .kepy created by epy_books."
            )
        if not self.path.exists() and not create:
            raise StoreError(f"store not found: {self.path}")
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.connection = sqlite3.connect(self.path)
        self.connection.row_factory = sqlite3.Row
        if create:
            self._init_schema()
        self._check_schema()

    def _init_schema(self) -> None:
        self.connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS book_meta (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS book_documents (
                id INTEGER PRIMARY KEY,
                path TEXT NOT NULL UNIQUE,
                title TEXT NOT NULL,
                body TEXT NOT NULL,
                sha256 TEXT NOT NULL,
                version INTEGER NOT NULL
            );
            CREATE TABLE IF NOT EXISTS book_document_versions (
                id INTEGER PRIMARY KEY,
                document_id INTEGER NOT NULL,
                version INTEGER NOT NULL,
                sha256 TEXT NOT NULL,
                body TEXT NOT NULL,
                created_at TEXT NOT NULL,
                message TEXT NOT NULL,
                UNIQUE(document_id, version)
            );
            CREATE TABLE IF NOT EXISTS minigit_commits (
                id TEXT PRIMARY KEY,
                parent TEXT,
                message TEXT NOT NULL,
                created_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS minigit_commit_entries (
                commit_id TEXT NOT NULL,
                document_id INTEGER NOT NULL,
                version INTEGER NOT NULL,
                PRIMARY KEY (commit_id, document_id)
            );
            CREATE TABLE IF NOT EXISTS minigit_refs (
                name TEXT PRIMARY KEY,
                commit_id TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS minigit_tags (
                name TEXT PRIMARY KEY,
                commit_id TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS book_attachments (
                path TEXT PRIMARY KEY,
                sha256 TEXT NOT NULL,
                size INTEGER NOT NULL,
                role TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS book_design (
                id INTEGER PRIMARY KEY CHECK (id = 1),
                design_id TEXT NOT NULL,
                payload TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS book_publication (
                id INTEGER PRIMARY KEY CHECK (id = 1),
                payload TEXT NOT NULL
            );
            """
        )
        self.set_meta("kind", KIND)
        self.set_meta("schema_version", str(SCHEMA_VERSION))
        self.connection.commit()

    def _check_schema(self) -> None:
        if self.get_meta("kind") != KIND:
            raise StoreError(f"{self.path.name} is not an epy_books store")
        if int(self.get_meta("schema_version") or 0) > SCHEMA_VERSION:
            raise StoreError(
                f"{self.path.name} uses a newer epy_books schema"
            )

    def set_meta(self, key: str, value: str) -> None:
        self.connection.execute(
            "INSERT INTO book_meta(key, value) VALUES(?, ?) "
            "ON CONFLICT(key) DO UPDATE SET value=excluded.value",
            (key, value),
        )
        self.connection.commit()

    def get_meta(self, key: str, default: str = "") -> str:
        row = self.connection.execute(
            "SELECT value FROM book_meta WHERE key=?", (key,)
        ).fetchone()
        return default if row is None else str(row["value"])

    def upsert_document(
        self, path: str, title: str, body: str, *, message: str = ""
    ) -> int:
        """Store one document and return its current version."""
        digest = _digest(body)
        row = self.connection.execute(
            "SELECT id, sha256, version FROM book_documents WHERE path=?",
            (path,),
        ).fetchone()
        if row is not None and row["sha256"] == digest:
            return int(row["version"])
        version = 1 if row is None else int(row["version"]) + 1
        if row is None:
            cursor = self.connection.execute(
                "INSERT INTO book_documents"
                "(path, title, body, sha256, version) "
                "VALUES(?, ?, ?, ?, ?)",
                (path, title, body, digest, version),
            )
            document_id = int(cursor.lastrowid)
        else:
            document_id = int(row["id"])
            self.connection.execute(
                "UPDATE book_documents "
                "SET title=?, body=?, sha256=?, version=? "
                "WHERE id=?",
                (title, body, digest, version, document_id),
            )
        self.connection.execute(
            "INSERT INTO book_document_versions"
            "(document_id, version, sha256, body, created_at, message) "
            "VALUES(?, ?, ?, ?, ?, ?)",
            (document_id, version, digest, body, _now(), message),
        )
        self.connection.commit()
        return version

    def documents(self) -> list[dict[str, Any]]:
        rows = self.connection.execute(
            "SELECT id, path, title, body, sha256, version "
            "FROM book_documents ORDER BY path"
        ).fetchall()
        return [dict(row) for row in rows]

    def document(self, path: str) -> dict[str, Any] | None:
        row = self.connection.execute(
            "SELECT id, path, title, body, sha256, version "
            "FROM book_documents WHERE path=?",
            (path,),
        ).fetchone()
        return None if row is None else dict(row)

    def versions(self, path: str) -> list[dict[str, Any]]:
        row = self.connection.execute(
            "SELECT id FROM book_documents WHERE path=?", (path,)
        ).fetchone()
        if row is None:
            return []
        rows = self.connection.execute(
            "SELECT version, sha256, body, created_at, message "
            "FROM book_document_versions WHERE document_id=? "
            "ORDER BY version",
            (int(row["id"]),),
        ).fetchall()
        return [dict(item) for item in rows]

    def version(self, path: str, version: int) -> dict[str, Any] | None:
        row = self.connection.execute(
            "SELECT id FROM book_documents WHERE path=?", (path,)
        ).fetchone()
        if row is None:
            return None
        item = self.connection.execute(
            "SELECT version, sha256, body, created_at, message "
            "FROM book_document_versions WHERE document_id=? AND version=?",
            (int(row["id"]), version),
        ).fetchone()
        return None if item is None else dict(item)

    def attach(self, path: str, *, role: str = "attachment") -> None:
        target = Path(path)
        if not target.is_file():
            raise StoreError(f"attachment not found: {target}")
        data = target.read_bytes()
        self.connection.execute(
            "INSERT INTO book_attachments(path, sha256, size, role) "
            "VALUES(?, ?, ?, ?) ON CONFLICT(path) DO UPDATE SET "
            "sha256=excluded.sha256, size=excluded.size, role=excluded.role",
            (
                str(target),
                hashlib.sha256(data).hexdigest(),
                len(data),
                role,
            ),
        )
        self.connection.commit()

    def attachments(self) -> list[dict[str, Any]]:
        rows = self.connection.execute(
            "SELECT path, sha256, size, role "
            "FROM book_attachments ORDER BY path"
        ).fetchall()
        return [dict(row) for row in rows]

    def set_design(self, design_id: str, payload: dict[str, Any]) -> None:
        self.connection.execute(
            "INSERT INTO book_design(id, design_id, payload) VALUES(1, ?, ?) "
            "ON CONFLICT(id) DO UPDATE SET design_id=excluded.design_id, "
            "payload=excluded.payload",
            (design_id, json.dumps(payload, ensure_ascii=False)),
        )
        self.connection.commit()

    def design(self) -> dict[str, Any] | None:
        row = self.connection.execute(
            "SELECT design_id, payload FROM book_design WHERE id=1"
        ).fetchone()
        if row is None:
            return None
        return {
            "design_id": row["design_id"],
            "payload": json.loads(row["payload"]),
        }

    def set_publication(self, payload: dict[str, Any]) -> None:
        self.connection.execute(
            "INSERT INTO book_publication(id, payload) VALUES(1, ?) "
            "ON CONFLICT(id) DO UPDATE SET payload=excluded.payload",
            (json.dumps(payload, ensure_ascii=False),),
        )
        self.connection.commit()

    def publication(self) -> dict[str, Any]:
        row = self.connection.execute(
            "SELECT payload FROM book_publication WHERE id=1"
        ).fetchone()
        return {} if row is None else json.loads(row["payload"])

    @property
    def minigit(self):
        """Return the minigit facade over this store."""
        from epy_books._core._minigit import MiniGit

        return MiniGit(self)

    def close(self) -> None:
        self.connection.close()

    def __enter__(self) -> BookStore:
        return self

    def __exit__(self, *args: object) -> None:
        self.close()
