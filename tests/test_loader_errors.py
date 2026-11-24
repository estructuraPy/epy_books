from __future__ import annotations

import json
from pathlib import Path

import pytest

from epy_books._config import _loader


def test_loader_rejects_malformed_catalog(tmp_path: Path, monkeypatch):
    (tmp_path / "bad.epyson").write_text("[]", encoding="utf-8")
    monkeypatch.setattr(_loader, "config_dir", lambda: tmp_path)
    with pytest.raises(ValueError):
        _loader.read_epyson("bad")


def test_loader_rejects_missing_header(tmp_path: Path, monkeypatch):
    (tmp_path / "bad.epyson").write_text("{}", encoding="utf-8")
    monkeypatch.setattr(_loader, "config_dir", lambda: tmp_path)
    with pytest.raises(ValueError):
        _loader.read_epyson("bad")


def test_loader_rejects_id_mismatch(tmp_path: Path, monkeypatch):
    (tmp_path / "bad.epyson").write_text(
        json.dumps(
            {
                "config_id": "other",
                "version": "1",
                "description": "x",
                "audit_status": "n_a",
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(_loader, "config_dir", lambda: tmp_path)
    with pytest.raises(ValueError):
        _loader.read_epyson("bad")
