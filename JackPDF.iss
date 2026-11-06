; ========================================================
; JackPDF - Inno Setup Installer Script
; ========================================================

#define MyAppName "JackPDF"
#define MyAppVersion "1.0.0"
#define MyAppPublisher "JackPDF"
#define MyAppExeName "JackPDF.exe"

[Setup]
; Unique GUID for JackPDF installation
AppId={{C7829E1B-3A26-47A4-9F89-A5C1E7039DFB}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={autopf}\{#MyAppName}
DefaultGroupName={#MyAppName}
AllowNoIcons=yes
; Support per-user or administrative installation
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog
OutputDir=installer
OutputBaseFilename=JackPDF_Setup
SetupIconFile=assets\icons\jackpdf.ico
UninstallDisplayIcon={app}\{#MyAppExeName}
Compression=lzma2/max
SolidCompression=yes
WizardStyle=modern

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "Buat shortcut Desktop"; GroupDescription: "Shortcut tambahan:"

[Files]
Source: "dist\JackPDF\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"
Name: "{group}\Uninstall JackPDF"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "Jalankan JackPDF"; Flags: nowait postinstall skipifsilent

