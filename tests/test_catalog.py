from __future__ import annotations

import pytest

from epy_books import (
    DesignSpec,
    available_designs,
    available_profiles,
    get_design,
    get_profile,
)


def test_profiles_are_available():
    profiles = available_profiles()
    assert ("et_submission", "Editorial Tecnologica del TEC") in profiles
    assert any(item[0] == "aec_ingenieria" for item in profiles)


def test_designs_are_available():
    designs = available_designs()
    assert any(item[0] == "aec_ingenieria" for item in designs)


def test_get_profile_returns_typed_object():
    profile = get_profile("et_submission")
    assert profile.manuscript["font_family"] == "Arial"
    assert profile.validation["require_ai_declaration"] is True


def test_get_design_returns_typed_object():
    design = get_design("aec_ingenieria")
    assert isinstance(design, DesignSpec)
    assert design.page_size == (8.5, 11.0)
    assert design.mirrored is True


def test_unknown_ids_name_the_failure():
    with pytest.raises(KeyError):
        get_profile("does-not-exist")
    with pytest.raises(KeyError):
        get_design("does-not-exist")
