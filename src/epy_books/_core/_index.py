"""Build a section-level analytic index from Markdown headings."""

from __future__ import annotations

import re

_HEADING = re.compile(r"^(#{2,3})\s+(.+?)\s*$")
_UNSAFE = re.compile(r"[{}\\%&#$_]")


def _term(text: str) -> str:
    clean = re.sub(r"\s*\{[^}]*\}\s*$", "", text).strip()
    clean = _UNSAFE.sub("", clean)
    return clean


def annotate_headings(markdown: str) -> str:
    r"""Insert ``\\index{}`` markers after H2/H3 headings."""
    lines: list[str] = []
    for line in markdown.splitlines():
        match = _HEADING.match(line.strip())
        lines.append(line)
        if match:
            term = _term(match.group(2))
            if term:
                lines.append(f"\\index{{{term}}}")
    return "\n".join(lines)
