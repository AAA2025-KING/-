#Requires -Version 5.1
<#
.SYNOPSIS
  Build redistributable folder/zip: code + LoRA + launchers, WITHOUT base model weights.

.DESCRIPTION
  Output: dist\chinese-braille-demo\  and optionally dist\chinese-braille-demo.zip

  Usage:
    powershell -ExecutionPolicy Bypass -File scripts\windows\Pack-DemoZip.ps1
    powershell -ExecutionPolicy Bypass -File scripts\windows\Pack-DemoZip.ps1 -MakeZip
#>
param(
  [switch]$MakeZip,
  [switch]$IncludeVenv
)

$ErrorActionPreference = "Stop"
try { [Console]::OutputEncoding = [System.Text.Encoding]::UTF8 } catch {}

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$Root = (Resolve-Path (Join-Path $ScriptDir "..\..")).Path
$OutDir = Join-Path $Root "dist\chinese-braille-demo"
$ZipPath = Join-Path $Root "dist\chinese-braille-demo.zip"

Write-Host "Packing to: $OutDir"
Write-Host "Excluded: base model Vision-Braille-Qwen3-8B, .venv*, outputs"

if (Test-Path $OutDir) {
  Remove-Item -Recurse -Force $OutDir
}
New-Item -ItemType Directory -Force -Path $OutDir | Out-Null

$includeDirs = @("apps", "src", "configs", "data", "docs", "scripts", "tests")
foreach ($d in $includeDirs) {
  $src = Join-Path $Root $d
  if (Test-Path $src) {
    Write-Host "  + $d"
    Copy-Item -Recurse -Force $src (Join-Path $OutDir $d)
  }
}

foreach ($f in @("pyproject.toml", "README.md", "LICENSE", ".gitignore")) {
  $src = Join-Path $Root $f
  if (Test-Path $src) {
    Copy-Item -Force $src (Join-Path $OutDir $f)
  }
}

$loraSrc = Join-Path $Root "models\lora_tables"
$loraDst = Join-Path $OutDir "models\lora_tables"
if (Test-Path $loraSrc) {
  New-Item -ItemType Directory -Force -Path (Join-Path $OutDir "models") | Out-Null
  Copy-Item -Recurse -Force $loraSrc $loraDst
  Write-Host "  + models\lora_tables (LoRA adapter)"
} else {
  Write-Host "  ! WARN: models\lora_tables missing; recipients will get weak translation"
}

$baseHint = Join-Path $OutDir "models\Vision-Braille-Qwen3-8B"
New-Item -ItemType Directory -Force -Path $baseHint | Out-Null
$hintText = @"
Do NOT ship full base weights in the share zip (large + CC BY-NC-SA limits).

Recipient should run:

  powershell -ExecutionPolicy Bypass -File scripts\windows\Download-BaseModel.ps1

Or manually download Violet-yo/Vision-Braille-Qwen3-8B into this folder.
"@
Set-Content -Path (Join-Path $baseHint "README_DOWNLOAD.txt") -Value $hintText -Encoding UTF8

$packDoc = Join-Path $Root "docs\desktop_packaging.md"
$readmeCn = Join-Path $OutDir "README_CN.md"
if (Test-Path $packDoc) {
  Copy-Item -Force $packDoc $readmeCn
} else {
  Set-Content -Path $readmeCn -Value "See docs\desktop_packaging.md" -Encoding UTF8
}

Copy-Item -Force (Join-Path $Root "scripts\windows\Start-BrailleDemo.bat") (Join-Path $OutDir "Start-BrailleDemo.bat")

Get-ChildItem -Path $OutDir -Recurse -Directory -Filter "__pycache__" -ErrorAction SilentlyContinue |
  Remove-Item -Recurse -Force -ErrorAction SilentlyContinue
Get-ChildItem -Path $OutDir -Recurse -Directory -Filter ".pytest_cache" -ErrorAction SilentlyContinue |
  Remove-Item -Recurse -Force -ErrorAction SilentlyContinue

if ($IncludeVenv) {
  Write-Host "  + .venv-qwen (very large; optional for LAN colleagues only)"
  Copy-Item -Recurse -Force (Join-Path $Root ".venv-qwen") (Join-Path $OutDir ".venv-qwen")
}

if ($MakeZip) {
  if (Test-Path $ZipPath) { Remove-Item -Force $ZipPath }
  Write-Host "Compressing: $ZipPath"
  Compress-Archive -Path $OutDir -DestinationPath $ZipPath -Force
  $sz = (Get-Item $ZipPath).Length / 1MB
  Write-Host ("ZIP approx {0:N1} MB" -f $sz)
}

Write-Host ""
Write-Host "Done. Share dist\chinese-braille-demo\ or chinese-braille-demo.zip"
Write-Host "Recipient steps: README_CN.md / docs\desktop_packaging.md"
