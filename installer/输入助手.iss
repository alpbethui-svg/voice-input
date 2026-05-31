#define MyAppName "输入助手"
#define MyAppVersion "1.0.0"
#define MyAppPublisher "输入助手"
#define MyAppExeName "输入助手.exe"

[Setup]
AppId={{B98F7E20-0E3C-4A8A-A1D7-6BCFEA901001}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={localappdata}\Programs\{#MyAppName}
DefaultGroupName={#MyAppName}
OutputDir=Output
OutputBaseFilename=输入助手-Setup
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=lowest
InfoBeforeFile=说明.txt
UninstallDisplayIcon={app}\{#MyAppExeName}

[Tasks]
Name: "autostart"; Description: "开机自动启动输入助手"; GroupDescription: "启动选项："; Flags: checkedonce
Name: "desktopicon"; Description: "创建桌面快捷方式"; GroupDescription: "快捷方式："; Flags: unchecked

[Files]
Source: "..\dist\输入助手\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\输入助手"; Filename: "{app}\{#MyAppExeName}"
Name: "{group}\输入助手 - 模型准备"; Filename: "{app}\{#MyAppExeName}"; Parameters: "--model-setup"
Name: "{autodesktop}\输入助手"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Registry]
Root: HKCU; Subkey: "Software\Microsoft\Windows\CurrentVersion\Run"; ValueType: string; ValueName: "输入助手"; ValueData: """{app}\{#MyAppExeName}"""; Tasks: autostart; Flags: uninsdeletevalue

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "启动输入助手"; Flags: nowait postinstall skipifsilent unchecked
