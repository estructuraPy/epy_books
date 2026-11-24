"""Generate a clean editorial cover from the book metadata."""

from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

from epy_books._core._catalog import DesignSpec
from epy_books._core._manifest import BookManifest

_DPI = 300
_FONT_CANDIDATES = (
    r"C:\Windows\Fonts\arial.ttf",
    r"C:\Windows\Fonts\calibri.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
)


def _font(size: int, *, bold: bool = False) -> ImageFont.FreeTypeFont:
    candidates = (
        (r"C:\Windows\Fonts\arialbd.ttf",)
        if bold
        else _FONT_CANDIDATES
    )
    for candidate in candidates:
        if Path(candidate).is_file():
            return ImageFont.truetype(candidate, size)
    return ImageFont.load_default()


def _hex(color: list[int] | tuple[int, ...]) -> str:
    values = tuple(int(value) for value in color[:3])
    return "#" + "".join(f"{value:02x}" for value in values)


def _wrap(
    draw: ImageDraw.ImageDraw,
    text: str,
    font: ImageFont.FreeTypeFont,
    width: int,
) -> list[str]:
    words = text.split()
    lines: list[str] = []
    current = ""
    for word in words:
        candidate = f"{current} {word}".strip()
        if draw.textlength(candidate, font=font) <= width:
            current = candidate
        else:
            if current:
                lines.append(current)
            current = word
    if current:
        lines.append(current)
    return lines


def render_cover(
    manifest: BookManifest,
    design: DesignSpec,
    target: str | Path,
) -> Path:
    """Draw a front cover at the design's page size and save it."""
    width = int(design.page_size[0] * _DPI)
    height = int(design.page_size[1] * _DPI)
    paper = _hex(design.palette.get("paper", [255] * 3))
    image = Image.new("RGB", (width, height), paper)
    draw = ImageDraw.Draw(image)
    accent = _hex(design.palette.get("accent", [0, 36, 63]))
    secondary = _hex(design.palette.get("secondary", [87, 106, 61]))
    ink = _hex(design.palette.get("ink", [10, 10, 10]))
    margin = int(width * 0.11)

    draw.rectangle((0, 0, width, int(height * 0.035)), fill=accent)
    draw.rectangle(
        (
            margin,
            int(height * 0.12),
            margin + int(width * 0.16),
            int(height * 0.128),
        ),
        fill=secondary,
    )

    title_font = _font(int(width * 0.075), bold=True)
    subtitle_font = _font(int(width * 0.035))
    author_font = _font(int(width * 0.028))
    imprint_font = _font(int(width * 0.018))

    y = int(height * 0.18)
    for line in _wrap(draw, manifest.title, title_font, width - 2 * margin):
        draw.text((margin, y), line, font=title_font, fill=accent)
        y += int(width * 0.09)
    y += int(height * 0.02)
    if manifest.subtitle:
        for line in _wrap(
            draw, manifest.subtitle, subtitle_font, width - 2 * margin
        ):
            draw.text((margin, y), line, font=subtitle_font, fill=ink)
            y += int(width * 0.045)
    y += int(height * 0.05)
    draw.text(
        (margin, y),
        manifest.author or "Autor",
        font=author_font,
        fill=ink,
    )

    draw.text(
        (margin, height - int(height * 0.09)),
        "Editorial Tecnologica del TEC",
        font=imprint_font,
        fill=secondary,
    )
    target_path = Path(target)
    target_path.parent.mkdir(parents=True, exist_ok=True)
    if target_path.suffix.lower() == ".pdf":
        image.save(target_path, "PDF", resolution=_DPI)
    else:
        image.save(target_path)
    return target_path
