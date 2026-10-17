from pathlib import Path


project_root = Path(SPECPATH).parent
src_root = project_root / "src"

datas = [
    (str(project_root / "vendor" / "tesseract"), "vendor/tesseract"),
    (str(src_root / "rox_overlay" / "assets"), "rox_overlay/assets"),
    (str(project_root / "README.md"), "."),
]

a = Analysis(
    [str(src_root / "rox_overlay" / "app.py")],
    pathex=[str(src_root)],
    binaries=[],
    datas=datas,
    hiddenimports=["windows_capture", "mss"],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        "PySide6.QtWebEngineCore",
        "PySide6.QtWebEngineWidgets",
        "PySide6.QtPdf",
        "PySide6.QtPdfWidgets",
        "pytest",
        "tkinter",
    ],
    noarchive=False,
    optimize=1,
)
# The host workspace exposes Poppler's ICU 78 on PATH. PyInstaller otherwise
# bundles its icuuc.dll beside Qt, where it shadows Windows' compatible ICU
# forwarder and makes PySide6.QtCore fail with WinError 127 on Windows 10.
a.binaries = [
    entry
    for entry in a.binaries
    if not (entry[0].casefold() == "icuuc.dll" and "poppler" in entry[1].casefold())
]
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="ROX Enchantment Overlay",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="ROX Enchantment Overlay",
)
