"""Generate figures and record their source."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch

NAVY = "#00243f"
GREEN = "#576a3d"
SAND = "#c0ab87"
INK = "#0b0c0c"


@dataclass(frozen=True)
class FigureSpec:
    """Description of one generated figure."""

    filename: str
    title: str
    boxes: tuple[str, ...]
    caption: str


def render_flow(spec: FigureSpec, out_dir: Path) -> Path:
    """Render a flow diagram and record its metadata."""
    out_dir.mkdir(parents=True, exist_ok=True)
    fig, ax = plt.subplots(figsize=(8, 4.5), dpi=200)
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 5.6)
    ax.axis("off")
    ax.set_title(
        spec.title,
        fontsize=14,
        color=NAVY,
        fontweight="bold",
        loc="left",
        pad=12,
    )
    n = max(1, len(spec.boxes))
    width = min(1.8, 8.6 / n)
    gap = (8.8 - width * n) / max(1, n - 1) if n > 1 else 0
    for i, label in enumerate(spec.boxes):
        x = 0.6 + i * (width + gap)
        y = 2.7
        patch = FancyBboxPatch(
            (x, y),
            width,
            0.95,
            boxstyle="round,pad=0.05,rounding_size=0.08",
            fc=SAND if i % 2 == 0 else "#ffffff",
            ec=NAVY,
            lw=1.3,
        )
        ax.add_patch(patch)
        ax.text(
            x + width / 2,
            y + 0.47,
            label,
            ha="center",
            va="center",
            fontsize=8,
            color=INK,
        )
        if i < n - 1:
            ax.add_patch(
                FancyArrowPatch(
                    (x + width, y + 0.47),
                    (x + width + gap, y + 0.47),
                    arrowstyle="-|>",
                    mutation_scale=12,
                    lw=1.3,
                    color=GREEN,
                )
            )
    ax.text(5, 1.2, spec.caption, ha="center", fontsize=9, color=NAVY)
    target = out_dir / spec.filename
    fig.tight_layout()
    fig.savefig(target, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    meta = out_dir / "FIGURAS.json"
    records: list[dict[str, str]] = (
        json.loads(meta.read_text(encoding="utf-8")) if meta.exists() else []
    )
    records.append(
        {
            "file": spec.filename,
            "title": spec.title,
            "caption": spec.caption,
            "source": "Ver pie de figura",
        }
    )
    meta.write_text(
        json.dumps(records, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    return target
