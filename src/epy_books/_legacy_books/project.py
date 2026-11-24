"""A book produced chapter by chapter under a quality gate."""

from __future__ import annotations

import os
import re
from pathlib import Path

from epy_draft._api import DraftProject

from .book import BookQualityError, check_citations
from .book import build as build_book
from .contract import normalize_markdown
from .encoding import broken_accents


class BookProject:
    """A book produced chapter by chapter under a quality gate."""

    def __init__(
        self,
        root: str | Path,
        title: str,
        stem: str,
        author: str = "",
    ) -> None:
        """Create a staged book project."""
        self.root = Path(root)
        self.title = title
        self.stem = stem
        self.author = author
        self.draft = DraftProject(self.root / "draft")

    def generate(
        self,
        briefs: list[Path],
        *,
        prompt: str = "session-10k",
        provider: str | None = None,
        model: str | None = None,
    ) -> list[Path]:
        """Generate the six sessions."""
        outputs: list[Path] = []
        out = self.root / "sessions"
        provider = provider or os.environ.get("EPY_DRAFT_PROVIDER", "")
        model = model or os.environ.get("EPY_DRAFT_MODEL", "")
        if not provider or not model:
            raise BookQualityError(
                "configure EPY_DRAFT_PROVIDER y EPY_DRAFT_MODEL"
            )
        for brief in briefs:
            result = self.draft.run(
                prompt,
                brief,
                output=out,
                provider=provider,
                model=model,
                answer_language="spanish",
            )
            if result.get("ok", 0) != 1:
                raise BookQualityError(f"no se gener? {brief.name}: {result}")
            produced = out / brief.name
            if not produced.exists():
                raise BookQualityError(f"falta la salida de {brief.name}")
            text = normalize_markdown(produced.read_text(encoding="utf-8"))
            broken = broken_accents(text)
            if broken:
                raise BookQualityError(
                    f"{brief.name}: tildes rotas {broken[:8]}"
                )
            produced.write_text(text, encoding="utf-8")
            words = len(text.split())
            h2 = len(re.findall(r"^## ", text, re.M))
            h3 = len(re.findall(r"^### ", text, re.M))
            if words < 10000 or h2 < 7 or h3 < 20:
                raise BookQualityError(
                    f"{brief.name}: {words} palabras, {h2} H2, {h3} H3"
                )
            if check_citations(text):
                raise BookQualityError(f"{brief.name}: citas sin resolver")
            outputs.append(produced)
        return outputs

    def compile(
        self,
        sessions: list[Path],
        *,
        bibliography: Path,
        csl: Path,
        chapters: list[str],
        min_pages: int = 200,
    ) -> Path:
        """Compile the generated book."""
        return build_book(
            title=self.title,
            sessions=sessions,
            output_dir=self.root / "build",
            stem=self.stem,
            bibliography=bibliography,
            csl=csl,
            chapter_titles=chapters,
            author=self.author,
            min_pages=min_pages,
        )
