from __future__ import annotations

import epy_books


def test_public_names():
    for name in (
        "Book",
        "BookProfile",
        "DesignSpec",
        "ValidationResult",
        "available_profiles",
        "available_designs",
        "get_profile",
        "get_design",
        "get_theme",
        "themes",
    ):
        assert hasattr(epy_books, name), name


def test_version_is_published():
    assert epy_books.__version__
