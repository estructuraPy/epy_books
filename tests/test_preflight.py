from __future__ import annotations

from pathlib import Path

import pymupdf

from epy_books import get_design
from epy_books._core._preflight import preflight_pdf


def test_preflight_accepts_expected_page_size(tmp_path: Path):
    pdf = tmp_path / "ok.pdf"
    document = pymupdf.open()
    page = document.new_page(width=612, height=792)
    page.insert_text((72, 72), "Contenido")
    document.save(pdf)
    document.close()
    result = preflight_pdf(pdf, get_design("aec_ingenieria"))
    assert result.ok
    assert result.pages == 1


def test_preflight_rejects_wrong_size_and_blank(tmp_path: Path):
    pdf = tmp_path / "bad.pdf"
    document = pymupdf.open()
    document.new_page(width=504, height=720)
    document.new_page(width=504, height=720)
    document.save(pdf)
    document.close()
    result = preflight_pdf(pdf, get_design("aec_ingenieria"))
    assert not result.ok
    assert any("ancho" in item for item in result.failures)
