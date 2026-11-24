"""The public book facade: one source, editorial profiles, exports."""

from __future__ import annotations

import json
import shutil
import tempfile
from pathlib import Path
from typing import Any

from epy_books._config._loader import read_epyson
from epy_books._core._archive import ARCHIVE_SUFFIX, pack
from epy_books._core._catalog import (
    BookProfile,
    DesignSpec,
    get_design,
    get_profile,
)
from epy_books._core._cover import render_cover
from epy_books._core._manifest import BookManifest
from epy_books._core._manuscript import format_manuscript
from epy_books._core._preflight import PreflightResult, preflight_pdf
from epy_books._core._renderer import BookRenderer
from epy_books._core._store import BookStore, StoreError
from epy_books._core._validation import ValidationResult, validate_book

CONTENT_GATE_CODES = frozenset(
    {
        "caption.forbidden_source",
        "chapter.placeholder",
        "glyph.unsafe",
        "heading.empty",
        "heading.manual_number",
    }
)


class BookContentError(RuntimeError):
    """Raised when a book cannot be rendered safely."""


def _settings() -> dict[str, Any]:
    return read_epyson("settings")


def _default_profile() -> str:
    return str(_settings().get("default_profile") or "et_submission")


def _default_design() -> str:
    return str(_settings().get("default_design") or "aec_ingenieria")


def _deliver(rendered: Path, target: Path) -> Path:
    target.parent.mkdir(parents=True, exist_ok=True)
    if rendered.resolve() != target.resolve():
        shutil.copy2(rendered, target)
    return target


