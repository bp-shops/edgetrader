; ══════════════════════════════════════════════════════════
; EdgeTrader – Inno Setup Installer Script
; by Philip Babuda
;
; Voraussetzung: Erst build.bat ausführen!
; Dann diese Datei in Inno Setup öffnen und kompilieren.
; Download Inno Setup: https://jrsoftware.org/isinfo.php
; ══════════════════════════════════════════════════════════

#define MyAppName "EdgeTrader"
#define MyAppVersion "1.1.0"
#define MyAppPublisher "Philip Babuda"
#define MyAppURL "https://edgetrader.de"
#define MyAppExeName "EdgeTrader.exe"

[Setup]
; Eindeutige App-ID (NICHT ändern nach Veröffentlichung!)
AppId={{B7E3F2A1-4D5C-6E7F-8A9B-0C1D2E3F4A5B}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppVerName={#MyAppName} v{#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}
DefaultDirName={autopf}\{#MyAppName}
DefaultGroupName={#MyAppName}
LicenseFile=LICENSE.txt
OutputDir=installer_output
OutputBaseFilename=EdgeTrader_Setup
SetupIconFile=assets\icon.ico
Compression=lzma2/ultra64
SolidCompression=yes
WizardStyle=modern

; Windows 10+ erforderlich
MinVersion=10.0

; 64-Bit
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible

; Keine Admin-Rechte nötig (installiert für aktuellen Benutzer)
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog

; Deinstallation
UninstallDisplayIcon={app}\{#MyAppExeName}
UninstallDisplayName={#MyAppName}

[Languages]
Name: "german"; MessagesFile: "compiler:Languages\German.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked
Name: "quicklaunchicon"; Description: "Schnellstart-Symbol erstellen"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
; Alle Dateien aus dem Build-Ordner
Source: "dist\EdgeTrader\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

; Default-Config für AppData (wird beim ersten Start kopiert)
Source: "dist\EdgeTrader\default_config.json"; DestDir: "{app}"; Flags: ignoreversion

; Lizenz
Source: "LICENSE.txt"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; IconFilename: "{app}\icon.ico"
Name: "{group}\{#MyAppName} deinstallieren"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; IconFilename: "{app}\icon.ico"; Tasks: desktopicon

[Run]
; Nach Installation starten (optional)
Filename: "{app}\{#MyAppExeName}"; Description: "{#MyAppName} jetzt starten"; Flags: nowait postinstall skipifsilent

[Code]
// ── AppData-Ordner erstellen und Default-Config kopieren ──
procedure CurStepChanged(CurStep: TSetupStep);
var
  AppDataDir: String;
  ConfigFile: String;
  DefaultConfig: String;
begin
  if CurStep = ssPostInstall then
  begin
    // AppData\EdgeTrader Ordner erstellen
    AppDataDir := ExpandConstant('{userappdata}\EdgeTrader');
    if not DirExists(AppDataDir) then
      ForceDirectories(AppDataDir);

    // Default-Config kopieren wenn noch keine existiert
    ConfigFile := AppDataDir + '\edgetrader_config.json';
    DefaultConfig := ExpandConstant('{app}\default_config.json');
    if not FileExists(ConfigFile) then
    begin
      if FileExists(DefaultConfig) then
        FileCopy(DefaultConfig, ConfigFile, False);
    end;
  end;
end;

// ── Bei Deinstallation: Fragen ob Benutzerdaten gelöscht werden sollen ──
procedure CurUninstallStepChanged(CurUninstallStep: TUninstallStep);
var
  AppDataDir: String;
begin
  if CurUninstallStep = usPostUninstall then
  begin
    AppDataDir := ExpandConstant('{userappdata}\EdgeTrader');
    if DirExists(AppDataDir) then
    begin
      if MsgBox('Sollen Ihre EdgeTrader-Einstellungen und Konfigurationsdateien ebenfalls gelöscht werden?',
                mbConfirmation, MB_YESNO) = IDYES then
      begin
        DelTree(AppDataDir, True, True, True);
      end;
    end;
  end;
end;
