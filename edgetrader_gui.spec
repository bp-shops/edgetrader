# -*- mode: python ; coding: utf-8 -*-
# EdgeTrader GUI – PyInstaller Spec
# Baut die Haupt-GUI als Windows-Anwendung (kein CMD-Fenster)

import os
import sys
from PyInstaller.utils.hooks import collect_data_files

block_cipher = None
ICON = os.path.join('assets', 'icon.ico')

# certifi CA-Bundle für SSL-Zertifikatsvalidierung einbinden
certifi_datas = collect_data_files('certifi')

a = Analysis(
    ['bot_ui.py'],
    pathex=[],
    binaries=[],
    datas=certifi_datas,
    hiddenimports=[
        'tkinter',
        'tkinter.scrolledtext',
        'tkinter.messagebox',
        'tkinter.ttk',
        'license_manager',
        'updater',
        'urllib',
        'urllib.request',
        'urllib.error',
        'tempfile',
        'json',
        'hashlib',
        'hmac',
        'uuid',
        'platform',
        'base64',
        'threading',
        'subprocess',
        'datetime',
        're',
        'trade_history',
        'sqlite3',
        'ssl',
        'certifi',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['matplotlib', 'numpy', 'pandas', 'scipy', 'PIL', 'pytest'],
    noarchive=False,
    optimize=2,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='EdgeTrader',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,           # Kein CMD-Fenster!
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=ICON,
    version='version_info.txt',
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='EdgeTrader',
)
