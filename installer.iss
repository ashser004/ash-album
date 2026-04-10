; ============================================================
;  Ash Album — Inno Setup Installer Script
;  Produces: "Ash Album Setup.exe"
;
;  Prerequisites:
;    1. Build the portable exe first:
;       pyinstaller "Ash Album.spec"
;    2. Place the resulting "Ash Album.exe" in  dist\
;    3. Ensure icon.png sits in the project root.
;    4. Convert icon.png → icon.ico (256×256, 48×48, 32×32, 16×16)
;       and place icon.ico in the project root.
;    5. Compile this script with Inno Setup 6+:
;       iscc installer.iss
;
;  Output : dist\Ash Album Setup.exe
; ============================================================

#define MyAppName      "Ash Album"
#define MyAppVersion   "1.2.3"
#define MyAppPublisher "Ash Album"
#define MyAppURL       "https://github.com/AshAlbum"
#define MyAppExeName   "Ash Album.exe"

[Setup]
AppId={{B8A5D2E1-7F3C-4A2D-9E6B-1C5D8F0A3E7B}}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}
AppUpdatesURL={#MyAppURL}
DefaultDirName={autopf}\{#MyAppName}
DefaultGroupName={#MyAppName}
AllowNoIcons=yes
OutputDir=dist
OutputBaseFilename=Ash Album Setup
SetupIconFile=icon.ico
Compression=lzma2/ultra64
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=lowest
PrivilegesRequiredOverridesAllowed=dialog
UninstallDisplayIcon={app}\{#MyAppExeName}
ChangesAssociations=yes
ArchitecturesInstallIn64BitMode=x64compatible

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon";    Description: "{cm:CreateDesktopIcon}";    GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked
Name: "fileassoc_jpg";  Description: "Associate .jpg files with {#MyAppName}";  GroupDescription: "File Associations:"; Flags: unchecked
Name: "fileassoc_jpeg"; Description: "Associate .jpeg files with {#MyAppName}"; GroupDescription: "File Associations:"; Flags: unchecked
Name: "fileassoc_png";  Description: "Associate .png files with {#MyAppName}";  GroupDescription: "File Associations:"; Flags: unchecked

[Files]
Source: "dist\Ash Album\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "icon.png";           DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\{#MyAppName}";           Filename: "{app}\{#MyAppExeName}"; Comment: "Open Ash Album"
Name: "{group}\Uninstall {#MyAppName}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#MyAppName}";     Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Registry]
; ---- Register our ProgId so Windows shows "Ash Album" in the
;      "Open with" / "Set Default" lists for image files. ----

; ProgId: AshAlbum.Image
Root: HKA; Subkey: "Software\Classes\AshAlbum.Image";                         ValueType: string; ValueName: "";            ValueData: "Ash Album Image";                      Flags: uninsdeletekey
Root: HKA; Subkey: "Software\Classes\AshAlbum.Image\DefaultIcon";             ValueType: string; ValueName: "";            ValueData: "{app}\{#MyAppExeName},0";               Flags: uninsdeletekey
Root: HKA; Subkey: "Software\Classes\AshAlbum.Image\shell\open\command";      ValueType: string; ValueName: "";            ValueData: """{app}\{#MyAppExeName}"" --standalone ""%1""";       Flags: uninsdeletekey

; Tell Windows our app supports these extensions (appears in "Open with")
Root: HKA; Subkey: "Software\Classes\.jpg\OpenWithProgids";   ValueType: string; ValueName: "AshAlbum.Image"; ValueData: ""; Flags: uninsdeletevalue
Root: HKA; Subkey: "Software\Classes\.jpeg\OpenWithProgids";  ValueType: string; ValueName: "AshAlbum.Image"; ValueData: ""; Flags: uninsdeletevalue
Root: HKA; Subkey: "Software\Classes\.png\OpenWithProgids";   ValueType: string; ValueName: "AshAlbum.Image"; ValueData: ""; Flags: uninsdeletevalue

; Registered Applications entry (makes the app discoverable in Default Programs)
Root: HKA; Subkey: "Software\RegisteredApplications"; ValueType: string; ValueName: "AshAlbum"; ValueData: "Software\AshAlbum\Capabilities"; Flags: uninsdeletevalue

; Application Capabilities (Default Programs panel)
Root: HKA; Subkey: "Software\AshAlbum\Capabilities";                    ValueType: string; ValueName: "ApplicationName";         ValueData: "{#MyAppName}";              Flags: uninsdeletekey
Root: HKA; Subkey: "Software\AshAlbum\Capabilities";                    ValueType: string; ValueName: "ApplicationDescription";  ValueData: "Your private desktop gallery"; Flags: uninsdeletekey
Root: HKA; Subkey: "Software\AshAlbum\Capabilities\FileAssociations";   ValueType: string; ValueName: ".jpg";  ValueData: "AshAlbum.Image"; Flags: uninsdeletekey
Root: HKA; Subkey: "Software\AshAlbum\Capabilities\FileAssociations";   ValueType: string; ValueName: ".jpeg"; ValueData: "AshAlbum.Image"; Flags: uninsdeletekey
Root: HKA; Subkey: "Software\AshAlbum\Capabilities\FileAssociations";   ValueType: string; ValueName: ".png";  ValueData: "AshAlbum.Image"; Flags: uninsdeletekey

; One-time dismissal flag for the Set as Default toolbar button
Root: HKCU; Subkey: "Software\AshAlbum\UI"; ValueType: string; ValueName: "HideDefaultButton"; ValueData: "0"; Flags: uninsdeletekey

; ---- Optional: set UserChoice directly (only when the user ticks the checkbox) ----
; NOTE: On Windows 10/11 the OS may ignore direct UserChoice writes and require
;       the user to confirm via Settings. The registry entries above ensure Ash Album
;       appears in the list when the user opens Settings → Default apps.

Root: HKA; Subkey: "Software\Classes\.jpg";  ValueType: string; ValueName: ""; ValueData: "AshAlbum.Image"; Tasks: fileassoc_jpg;  Flags: uninsdeletevalue
Root: HKA; Subkey: "Software\Classes\.jpeg"; ValueType: string; ValueName: ""; ValueData: "AshAlbum.Image"; Tasks: fileassoc_jpeg; Flags: uninsdeletevalue
Root: HKA; Subkey: "Software\Classes\.png";  ValueType: string; ValueName: ""; ValueData: "AshAlbum.Image"; Tasks: fileassoc_png;  Flags: uninsdeletevalue

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#StringChange(MyAppName, '&', '&&')}}"; Flags: nowait postinstall skipifsilent
