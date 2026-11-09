# -*- mode: python ; coding: utf-8 -*-

import os
from PyInstaller.utils.hooks import collect_data_files, collect_submodules, copy_metadata

block_cipher = None

# Gather project assets
datas = [
    ('assets/icons', 'assets/icons'),
    ('assets/styles', 'assets/styles'),
    ('assets/models', 'assets/models'),
]

# Collect all package data files from PyMuPDF and ONNX Runtime
datas += collect_data_files('pymupdf')
datas += collect_data_files('onnxruntime')

# Collect package distribution metadata for packages that use importlib.metadata
datas += copy_metadata('pymatting')
datas += copy_metadata('rembg')
datas += copy_metadata('onnxruntime')
datas += copy_metadata('pooch')
datas += copy_metadata('tqdm')

# Explicit hidden imports for runtime safety, including all pymupdf submodules
hidden_imports = [
    'PySide6.QtCore',
    'PySide6.QtGui',
    'PySide6.QtWidgets',
    'fitz',
    'pymupdf',
    'pypdf',
    'PIL',
    'PIL.Image',
    'rembg',
    'rembg.bg',
    'rembg.sessions',
    'rembg.sessions.base',
    'rembg.sessions.u2net',
    'rembg.session_factory',
    'onnxruntime',
    'unittest',
] + collect_submodules('pymupdf')

a = Analysis(
    ['main.py'],
    pathex=['.'],
    binaries=[],
    datas=datas,
    hiddenimports=hidden_imports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['pytest'],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='JackPDF',
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
    icon='assets/icons/jackpdf.ico',
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='JackPDF',
)
