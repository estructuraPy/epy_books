from __future__ import annotations

from pathlib import Path

from epy_books import get_design, get_profile
from epy_books._core._validation import (
    Severity,
    ValidationResult,
    validate_book,
)


def _validate(tmp_path: Path, **overrides):
    chapter = tmp_path / "c.md"
    body = overrides.pop("body", "# C\n\nTexto\n")
    chapter.write_text(body, encoding="utf-8")
    profile = get_profile("et_submission")
    return validate_book(
        profile=profile,
        design=get_design("aec_ingenieria"),
        root=tmp_path,
        title=overrides.pop("title", "Libro"),
        author=overrides.pop("author", "Autor"),
        chapters=overrides.pop("chapters", [chapter]),
        front_matter=overrides.pop("front_matter", None),
        back_matter=overrides.pop("back_matter", []),
        publication=overrides.pop("publication", {}),
    )


def test_validate_reports_missing_fields(tmp_path: Path):
    result = _validate(tmp_path, title="", author="", chapters=[])
    codes = {item.code for item in result}
    assert "title.missing" in codes
    assert "author.missing" in codes
    assert "chapters.missing" in codes
    assert result.ok is False
    assert len(result) > 0
    assert result.messages()
    assert bool(result) is True


def test_validate_errors_and_warnings(tmp_path: Path):
    result = _validate(
        tmp_path,
        chapters=[tmp_path / "missing.md"],
        body="# C\n\nTODO\n",
        front_matter=tmp_path / "missing-front.md",
        back_matter=[tmp_path / "missing-back.md"],
        publication={},
    )
    codes = {item.code for item in result}
    assert "chapter.missing" in codes
    assert "front_matter.missing" in codes
    assert "back_matter.missing" in codes
    assert "publication.ai_declaration" in codes
    assert "publication.permissions" in codes


def test_validate_empty_chapter_and_mirror_warning(tmp_path: Path):
    chapter = tmp_path / "empty.md"
    chapter.write_text("", encoding="utf-8")
    result = validate_book(
        profile=get_profile("et_submission"),
        design=get_design("aec_arquitectura"),
        root=tmp_path,
        title="Libro",
        author="Autor",
        chapters=[chapter],
        front_matter=None,
        back_matter=[],
        publication={"ai_declaration": "x", "permissions": ["x"]},
    )
    assert any(item.code == "chapter.empty" for item in result)


def test_validation_result_helpers():
    result = ValidationResult("p", "P")
    result.add("x", Severity.INFO, "mensaje")
    assert str(result.warnings[0]) == "[info] mensaje"
    assert result.ok is True
    assert len(result) == 1
