# -*- mode: python ; coding: utf-8 -*-

from pathlib import Path

project_root = Path(SPECPATH)

a = Analysis(
    [str(project_root / "app.py")],
    pathex=[str(project_root)],
    binaries=[],
    datas=[],
    hiddenimports=[
        "keyring.backends.macOS",
        "keyring.backends.OS_X",
        "paramiko",
        "bcrypt",
        "cryptography",
    ],
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
    name="Remote Workspace",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch="universal2",
    codesign_identity=None,
    entitlements_file=str(project_root / "packaging" / "entitlements.plist"),
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name="Remote Workspace",
)

app = BUNDLE(
    coll,
    name="Remote Workspace.app",
    icon=str(project_root / "assets" / "RemoteWorkspace.icns"),
    bundle_identifier="net.alcyber.remoteworkspace",
    info_plist={
        "CFBundleName": "Remote Workspace",
        "CFBundleDisplayName": "Remote Workspace",
        "CFBundleShortVersionString": "2.9",
        "CFBundleVersion": "2.9.0",
        "NSHighResolutionCapable": True,
        "LSApplicationCategoryType": "public.app-category.developer-tools",
        "NSHumanReadableCopyright": "Remote Workspace",
    },
)
