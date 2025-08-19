# -*- mode: python ; coding: utf-8 -*-
import sys ; sys.setrecursionlimit(sys.getrecursionlimit() * 5)

a = Analysis(
    ['calview_temperature.py'],
    pathex=[],
    binaries=[],
    datas=[('inputs/TR_fields_temperature.txt', 'inputs/.'), ('inputs/usbr_logo.jpg', 'inputs/.')],
    hiddenimports=[],
    hookspath=['src/hook-panel.py'],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,

)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='CalView Temperature',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
