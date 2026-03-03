# -*- mode: python ; coding: utf-8 -*-
# EdgeTrader Bot Engine – PyInstaller Spec
# Baut den Trading-Bot als versteckte Console-Anwendung

import os
from PyInstaller.utils.hooks import collect_data_files, collect_submodules

block_cipher = None
ICON = os.path.join('assets', 'icon.ico')

# dateparser Daten (.pkl, Locale-Dateien) automatisch sammeln
dateparser_datas = collect_data_files('dateparser')
dateparser_hiddenimports = collect_submodules('dateparser')

a = Analysis(
    ['telegram_binance_bot.py'],
    pathex=[],
    binaries=[],
    datas=dateparser_datas,
    hiddenimports=[
        'telethon',
        'telethon.events',
        'telethon.tl',
        'telethon.tl.types',
        'telethon.crypto',
        'binance',
        'binance.client',
        'binance.enums',
        'binance.exceptions',
        'dateparser',
        'json',
        'asyncio',
        'logging',
        're',
        'sqlite3',
        'ssl',
        'certifi',
        'socks',
        'trade_history',
    ] + dateparser_hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['tkinter', 'matplotlib', 'numpy', 'pandas', 'scipy', 'PIL', 'pytest'],
    noarchive=False,
    optimize=2,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='edgetrader_bot',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=True,            # Console für stdout-Ausgabe (wird von GUI gelesen)
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=ICON,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='edgetrader_bot',
)
