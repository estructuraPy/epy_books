"""Repair and reject broken Spanish accents."""

from __future__ import annotations

import re

REPLACEMENTS = {
    "Ecuaci?n": "Ecuación",
    "relaci?n": "relación",
    "continuaci?n": "continuación",
    "funci?n": "función",
    "secci?n": "sección",
    "definici?n": "definición",
    "condici?n": "condición",
    "soluci?n": "solución",
    "aplicaci?n": "aplicación",
    "verificaci?n": "verificación",
    "medici?n": "medición",
    "documentaci?n": "documentación",
    "informaci?n": "información",
    "investigaci?n": "investigación",
    "construcci?n": "construcción",
    "producci?n": "producción",
    "introducci?n": "introducción",
    "conclusi?n": "conclusión",
    "decisi?n": "decisión",
    "precisi?n": "precisión",
    "t?cnica": "técnica",
    "t?cnico": "técnico",
    "m?todo": "método",
    "m?todos": "métodos",
    "l?mite": "límite",
    "l?mites": "límites",
    "c?lculo": "cálculo",
    "f?sica": "física",
    "f?sico": "físico",
    "matem?tica": "matemática",
    "matem?tico": "matemático",
    "an?lisis": "análisis",
    "din?mica": "dinámica",
    "mec?nica": "mecánica",
    "est?tica": "estática",
    "pr?ctica": "práctica",
    "f?rmula": "fórmula",
    "n?mero": "número",
    "n?meros": "números",
    "p?gina": "página",
    "p?ginas": "páginas",
    "m?ximo": "máximo",
    "m?nimo": "mínimo",
    "s?mbolo": "símbolo",
    "s?mbolos": "símbolos",
    "?ndice": "índice",
    "?nico": "único",
    "?nica": "única",
    "?rea": "área",
    "?ngulo": "ángulo",
    "d?as": "días",
    "d?a": "día",
}


def repair_spanish(text: str) -> str:
    """Repair the common `?n` corruption without inventing words."""
    text = re.sub(r"(?<=[A-Za-zÁÉÍÓÚáéíóúñ])\?n\b", "ón", text)
    for bad, good in REPLACEMENTS.items():
        text = text.replace(bad, good)
    return text


def broken_accents(text: str) -> list[str]:
    """Return broken accent tokens."""
    return sorted(
        set(re.findall(r"[A-Za-zÁÉÍÓÚáéíóúñ]\?[A-Za-zÁÉÍÓÚáéíóúñ]", text))
    )


def assert_clean(text: str) -> None:
    """Reject text that still contains broken accents."""
    broken = broken_accents(text)
    if broken:
        raise ValueError(f"tildes rotas: {broken[:10]}")
