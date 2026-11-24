"""Read the .epyson catalogs bundled under ``_config``."""

from __future__ import annotations

import json
from importlib import resources
from pathlib import Path
from typing import Any

_CONFIG_PACKAGE = "epy_books._config"
_REQUIRED_KEYS = ("config_id", "version", "description", "audit_status")


def config_dir() -> Path:
    """Return the package directory that holds the .epyson catalogs."""
    return Path(__file__).resolve().parent


def read_epyson(name: str) -> dict[str, Any]:
    """Read one bundled catalog and validate its standard header."""
    path = config_dir() / f"{name}.epyson"
    with open(path, encoding="utf-8") as handle:
        data = json.load(handle)
    if not isinstance(data, dict):
        raise ValueError(f"{path.name} must contain a JSON object")
    for key in _REQUIRED_KEYS:
        if key not in data:
            raise ValueError(f"{path.name} is missing {key!r}")
    if data["config_id"] != path.stem:
        raise ValueError(
            f"{path.name} declares config_id={data['config_id']!r}; "
            f"expected {path.stem!r}"
        )
    return data


def read_asset_text(*parts: str) -> str:
    """Read a bundled text asset under ``_config``."""
    target = config_dir().joinpath(*parts)
    if target.is_file():
        return target.read_text(encoding="utf-8")
    anchor = resources.files(_CONFIG_PACKAGE)
    for part in parts:
        anchor = anchor.joinpath(part)
    return anchor.read_text(encoding="utf-8")
