# -*- mode: python ; coding: utf-8 -*-
import sys ; sys.setrecursionlimit(sys.getrecursionlimit() * 5)
from PyInstaller.utils.hooks import copy_metadata, collect_data_files

metadata_datas = []
for pkg in ('pandas', 'numpy', 'holoviews', 'panel', 'bokeh', 'param', 'hvplot'):
    metadata_datas += copy_metadata(pkg)


gdal_datas = collect_data_files('rasterio', subdir='gdal_data')

a = Analysis(
    ['calview_calsim.py'],
    pathex=[],
    binaries=[],
    datas=[('inputs/TR_fields.txt', 'inputs/.'), ('inputs/usbr_logo.jpg', 'inputs/.')] + metadata_datas + gdal_datas,
    hiddenimports=[
        'rasterio.sample',
        'rasterio._io',
        'rasterio.control',
        'rasterio.crs',
        'rasterio.transform',
        'rasterio.vrt',
        'rasterio._features',
        'rasterio._warp',
        'rasterio._base',
        'rasterio._env',
    ],
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
    name='CalView',
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
