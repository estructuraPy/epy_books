"""Common Markdown contract shared by the ePy renderers."""

from __future__ import annotations

import re

from .encoding import repair_spanish

MAX_TABLE_ROWS = 18
MAX_TABLE_COLUMNS = 8


def _fit_row(line: str) -> str:
    cells = line.strip().strip("|").split("|")
    return "|" + "|".join(cells[:MAX_TABLE_COLUMNS]) + "|"


def _split_table(block: list[str]) -> list[list[str]]:
    block = [_fit_row(line) for line in block]
    if len(block) <= MAX_TABLE_ROWS + 2:
        return [block]
    header = block[:2]
    rows = block[2:]
    chunks = [
        rows[i : i + MAX_TABLE_ROWS]
        for i in range(0, len(rows), MAX_TABLE_ROWS)
    ]
    return [header + chunk for chunk in chunks]


def normalize_markdown(text: str) -> str:
    """Return the common Markdown accepted by the ePy renderers."""
    text = repair_spanish(text)
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"\\newpage\s*\n", "\n", text)
    text = re.sub(r"\\tag\{[^}]*\}", "", text)
    lines = text.splitlines()
    out: list[str] = []
    block: list[str] = []
    in_table = False

    def flush_table() -> None:
        nonlocal block, in_table
        if in_table and block:
            for part in _split_table(block):
                out.extend(part)
                out.append("")
        block = []
        in_table = False

    for line in lines:
        is_row = line.strip().startswith("|") and line.strip().endswith("|")
        if is_row:
            block.append(line)
            in_table = True
        else:
            if in_table:
                flush_table()
            out.append(line)
    if in_table:
        flush_table()
    text = "\n".join(out)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip() + "\n"


def issues(text: str) -> list[str]:
    """Return contract violations found in the text."""
    found: list[str] = []
    for line in text.splitlines():
        if line.count("|") > MAX_TABLE_COLUMNS + 1:
            found.append("tabla con demasiadas columnas")
        if re.search(r"[A-Za-zÁÉÍÓÚáéíóúñ]\?[A-Za-zÁÉÍÓÚáéíóúñ]", line):
            found.append("tilde rota")
        if line.startswith("####"):
            found.append("H4 no permitido")
    return sorted(set(found))
