"""Editorial and design catalogs for epy_books."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, cast

from epy_books._config._loader import read_epyson


@dataclass(frozen=True)
class BookProfile:
    """One editorial target and the gates a book must satisfy for it."""

    id: str
    name: str
    description: str
    language: str
    kind: str
    design_default: str
    output_formats: tuple[str, ...]
    manuscript: dict[str, Any]
    required_front_matter: tuple[str, ...]
    required_back_matter: tuple[str, ...]
    validation: dict[str, Any]

    @classmethod
    def from_row(cls, row: dict[str, Any]) -> BookProfile:
        """Build and validate one profile from catalog data."""
        profile = cls(
            id=str(row["id"]).strip(),
            name=str(row.get("name") or row["id"]).strip(),
            description=str(row.get("description") or "").strip(),
            language=str(row.get("language") or "es"),
            kind=str(row.get("kind") or "general"),
            design_default=str(row.get("design_default") or "general"),
            output_formats=tuple(
                str(item) for item in row.get("output_formats") or ()
            ),
            manuscript=cast("dict[str, Any]", row.get("manuscript") or {}),
            required_front_matter=tuple(
                str(item) for item in row.get("required_front_matter") or ()
            ),
            required_back_matter=tuple(
                str(item) for item in row.get("required_back_matter") or ()
            ),
            validation=cast("dict[str, Any]", row.get("validation") or {}),
        )
        profile.validate()
        return profile

    def validate(self) -> None:
        """Refuse a profile with no identity or no output format."""
        if not self.id:
            raise ValueError("a book profile needs an id")
        if not self.name:
            raise ValueError(f"{self.id}: name is empty")
        if not self.output_formats:
            raise ValueError(f"{self.id}: output_formats is empty")
        if "docx" in self.output_formats and not self.manuscript:
            raise ValueError(f"{self.id}: docx requires manuscript settings")

    def get(self, key: str, default: Any = None) -> Any:
        """Return a raw catalog field with a default."""
        return getattr(self, key, default)


@dataclass(frozen=True)
class DesignSpec:
    """One interior design: page, margins, typography and components."""

    id: str
    name: str
    description: str
    layout_style: str
    page: dict[str, Any]
    margins: dict[str, Any]
    typography: dict[str, Any]
    palette: dict[str, Any]
    components: dict[str, Any]

    @classmethod
    def from_row(cls, row: dict[str, Any]) -> DesignSpec:
        """Build and validate one design from catalog data."""
        design = cls(
            id=str(row["id"]).strip(),
            name=str(row.get("name") or row["id"]).strip(),
            description=str(row.get("description") or "").strip(),
            layout_style=str(row.get("layout_style") or "academic"),
            page=cast("dict[str, Any]", row.get("page") or {}),
            margins=cast("dict[str, Any]", row.get("margins") or {}),
            typography=cast("dict[str, Any]", row.get("typography") or {}),
            palette=cast("dict[str, Any]", row.get("palette") or {}),
            components=cast("dict[str, Any]", row.get("components") or {}),
        )
        design.validate()
        return design

    def validate(self) -> None:
        """Refuse a design with unusable page geometry."""
        if not self.id:
            raise ValueError("a design needs an id")
        if not self.name:
            raise ValueError(f"{self.id}: name is empty")
        width = float(self.page.get("width_in") or 0)
        height = float(self.page.get("height_in") or 0)
        if width <= 0 or height <= 0:
            raise ValueError(f"{self.id}: page width and height are required")
        for key in ("top_in", "bottom_in", "inside_in", "outside_in"):
            if float(self.margins.get(key) or 0) < 0:
                raise ValueError(f"{self.id}: margin {key} is negative")
        if float(self.typography.get("body_size_pt") or 0) <= 0:
            raise ValueError(f"{self.id}: body_size_pt is required")

    @property
    def page_size(self) -> tuple[float, float]:
        """Return the page size in inches."""
        return (
            float(self.page["width_in"]),
            float(self.page["height_in"]),
        )

    @property
    def mirrored(self) -> bool:
        """Whether the margins mirror across facing pages."""
        return bool(self.margins.get("mirror", False))

    def to_epy_docs(self) -> dict[str, Any]:
        """Return the public BookDesign payload consumed by epy_docs."""
        return {
            "design_id": self.id,
            "layout_style": self.layout_style,
            "page": dict(self.page),
            "margins": dict(self.margins),
            "typography": dict(self.typography),
            "palette": dict(self.palette),
            "components": dict(self.components),
        }


def _rows(name: str, key: str) -> list[dict[str, Any]]:
    data = read_epyson(name)
    rows = data.get(key)
    if not isinstance(rows, list):
        raise ValueError(f"{name}.epyson must contain a {key!r} list")
    return [cast("dict[str, Any]", row) for row in rows]


def list_profiles() -> list[BookProfile]:
    """Return every bundled editorial profile."""
    return [BookProfile.from_row(row) for row in _rows("profiles", "profiles")]


def list_designs() -> list[DesignSpec]:
    """Return every bundled design."""
    return [DesignSpec.from_row(row) for row in _rows("designs", "designs")]


def available_profiles() -> list[tuple[str, str]]:
    """Return ``(id, name)`` for every profile."""
    return [(profile.id, profile.name) for profile in list_profiles()]


def available_designs() -> list[tuple[str, str]]:
    """Return ``(id, name)`` for every design."""
    return [(design.id, design.name) for design in list_designs()]


def get_profile(profile_id: str) -> BookProfile:
    """Return one profile by id, naming the known ids when absent."""
    wanted = profile_id.strip()
    profiles = list_profiles()
    for profile in profiles:
        if profile.id == wanted:
            return profile
    known = ", ".join(profile.id for profile in profiles)
    raise KeyError(f"unknown book profile {wanted!r}; known: {known}")


def get_design(design_id: str) -> DesignSpec:
    """Return one design by id, naming the known ids when absent."""
    wanted = design_id.strip()
    designs = list_designs()
    for design in designs:
        if design.id == wanted:
            return design
    known = ", ".join(design.id for design in designs)
    raise KeyError(f"unknown book design {wanted!r}; known: {known}")
