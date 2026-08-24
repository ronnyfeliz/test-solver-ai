# -*- mode: python ; coding: utf-8 -*-
# PyInstaller spec for the Linux build of Test Solver AI v1.0.2.
# Build with: python3 -m PyInstaller test_solver_v1.0.2.spec --noconfirm --clean


a = Analysis(
    ['test_solver_v1.0.2.py'],
    pathex=[],
    binaries=[],
    datas=[('media', 'media')],
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='test_solver_v1.0.2',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
