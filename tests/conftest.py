from __future__ import annotations

import json
from pathlib import Path

import pytest


@pytest.fixture()
def project(tmp_path: Path) -> Path:
    """Create a minimal book project with one chapter."""
    content = tmp_path / "libro" / "contenido"
    content.mkdir(parents=True)
    (content / "Frontmatter.md").write_text(
        "# Prologo\n\nTexto del prologo.\n", encoding="utf-8"
    )
    (content / "Cap01_Book01.md").write_text(
        "# Capitulo uno\n\nTexto del capitulo.\n", encoding="utf-8"
    )
    (content / "Referencias.md").write_text(
        "# Referencias\n\n- Referencia uno.\n", encoding="utf-8"
    )
    coordination = tmp_path / "coordinacion"
    coordination.mkdir()
    (coordination / "libro.json").write_text(
        json.dumps(
            {
                "libro": {
                    "codigo": "LIB01",
                    "titulo": "Libro de prueba",
                    "subtitulo": "Piloto",
                    "autor": "Autora de prueba",
                    "stem": "Libro_Prueba",
                    "idioma": "es",
                },
                "capitulos": [
                    {
                        "n": 1,
                        "titulo": "Capitulo uno",
                        "fuente": "libro/contenido/Cap01_Book01.md",
                    }
                ],
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    return tmp_path
