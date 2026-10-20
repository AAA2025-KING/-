; Inno Setup outline for chinese-braille-toolkit Gradio demo (Windows).
; NOT a ready-to-ship commercial installer. Review license before shipping base weights.
;
; Build steps (on a Windows PC with Inno Setup 6+):
;   1. Run Pack-DemoZip.ps1 so dist\chinese-braille-demo\ exists (no base model).
;   2. Open this file in Inno Setup Compiler, adjust Source paths, Compile.
;   3. Distribute the generated Setup.exe; recipients still run setup_demo_env.ps1
;      and Download-BaseModel.ps1 after install (or you add [Run] entries).
;
; Do NOT add models\Vision-Braille-Qwen3-8B\*.safetensors to Source unless you
; have confirmed CC BY-NC-SA redistribution is allowed for your use case.

#define MyAppName "Chinese Braille Demo"
#define MyAppVersion "0.1.0a1"
#define MyAppPublisher "Chinese Braille Toolkit contributors"
#define MyAppURL "https://huggingface.co/Violet-yo/Vision-Braille-Qwen3-8B"
#define MyAppExeName "Start-BrailleDemo.bat"
; Point at packed tree (adjust if needed):
#define PackRoot "..\..\dist\chinese-braille-demo"

[Setup]
AppId={{A7C3E2B1-9F40-4D2A-8C11-CBTDEMO0001}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
DefaultDirName={autopf}\ChineseBrailleDemo
DefaultGroupName={#MyAppName}
DisableProgramGroupPage=yes
OutputDir=..\..\dist
OutputBaseFilename=ChineseBrailleDemo-Setup
Compression=lzma
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=lowest
ArchitecturesInstallIn64BitMode=x64compatible
InfoBeforeFile=license_note_before_install.txt
; Create license_note_before_install.txt next to this .iss with CC BY-NC-SA notice.

[Languages]
Name: "chinesesimplified"; MessagesFile: "compiler:Languages\ChineseSimplified.isl"
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "创建桌面快捷方式"; GroupDescription: "附加图标:"

[Files]
; Entire packed demo EXCEPT base weights (Pack-DemoZip already excludes them)
Source: "{#PackRoot}\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\启动盲文演示"; Filename: "{app}\scripts\windows\Start-BrailleDemo.bat"; WorkingDir: "{app}"
Name: "{group}\安装 Python 环境"; Filename: "powershell.exe"; Parameters: "-ExecutionPolicy Bypass -File ""{app}\scripts\windows\setup_demo_env.ps1"""; WorkingDir: "{app}"
Name: "{group}\下载基座模型"; Filename: "powershell.exe"; Parameters: "-ExecutionPolicy Bypass -File ""{app}\scripts\windows\Download-BaseModel.ps1"""; WorkingDir: "{app}"
Name: "{autodesktop}\盲文翻译演示"; Filename: "{app}\scripts\windows\Start-BrailleDemo.bat"; WorkingDir: "{app}"; Tasks: desktopicon

[Run]
Filename: "powershell.exe"; Parameters: "-ExecutionPolicy Bypass -File ""{app}\scripts\windows\setup_demo_env.ps1"""; WorkingDir: "{app}"; Flags: postinstall skipifsilent; Description: "安装 Python 依赖（.venv-qwen）"
; Uncomment only if you want to auto-start download (large, needs network):
; Filename: "powershell.exe"; Parameters: "-ExecutionPolicy Bypass -File ""{app}\scripts\windows\Download-BaseModel.ps1"""; WorkingDir: "{app}"; Flags: postinstall skipifsilent unchecked; Description: "下载基座模型（CC BY-NC-SA，体积大）"

[Code]
// Optional: show reminder that base model is not included.
procedure CurPageChanged(CurPageID: Integer);
begin
  if CurPageID = wpFinished then
    MsgBox('安装完成。若尚未下载基座模型，请从开始菜单运行「下载基座模型」。' + #13#10 +
           '基座许可为 CC BY-NC-SA，请勿用于未授权的商业再分发。', mbInformation, MB_OK);
end;
