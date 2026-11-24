"""Build the epy_books application bundle with PyInstaller."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def main() -> int:
    """Run PyInstaller against epy_books.spec."""
    command = [
        sys.executable,
        "-m",
        "PyInstaller",
        "--noconfirm",
        str(ROOT / "epy_books.spec"),
    ]
    return subprocess.run(command, cwd=ROOT, check=False).returncode


if __name__ == "__main__":
    raise SystemExit(main())
