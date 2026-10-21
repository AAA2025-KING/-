@echo off
chcp 65001 >nul
setlocal EnableExtensions

REM One-click FastAPI + web UI launcher for chinese-braille-toolkit (Windows).

set "SCRIPT_DIR=%~dp0"
pushd "%SCRIPT_DIR%..\.." || (
  echo [错误] 找不到项目根目录。
  pause
  exit /b 1
)
set "ROOT=%CD%"

echo ========================================
echo  中文盲文翻译 — FastAPI + 网页
echo  项目: %ROOT%
echo  地址: http://127.0.0.1:8000/
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

if not exist "%ROOT%\apps\api_server.py" (
  echo [错误] 缺少 apps\api_server.py
  pause
  popd
  exit /b 1
)

if not exist "%ROOT%\apps\web\index.html" (
  echo [错误] 缺少 apps\web\index.html
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

echo [2/3] 检查 FastAPI / uvicorn ...
"%PY%" -c "import fastapi, uvicorn" 2>nul
if errorlevel 1 (
  echo   未安装，正在 pip install -e ".[api]" ...
  "%PY%" -m pip install -e ".[api]"
  if errorlevel 1 (
    echo [错误] 安装失败。可手动: pip install "fastapi" "uvicorn[standard]"
    pause
    popd
    exit /b 1
  )
) else (
  echo   FastAPI / uvicorn: 已安装
)
echo.

if not defined CBT_API_HOST set "CBT_API_HOST=127.0.0.1"
if not defined CBT_API_PORT set "CBT_API_PORT=8000"

REM 本机 Windows CUDA 一键重训（仅本地；勿在无 GPU / 共享服务器上开启）
if not defined CBT_ALLOW_RETRAIN set "CBT_ALLOW_RETRAIN=1"
echo [提示] CBT_ALLOW_RETRAIN=%CBT_ALLOW_RETRAIN% （网页「一键重训」可用；仅建议本机 GPU）
echo.


echo [3/3] 启动 uvicorn ...
echo       浏览器打开 http://%CBT_API_HOST%:%CBT_API_PORT%/
echo       API 文档   http://%CBT_API_HOST%:%CBT_API_PORT%/docs
echo       首次翻译加载 8B 模型可能需要数十秒到数分钟。
echo       按 Ctrl+C 结束服务。
echo.

"%PY%" -m uvicorn apps.api_server:app --host %CBT_API_HOST% --port %CBT_API_PORT%
set "EC=%ERRORLEVEL%"

echo.
if not "%EC%"=="0" (
  echo [错误] 进程退出码 %EC%。
  pause
)
popd
endlocal
exit /b %EC%
