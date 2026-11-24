from __future__ import annotations

import pytest

import epy_books
from epy_books._core import themes
from epy_books.epy_studio_connect import (
    Handoff,
    StudioConnectError,
    available,
    command,
    handoff,
    launch_hint,
    manifest,
    open_app,
    register,
    unregister,
)


def test_theme_surface():
    assert "aec_ingenieria" in themes.names()
    assert themes.get("aec_ingenieria")["design_id"] == "aec_ingenieria"
    with pytest.raises(KeyError):
        themes.get("missing")
    theme = epy_books.get_theme("aec_ingenieria")
    assert theme["design_id"] == "aec_ingenieria"
    assert epy_books.themes is themes


def test_studio_manifest_and_registration():
    entry = manifest()
    assert entry.app_id == "epy_books"
    assert entry.register == "none"
    assert register([]) == [
        "epy_books: claims no document type; registered in Studio as an "
        "application."
    ]
    assert unregister() == [
        "epy_books: no document type registration to remove."
    ]
    assert launch_hint() == {
        "app_id": "epy_books",
        "entry_point": "epy_books.app",
    }
    assert available() is True
    assert open_app() is None
    assert command() == ["epy_books", "--entry", "epy_books.app"]


def test_handoff_contract():
    assert handoff({"path": "libro.kepy"}) == Handoff("libro.kepy")
    with pytest.raises(StudioConnectError):
        handoff({})
