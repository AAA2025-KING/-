@echo off
chcp 65001 >nul
setlocal EnableExtensions

REM One-click PySide6 desktop launcher for chinese-braille-toolkit (Windows).
REM Double-click this file, or run from a CMD/PowerShell window.

set "SCRIPT_DIR=%~dp0"
pushd "%SCRIPT_DIR%..\.." || (
  echo [错误] 找不到项目根目录。
  pause
  exit /b 1
)
set "ROOT=%CD%"

echo ========================================
echo  中文盲文翻译 — PySide6 桌面版
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

if not exist "%ROOT%\apps\desktop_pyside.py" (
  echo [错误] 缺少 apps\desktop_pyside.py
  pause
  popd
  exit /b 1
)

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

echo [2/3] 检查 PySide6 ...
"%PY%" -c "from PySide6.QtWidgets import QApplication" 2>nul
if errorlevel 1 (
  echo   未安装 PySide6，正在安装 PySide6-Essentials（体积更小）...
  "%PY%" -m pip install "PySide6-Essentials"
  if errorlevel 1 (
    echo [错误] PySide6 安装失败。可手动: pip install -e ".[desktop]"
    pause
    popd
    exit /b 1
  )
) else (
  echo   PySide6: 已安装
)
echo.

echo [3/3] 启动桌面窗口 ...
echo       首次点「翻译」加载 8B 模型可能需要数十秒到数分钟，请勿强制结束。
echo.

"%PY%" "%ROOT%\apps\desktop_pyside.py"
set "EC=%ERRORLEVEL%"

echo.
if not "%EC%"=="0" (
  echo [错误] 进程退出码 %EC%。若缺依赖，请先运行 setup_demo_env.ps1 并 pip install PySide6
  pause
)
popd
endlocal
exit /b %EC%
