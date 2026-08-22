[Setup]
AppName='FixBug-core'
AppVersion=1.0.0
AppPublisher="Bharathikannan R"
DefaultDirName={autopf}\fixbug-core
DefaultGroupName=fixbug-core
OutputDir=Output
OutputBaseFilename=FixBug_core_Installer
Compression=lzma
SolidCompression=yes
; Required to immediately refresh the terminal environment variables after installation
ChangesEnvironment=yes
SetupIconFile=assets\fixbug.ico
UninstallDisplayIcon={app}\fbcore.exe

[Files]
; Changed to target fbcore.exe (Update "dist\fbcore" if your build output folder is named differently)
Source: "dist\fbcore\fbcore.exe"; DestDir: "{app}"; Flags: ignoreversion
Source: "dist\fbcore\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\fixbug-core"; Filename: "{app}\fbcore.exe"

[Registry]
; Changed HKCU to HKLM and updated Subkey for system-wide PATH
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