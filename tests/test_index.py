from __future__ import annotations

from epy_books._core._index import annotate_headings


def test_annotate_headings():
    text = "# Libro\n\n## Capitulo uno\n\n### Detalle\n"
    result = annotate_headings(text)
    assert "\\index{Capitulo uno}" in result
    assert "\\index{Detalle}" in result
    assert result.count("\\index{") == 2


def test_annotate_strips_anchor_and_unsafe_chars():
    result = annotate_headings("## Capacidad {#sec-cap}\n")
    assert "\\index{Capacidad}" in result
