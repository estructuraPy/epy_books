from __future__ import annotations

from epy_books._core import _i18n


def test_i18n_spanish_default():
    assert _i18n.current_language() in {"es", "en"}
    assert _i18n.text("app") == "ePy Books"
    assert _i18n.text("missing") == "missing"
