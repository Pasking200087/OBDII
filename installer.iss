; OBD-II Diagnostics — Inno Setup Script
; Версия инжектируется GitHub Actions через /DAppVersion=...

#ifndef AppVersion
  #define AppVersion "dev"
#endif

#define AppName    "OBD-II Диагностика"
#define AppExeName "OBD2_Diagnostics.exe"
#define AppId      "A7F3B2C1-D4E5-4F60-9ABC-DEF012345678"

[Setup]
AppId={{{#AppId}}
AppName={#AppName}
AppVersion={#AppVersion}
AppPublisher=Pasking200087
AppPublisherURL=https://github.com/Pasking200087/OBDII
AppSupportURL=https://github.com/Pasking200087/OBDII/issues
AppUpdatesURL=https://github.com/Pasking200087/OBDII/releases
DefaultDirName={localappdata}\OBD2_Diagnostics
DefaultGroupName={#AppName}
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
OutputBaseFilename=OBD2_Diagnostics_Setup
Compression=lzma2/max
SolidCompression=yes
WizardStyle=modern
UninstallDisplayName={#AppName}
UninstallDisplayIcon={app}\{#AppExeName}
CloseApplications=yes
CloseApplicationsFilter=*.exe

[Languages]
Name: "russian"; MessagesFile: "compiler:Languages\Russian.isl"

[Tasks]
Name: "desktopicon"; Description: "Создать ярлык на рабочем столе"; GroupDescription: "Дополнительно:"; Flags: unchecked

[Files]
Source: "dist\OBD2_Diagnostics\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\{#AppName}";           Filename: "{app}\{#AppExeName}"
Name: "{group}\Удалить {#AppName}";   Filename: "{uninstallexe}"
Name: "{autodesktop}\{#AppName}";     Filename: "{app}\{#AppExeName}"; Tasks: desktopicon

[Run]
Filename: "{app}\{#AppExeName}"; Description: "Запустить {#AppName}"; Flags: nowait postinstall skipifsilent
