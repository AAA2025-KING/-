@echo off
chcp 65001 >nul
setlocal EnableExtensions

REM One-click Gradio launcher for chinese-braille-toolkit (Windows).
REM Double-click this file, or run from a CMD/PowerShell window.

set "SCRIPT_DIR=%~dp0"
pushd "%SCRIPT_DIR%..\.." || (
  echo [错误] 找不到项目根目录。
  pause
  exit /b 1
)
set "ROOT=%CD%"

echo ========================================
echo  中文盲文翻译演示 — Gradio
echo  项目: %ROOT%
echo ========================================
echo.

set "PY=%ROOT%\.venv-qwen\Scripts\python.exe"
if not exist "%PY%" (
  echo [提示] 未找到虚拟环境: .venv-qwen
  echo 请先运行: scripts\windows\setup_demo_env.ps1
  echo.
  echo   cd "%ROOT%"
  echo   powershell -ExecutionPolicy Bypass -File scripts\windows\setup_demo_env.ps1
  echo.
  pause
  popd
  exit /b 1
)

if not exist "%ROOT%\apps\gradio_demo.py" (
  echo [错误] 缺少 apps\gradio_demo.py
  pause
  popd
  exit /b 1
)

if "%CBT_WEBUI_PORT%"=="" set "CBT_WEBUI_PORT=7860"
if "%CBT_WEBUI_HOST%"=="" set "CBT_WEBUI_HOST=127.0.0.1"
set "URL=http://%CBT_WEBUI_HOST%:%CBT_WEBUI_PORT%/"

echo [1/3] 检查适配器 / 基座（仅提示，不阻止启动）...
if exist "%ROOT%\models\lora_tables\adapter_model.safetensors" (
  echo   LoRA: 已找到 models\lora_tables\
) else (
  echo   LoRA: 未找到 — 翻译可能走脚手架或需自备适配器
)
if exist "%ROOT%\models\Vision-Braille-Qwen3-8B\config.json" (
  echo   基座: 已找到 models\Vision-Braille-Qwen3-8B\
) else (
  echo   基座: 未找到 — 请运行 scripts\windows\Download-BaseModel.ps1
  echo         或从 Hugging Face 下载 Violet-yo/Vision-Braille-Qwen3-8B
  echo         （许可 CC BY-NC-SA，非商用分发请自查合规）
)
echo.

echo [2/3] 即将打开浏览器: %URL%
echo       首次加载 8B 模型可能需要 1–3 分钟，请勿关闭本窗口。
echo       关闭本窗口即停止演示服务。
echo.

REM Delayed browser open so Gradio has a moment to bind the port
start "open-braille-demo" /MIN cmd /c "timeout /t 4 /nobreak >nul & start %URL%"

echo [3/3] 启动 Gradio ...
echo.
"%PY%" "%ROOT%\apps\gradio_demo.py"
set "EC=%ERRORLEVEL%"

echo.
if not "%EC%"=="0" (
  echo [错误] 进程退出码 %EC%。若缺依赖，请先运行 setup_demo_env.ps1
  pause
)
popd
endlocal
exit /b %EC%
