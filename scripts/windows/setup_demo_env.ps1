#Requires -Version 5.1
<#
.SYNOPSIS
  Create/repair .venv-qwen and install demo + qwen extras for Gradio.

.DESCRIPTION
  Usage:
    powershell -ExecutionPolicy Bypass -File scripts\windows\setup_demo_env.ps1

  Optional:
    -ForceRecreate   Remove existing .venv-qwen and recreate
    -SkipTorchHint   Do not print CUDA torch tips
#>
param(
  [switch]$ForceRecreate,
  [switch]$SkipTorchHint
)

$ErrorActionPreference = "Stop"
try { [Console]::OutputEncoding = [System.Text.Encoding]::UTF8 } catch {}

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$Root = (Resolve-Path (Join-Path $ScriptDir "..\..")).Path
Set-Location $Root

Write-Host "========================================"
Write-Host " Demo env setup - chinese-braille-toolkit"
Write-Host " Root: $Root"
Write-Host "========================================"
Write-Host ""

$pyLauncher = $null
foreach ($c in @("py -3.12", "py -3.11", "py -3.10", "python")) {
  try {
    $out = & cmd /c "$c --version 2>nul"
    if ($LASTEXITCODE -eq 0 -and "$out" -match "Python 3\.(1[0-9]|[2-9][0-9])") {
      $pyLauncher = $c
      Write-Host "[OK] Found $out ($c)"
      break
    }
  } catch { }
}
if (-not $pyLauncher) {
  Write-Host "[ERR] Need Python 3.10+. Install from https://www.python.org/downloads/ (Add to PATH)."
  exit 1
}

$venvPath = Join-Path $Root ".venv-qwen"
$venvPy = Join-Path $venvPath "Scripts\python.exe"

if ($ForceRecreate -and (Test-Path $venvPath)) {
  Write-Host "[info] Removing old .venv-qwen ..."
  Remove-Item -Recurse -Force $venvPath
}

if (-not (Test-Path $venvPy)) {
  Write-Host "[1/4] Creating venv .venv-qwen ..."
  & cmd /c "$pyLauncher -m venv `"$venvPath`""
  if ($LASTEXITCODE -ne 0) { throw "venv create failed" }
} else {
  Write-Host "[1/4] Existing .venv-qwen found"
}

Write-Host "[2/4] Upgrading pip / setuptools / wheel ..."
& $venvPy -m pip install -U pip setuptools wheel
if ($LASTEXITCODE -ne 0) { throw "pip upgrade failed" }

Write-Host "[3/4] Installing package extras: .[demo,qwen] ..."
& $venvPy -m pip install -e ".[demo,qwen]"
if ($LASTEXITCODE -ne 0) { throw "pip install -e .[demo,qwen] failed" }

Write-Host "[4/4] Smoke import ..."
& $venvPy -c "import gradio, torch; print('gradio', gradio.__version__); print('torch', torch.__version__); print('cuda', torch.cuda.is_available())"
if ($LASTEXITCODE -ne 0) { throw "import check failed" }

Write-Host ""
Write-Host "Done. Next:"
Write-Host "  1) If base model missing: scripts\windows\Download-BaseModel.ps1"
Write-Host "  2) Start: scripts\windows\Start-BrailleDemo.bat"
Write-Host "  Browser: http://127.0.0.1:7860/"
Write-Host ""

if (-not $SkipTorchHint) {
  Write-Host "--- CUDA / PyTorch hint ---"
  Write-Host "If cuda is False, install GPU torch from https://pytorch.org matching your driver,"
  Write-Host "then re-run this script (or pip reinstall torch inside .venv-qwen)."
  Write-Host "Recommended NVIDIA VRAM >= 8GB (4-bit inference)."
  Write-Host ""
}
