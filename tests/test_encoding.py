from __future__ import annotations

import pytest

from epy_books._core._encoding import (
    assert_clean,
    broken_accents,
    repair_spanish,
)


def test_repair_spanish_tokens():
    assert "Ecuación" in repair_spanish("Ecuaci?n")
    assert "relación" in repair_spanish("relaci?n")
    assert repair_spanish("secci?n") == "sección"


def test_assert_clean_rejects_broken_accents():
    assert broken_accents("funci?n")
    with pytest.raises(ValueError):
        assert_clean("funci?n")
    assert_clean("función")
