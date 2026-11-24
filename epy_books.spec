# -*- mode: python ; coding: utf-8 -*-
from pathlib import Path

root = Path(SPECPATH)
src = root / "src"

a = Analysis(
    [str(src / "epy_books" / "app.py")],
    pathex=[str(src)],
    binaries=[],
    datas=[
        (str(src / "epy_books" / "_config"), "epy_books/_config"),
    ],
    hiddenimports=["epy_docs", "epy_draft"],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)
pyz = PYZ(a.pure)
exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="epy_books",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name="epy_books",
)
