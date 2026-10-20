#Requires -Version 5.1
<#
.SYNOPSIS
  Download Vision-Braille-Qwen3-8B into models\Vision-Braille-Qwen3-8B (NOT bundled in zip).

.DESCRIPTION
  Base weights are large and licensed CC BY-NC-SA 4.0.
  Do NOT redistribute commercially without checking the license.

  Usage:
    powershell -ExecutionPolicy Bypass -File scripts\windows\Download-BaseModel.ps1
#>
param(
  [string]$RepoId = "Violet-yo/Vision-Braille-Qwen3-8B",
  [string]$LocalDir = ""
)

$ErrorActionPreference = "Stop"
try { [Console]::OutputEncoding = [System.Text.Encoding]::UTF8 } catch {}

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$Root = (Resolve-Path (Join-Path $ScriptDir "..\..")).Path
if (-not $LocalDir) {
  $LocalDir = Join-Path $Root "models\Vision-Braille-Qwen3-8B"
}

Write-Host "========================================"
Write-Host " Download base model (personal / non-commercial)"
Write-Host " HF: $RepoId"
Write-Host " Dest: $LocalDir"
Write-Host " License: CC BY-NC-SA 4.0 - read the model card"
Write-Host "========================================"
Write-Host ""
Write-Host "Note: base weights are NOT packed into the share zip."
Write-Host ""

$venvPy = Join-Path $Root ".venv-qwen\Scripts\python.exe"
if (-not (Test-Path $venvPy)) {
  Write-Host "[ERR] Run setup_demo_env.ps1 first to create .venv-qwen"
  exit 1
}

& $venvPy -m pip install -U "huggingface_hub>=0.23"
if ($LASTEXITCODE -ne 0) { throw "install huggingface_hub failed" }

New-Item -ItemType Directory -Force -Path $LocalDir | Out-Null

$env:CBT_HF_REPO = $RepoId
$env:CBT_HF_DIR = $LocalDir
& $venvPy -c "from huggingface_hub import snapshot_download; import os; p=snapshot_download(repo_id=os.environ['CBT_HF_REPO'], local_dir=os.environ['CBT_HF_DIR']); print('downloaded_to', p)"
if ($LASTEXITCODE -ne 0) { throw "download failed; set HF_TOKEN or download manually from the model page" }

Write-Host ""
Write-Host "Done. Start with Start-BrailleDemo.bat"