class Book:
    """One book source that exports editorial and manuscript formats."""

    def __init__(
        self,
        manifest: BookManifest,
        *,
        profile_id: str | None = None,
        design_id: str | None = None,
        store: BookStore | None = None,
    ) -> None:
        """Build a book from a parsed manifest."""
        self.manifest = manifest
        self.store = store
        self._profile = get_profile(profile_id or _default_profile())
        self._design = get_design(design_id or self._profile.design_default)

    @property
    def profile_id(self) -> str:
        """Return the active profile id."""
        return self._profile.id

    @property
    def design_id(self) -> str:
        """Return the active design id."""
        return self._design.id

    @classmethod
    def from_file(
        cls,
        path: str | Path,
        *,
        profile_id: str | None = None,
        design_id: str | None = None,
    ) -> Book:
        """Open a ``.kepy`` store or import an existing ``libro.json``."""
        source = Path(path).resolve()
        if source.suffix.lower() == ".kepy":
            store = BookStore(source)
            raw = store.get_meta("manifest_json")
            if not raw:
                raise StoreError(f"{source.name} has no book manifest")
            manifest = BookManifest.from_dict(json.loads(raw))
            design = store.design()
            return cls(
                manifest,
                profile_id=store.get_meta("profile_id") or profile_id,
                design_id=(
                    str(design["design_id"]) if design else design_id
                ),
                store=store,
            )
        if source.suffix.lower() == ARCHIVE_SUFFIX:
            raise ValueError(
                "a .zepy is a snapshot; unpack it before opening the project"
            )
        manifest = BookManifest.from_file(source)
        return cls(manifest, profile_id=profile_id, design_id=design_id)

    def profile(self, profile_id: str) -> BookProfile:
        """Return one editorial profile."""
        return get_profile(profile_id)

    def design(self, design_id: str) -> DesignSpec:
        """Return one interior design."""
        return get_design(design_id)

    def validate(self, profile_id: str | None = None) -> ValidationResult:
        """Validate this book against an editorial profile."""
        profile = get_profile(profile_id) if profile_id else self._profile
        design = (
            self._design
            if not profile_id
            else get_design(profile.design_default)
        )
        publication = self.store.publication() if self.store else {}
        return validate_book(
            profile=profile,
            design=design,
            root=self.manifest.project_root,
            title=self.manifest.title,
            author=self.manifest.author,
            chapters=[chapter.source for chapter in self.manifest.chapters],
            front_matter=self.manifest.front_matter,
            back_matter=self.manifest.back_matter,
            publication=publication,
            documents=self._bodies(),
        )

    def apply_design(self, design: DesignSpec) -> None:
        """Use a design for subsequent renders and persist it when possible."""
        self._design = design
        if self.store is not None:
            self.store.set_design(design.id, design.to_epy_docs())
            self.store.minigit.commit(f"design {design.id}")

    def render_notes(self, design_id: str, fmt: str) -> list[str]:
        """Return the gaps a render would report without writing files."""
        design = get_design(design_id)
        renderer = BookRenderer(self.manifest, design)
        return renderer.notes

    def text_for(self, source: str | Path) -> str:
        """Return one source document from the store or from disk."""
        path = Path(source)
        bodies = self._bodies() or {}
        text = bodies.get(str(path))
        if text is not None:
            return text
        if path.is_file():
            return path.read_text(encoding="utf-8")
        raise FileNotFoundError(path)

    def _bodies(self) -> dict[str, str] | None:
        if self.store is None:
            return None
        bodies: dict[str, str] = {}
        for source in self.manifest.source_files:
            try:
                relative = source.relative_to(self.manifest.project_root)
            except ValueError:
                relative = Path(source.name)
            record = self.store.document(str(relative))
            if record is not None:
                bodies[str(source)] = str(record["body"])
        return bodies

    def _render_to(
        self,
        target: Path,
        *,
        design_id: str | None,
        formats: tuple[str, ...],
    ) -> dict[str, Path]:
        blocked = [
            item
            for item in self.validate()
            if item.code in CONTENT_GATE_CODES
        ]
        if blocked:
            detail = "\n".join(
                f"{item.code}: {item.message}" for item in blocked
            )
            raise BookContentError(detail)
        design = get_design(design_id) if design_id else self._design
        with tempfile.TemporaryDirectory(prefix="epy_books_") as hold:
            produced = BookRenderer(
                self.manifest, design, bodies=self._bodies()
            ).render(hold, formats=formats)
            delivered: dict[str, Path] = {}
            for fmt in formats:
                rendered = produced.get(fmt)
                if rendered is None:
                    continue
                delivered[fmt] = _deliver(
                    rendered, target.with_suffix(f".{fmt}")
                )
            return delivered

    def _check_pdf(self, path: Path) -> None:
        try:
            import pymupdf
        except ImportError:
            return
        with pymupdf.open(path) as document:
            text = "\n".join(page.get_text() for page in document)
        if "??" in text:
            raise BookContentError("unresolved cross-reference in the PDF")
        if any(glyph in text for glyph in "□�"):
            raise BookContentError("replacement glyph in the PDF")

    def to_pdf(
        self, path: str | Path, *, design: str | None = None
    ) -> Path:
        """Render the designed PDF."""
        result = self._render_to(
            Path(path),
            design_id=design,
            formats=("pdf",),
        )
        rendered = result.get("pdf")
        if rendered is None:
            raise RuntimeError("epy_docs did not produce a PDF")
        self._check_pdf(rendered)
        return rendered

    def to_docx(
        self, path: str | Path, *, design: str | None = None
    ) -> Path:
        """Render the designed DOCX."""
        result = self._render_to(
            Path(path),
            design_id=design,
            formats=("docx",),
        )
        rendered = result.get("docx")
        if rendered is None:
            raise RuntimeError("epy_docs did not produce a DOCX")
        return rendered

    def to_html(
        self, path: str | Path, *, design: str | None = None
    ) -> Path:
        """Render the designed HTML."""
        result = self._render_to(
            Path(path),
            design_id=design,
            formats=("html",),
        )
        rendered = result.get("html")
        if rendered is None:
            raise RuntimeError("epy_docs did not produce an HTML file")
        return rendered

    def to_epub(
        self, path: str | Path, *, design: str | None = None
    ) -> Path:
        """Render the book as EPUB."""
        result = self._render_to(
            Path(path),
            design_id=design,
            formats=("epub",),
        )
        rendered = result.get("epub")
        if rendered is None:
            raise RuntimeError("epy_docs did not produce an EPUB")
        return rendered

    def to_cover(
        self, path: str | Path, *, design: str | None = None
    ) -> Path:
        """Generate a front cover for the selected design."""
        selected = get_design(design) if design else self._design
        return render_cover(self.manifest, selected, path)

    def preflight(
        self, path: str | Path, *, design: str | None = None
    ) -> PreflightResult:
        """Check a rendered PDF against the selected design."""
        selected = get_design(design) if design else self._design
        return preflight_pdf(path, selected)

    def to_manuscript(self, path: str | Path) -> Path:
        """Render the plain manuscript document."""
        result = self._render_to(
            Path(path),
            design_id="et_manuscrito",
            formats=("docx",),
        )
        rendered = result.get("docx")
        if rendered is None:
            raise RuntimeError("epy_docs did not produce the manuscript")
        return format_manuscript(rendered)

    def to_store(self, path: str | Path) -> Path:
        """Import this book into a new ``.kepy`` store."""
        target = Path(path)
        if target.exists():
            raise StoreError(f"store already exists: {target}")
        store = BookStore(target, create=True)
        try:
            for source in self.manifest.source_files:
                store.upsert_document(
                    str(source.relative_to(self.manifest.project_root)),
                    source.stem,
                    source.read_text(encoding="utf-8"),
                    message="import",
                )
            store.set_meta("title", self.manifest.title)
            store.set_meta("author", self.manifest.author)
            store.set_meta("profile_id", self._profile.id)
            store.set_meta(
                "manifest_json",
                json.dumps(self.manifest.to_dict(), ensure_ascii=False),
            )
            store.set_design(self._design.id, self._design.to_epy_docs())
            store.set_publication({})
            figures = self.manifest.figures_dir
            if figures and figures.is_dir():
                for figure in figures.rglob("*"):
                    if figure.is_file():
                        store.attach(str(figure), role="figure")
            store.minigit.commit("import")
        finally:
            store.close()
        self.store = BookStore(target)
        return target

    def to_archive(self, path: str | Path) -> Path:
        """Pack this book's store into a ``.zepy`` snapshot."""
        if self.store is None:
            raise StoreError("save the book to a .kepy before packing it")
        target = Path(path)
        pack(self.store.path, target)
        return target

    def close(self) -> None:
        """Close the underlying ``.kepy`` connection, when open."""
        if self.store is not None:
            self.store.close()

    def __enter__(self) -> Book:
        return self

    def __exit__(self, *args: object) -> None:
        self.close()

    def commit(self, message: str) -> str:
        """Commit the current store."""
        if self.store is None:
            raise StoreError("this book has no .kepy store")
        return self.store.minigit.commit(message)

    def history(self, limit: int = 20) -> list[dict[str, Any]]:
        """Return the project history."""
        if self.store is None:
            return []
        return self.store.minigit.log(limit)

    def restore(self, commit_id: str) -> list[str]:
        """Restore a commit."""
        if self.store is None:
            raise StoreError("this book has no .kepy store")
        return self.store.minigit.restore(commit_id)

    def draft(
        self,
        *,
        provider: str = "deepseek",
        model: str | None = None,
        prompt: str = "generate-from-brief",
        output: str | Path | None = None,
    ) -> list[Path]:
        """Draft the book with epy_draft when it is installed."""
        try:
            from epy_draft import DraftProject
        except ImportError as exc:
            raise RuntimeError(
                "drafting requires epy_draft installed"
            ) from exc
        project_root = (
            self.store.path.parent
            if self.store
            else self.manifest.project_root
        )
        project = DraftProject(project_root)
        target = Path(
            output
            or self.manifest.project_root / "coordinacion" / "draft"
        )
        result = project.run(
            prompt,
            self.manifest.source_files,
            output=target,
            provider=provider,
            model=model,
            answer_language="spanish",
        )
        if int(result.get("ok", 0)) < 1:
            raise RuntimeError(f"epy_draft did not draft the book: {result}")
        return sorted(target.glob("*.md"))
