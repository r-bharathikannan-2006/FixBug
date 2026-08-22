[Setup]
; Check which compiler flag was passed by the GitHub Action's /D argument
#ifdef Is_x64
  #define ArchSuffix "_x64"
#else
  #define ArchSuffix "_x86"
#endif

AppName='FixBug-core'
AppVersion=1.0.0
AppPublisher="Bharathikannan R"
DefaultDirName={autopf}\fixbug-core
DefaultGroupName=fixbug-core
OutputDir=Output
OutputBaseFilename=FixBug_core_Installer{#ArchSuffix}
Compression=lzma
SolidCompression=yes
; Required to immediately refresh the terminal environment variables after installation
ChangesEnvironment=yes
SetupIconFile=assets\fixbug.ico
UninstallDisplayIcon={app}\fbcore.exe

; Ensure 64-bit installer installs to native Program Files and only runs on 64-bit machines.
#ifdef Is_x64
ArchitecturesAllowed=x64
ArchitecturesInstallIn64BitMode=x64
#endif

[Files]
Source: "dist\fbcore\fbcore.exe"; DestDir: "{app}"; Flags: ignoreversion
Source: "dist\fbcore\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\fixbug-core"; Filename: "{app}\fbcore.exe"

[Registry]
Root: HKLM; Subkey: "System\CurrentControlSet\Control\Session Manager\Environment"; ValueType: expandsz; ValueName: "Path"; ValueData: "{olddata};{app}"; Check: NeedsAddPath(ExpandConstant('{app}'))

[Code]
function NeedsAddPath(Param: string): boolean;
var
  OrigPath: string;
begin
  if not RegQueryStringValue(HKEY_CURRENT_USER, 'Environment', 'Path', OrigPath)
  then begin
    Result := True;
    exit;
  end;
  { Prevent duplicating the PATH entry if the user reinstalls or updates }
  Result := Pos(';' + Param + ';', ';' + OrigPath + ';') = 0;
end;
