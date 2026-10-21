#Requires -Version 5.1
<#
.SYNOPSIS
  合并网页/离线纠错样本后，在本机 CUDA 上短训表格 LoRA。

.DESCRIPTION
  1) 合并 data/user_corrections.jsonl (+ holdout) → data/train_tables_with_errors.jsonl
  2) 用 configs/lora_tables.yaml 跑短 QLoRA（默认 80 steps）
  3) 输出到 outputs/lora_tables_from_corrections
  4) 可选 -CopyToModels 复制适配器到 models/lora_tables

  Usage:
    powershell -ExecutionPolicy Bypass -File scripts\windows\retrain_from_corrections.ps1
    powershell -ExecutionPolicy Bypass -File scripts\windows\retrain_from_corrections.ps1 -MaxSteps 120 -CopyToModels
    powershell -ExecutionPolicy Bypass -File scripts\windows\retrain_from_corrections.ps1 -DryRun
#>
param(
  [int]$MaxSteps = 80,
  [switch]$DryRun,
  [switch]$CopyToModels,
  [switch]$SkipMerge,
  [string]$ModelPath = "",
  [string]$PythonExe = ""
)

$ErrorActionPreference = "Stop"
try { [Console]::OutputEncoding = [System.Text.Encoding]::UTF8 } catch {}

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$Root = (Resolve-Path (Join-Path $ScriptDir "..\..")).Path
Set-Location $Root

Write-Host "========================================"
Write-Host " Retrain from corrections (table LoRA)"
Write-Host " Root: $Root"
Write-Host "========================================"

if (-not $PythonExe) {
  $cand = Join-Path $Root ".venv-qwen\Scripts\python.exe"
  if (Test-Path $cand) { $PythonExe = $cand }
  else {
    $cand2 = Join-Path $Root ".venv\Scripts\python.exe"
    if (Test-Path $cand2) { $PythonExe = $cand2 }
    else { $PythonExe = "python" }
  }
}
Write-Host "[info] Python: $PythonExe"

if (-not $SkipMerge) {
  Write-Host "[1/3] Merge corrections ..."
  & $PythonExe (Join-Path $Root "scripts\merge_user_corrections.py") --prepare-retrain --max-steps $MaxSteps
  if ($LASTEXITCODE -ne 0) { throw "merge_user_corrections.py failed" }
} else {
  Write-Host "[1/3] Skip merge (-SkipMerge)"
}

$outDir = Join-Path $Root "outputs\lora_tables_from_corrections"
$dataPath = Join-Path $Root "data\train_tables_with_errors.jsonl"
$config = Join-Path $Root "configs\lora_tables.yaml"

if (-not (Test-Path $dataPath)) {
  throw "Missing $dataPath — run merge first"
}

Write-Host "[2/3] Train QLoRA max_steps=$MaxSteps → $outDir"
$trainArgs = @(
  (Join-Path $Root "scripts\train_lora_tables.py"),
  "--config", $config,
  "--data-path", $dataPath,
  "--output-dir", $outDir,
  "--bits", "4",
  "--max-steps", "$MaxSteps",
  "--optim", "adamw_torch",
  "--logging-steps", "5"
)
if ($ModelPath) {
  $trainArgs += @("--model-path", $ModelPath)
}
if ($DryRun) {
  $trainArgs += "--dry-run"
}

& $PythonExe @trainArgs
if ($LASTEXITCODE -ne 0) { throw "train_lora_tables.py failed (exit $LASTEXITCODE)" }

if ($DryRun) {
  Write-Host "[OK] Dry-run finished. Drop -DryRun to train for real."
  exit 0
}

Write-Host "[3/3] Post-train"
$adapterSrc = $outDir
$adapterCfg = Join-Path $adapterSrc "adapter_config.json"
$adapterW = Join-Path $adapterSrc "adapter_model.safetensors"
if (-not (Test-Path $adapterCfg)) {
  Write-Host "[WARN] adapter_config.json not found yet under $adapterSrc"
} else {
  Write-Host "[OK] Adapter at $adapterSrc"
}

if ($CopyToModels) {
  $dest = Join-Path $Root "models\lora_tables"
  New-Item -ItemType Directory -Force -Path $dest | Out-Null
  Copy-Item -Force (Join-Path $adapterSrc "adapter_config.json") $dest
  if (Test-Path $adapterW) {
    Copy-Item -Force $adapterW $dest
  } elseif (Test-Path (Join-Path $adapterSrc "adapter_model.bin")) {
    Copy-Item -Force (Join-Path $adapterSrc "adapter_model.bin") $dest
  }
  # copy tokenizer / extras if present
  Get-ChildItem $adapterSrc -File | Where-Object {
    $_.Name -match '^(adapter_|README|training_args)'
  } | ForEach-Object {
    Copy-Item -Force $_.FullName $dest
  }
  Write-Host "[OK] Copied adapter → models\lora_tables"
  Write-Host "请重启 API / 桌面端以加载新适配器。"
} else {
  Write-Host "提示: 加 -CopyToModels 可将适配器复制到 models\lora_tables"
  Write-Host "或手动复制后设置 CBT_ADAPTER_PATH=$outDir 并重启服务。"
}

Write-Host "Done."
