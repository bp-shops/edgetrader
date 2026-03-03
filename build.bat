@echo off
chcp 65001 >nul
title EdgeTrader Build System
echo.
echo ╔══════════════════════════════════════════════════╗
echo ║   EdgeTrader – Build System                     ║
echo ║   by Philip Babuda                              ║
echo ╚══════════════════════════════════════════════════╝
echo.

:: ── Prüfe Python ──────────────────────────────────────
python --version >nul 2>&1
if errorlevel 1 (
    echo [FEHLER] Python nicht gefunden! Bitte Python 3.10+ installieren.
    pause
    exit /b 1
)

:: ── Build-Dependencies installieren ───────────────────
echo [1/7] Installiere Build-Dependencies...
pip install pyinstaller --quiet

:: ── Code-Schutz mit PyArmor (optional) ───────────────
echo [2/7] Code-Schutz vorbereiten...
pip install pyarmor --quiet 2>nul
if not errorlevel 1 (
    echo        PyArmor verfügbar – Code wird verschlüsselt
    if not exist "protected" mkdir protected
    pyarmor gen --output protected bot_ui.py 2>nul
    pyarmor gen --output protected telegram_binance_bot.py 2>nul
    if exist "protected\bot_ui.py" (
        echo        Code erfolgreich verschlüsselt!
        set "USE_PROTECTED=1"
    ) else (
        echo        PyArmor-Verschlüsselung übersprungen – nutze Standard-Build
        set "USE_PROTECTED=0"
    )
) else (
    echo        PyArmor nicht verfügbar – Standard-Build
    set "USE_PROTECTED=0"
)

:: ── Alte Builds aufräumen ─────────────────────────────
echo [3/7] Räume alte Builds auf...
if exist dist rmdir /s /q dist
if exist build rmdir /s /q build

:: ── Icon erstellen ────────────────────────────────────
echo [4/7] Erstelle App-Icon...
if not exist "assets\icon.ico" (
    pip install Pillow --quiet
    python create_icon.py
)

:: ── GUI bauen ─────────────────────────────────────────
echo [5/7] Baue EdgeTrader.exe (GUI)...
pyinstaller --clean --noconfirm edgetrader_gui.spec

if errorlevel 1 (
    echo [FEHLER] GUI Build fehlgeschlagen!
    pause
    exit /b 1
)

:: ── Bot bauen ─────────────────────────────────────────
echo [6/7] Baue edgetrader_bot.exe (Bot Engine)...
pyinstaller --clean --noconfirm edgetrader_bot.spec

if errorlevel 1 (
    echo [FEHLER] Bot Build fehlgeschlagen!
    pause
    exit /b 1
)

:: ── Zusammenführen ────────────────────────────────────
echo [7/7] Führe zusammen...

:: Bot-Dateien in GUI-Ordner kopieren
xcopy /E /Y /Q "dist\edgetrader_bot\*" "dist\EdgeTrader\" >nul

:: Lizenz, Impressum und Default-Config kopieren
copy /Y "LICENSE.txt" "dist\EdgeTrader\" >nul
if exist "IMPRESSUM.txt" copy /Y "IMPRESSUM.txt" "dist\EdgeTrader\" >nul
copy /Y "assets\icon.ico" "dist\EdgeTrader\" >nul

:: Default-Config erstellen (leere Keys für Kunden)
echo {"active_profile":0,"profiles":[{"name":"Mein Profil","telegram_api_id":"31561693","telegram_api_hash":"76831e21ac32da38129342a94e05ab94","telegram_channel":"","broker":"Binance Futures","api_key":"","api_secret":"","passphrase":"","testnet":true,"leverage":"5","capital":"100","sl_percent":"1.5","tp_enabled":true,"sl_enabled":true,"auto_sl_enabled":true,"tp_distribution":"33,33,34","trailing_enabled":false,"trailing_percent":"1.0","trailing_trigger":"TP1","limit_invalidation_enabled":true,"limit_invalidation_percent":"2.0","map_signal_start":"Signal #","map_long":"LONG, BUY, KAUFEN","map_short":"SHORT, SELL, VERKAUFEN","map_pair":"Pair, Symbol, Coin, Asset","map_entry":"Entry, Einstieg, Buy at, Sell at","map_tp":"TP, TakeProfit, Take Profit, Ziel, Target","map_sl":"SL, StopLoss, Stop Loss, Stop, Absicherung","map_close":"CLOSED, Close, Exit, Geschlossen, Schließen","map_market":"MARKET, Markt, MKT","map_limit":"LIMIT, LMT"}]} > "dist\EdgeTrader\default_config.json"

:: Aufräumen
if exist protected rmdir /s /q protected

echo.
echo ╔══════════════════════════════════════════════════╗
echo ║   BUILD ERFOLGREICH!                            ║
echo ║                                                 ║
echo ║   Ausgabe: dist\EdgeTrader\                     ║
echo ║   → EdgeTrader.exe     (GUI)                   ║
echo ║   → edgetrader_bot.exe (Bot Engine)             ║
echo ║                                                 ║
echo ║   Nächster Schritt:                             ║
echo ║   Inno Setup öffnen → installer.iss kompilieren ║
echo ║   Download: https://jrsoftware.org/isinfo.php   ║
echo ╚══════════════════════════════════════════════════╝
echo.
pause
