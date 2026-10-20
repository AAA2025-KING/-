# Desktop packaging smoke (2026-10-20, Asia/Shanghai)

## Pack
- Command: `Pack-DemoZip.ps1 -MakeZip` on Windows Desktop project
- Output: `dist\chinese-braille-demo\` + `dist\chinese-braille-demo.zip` **~67.6 MB**
- Included: code, `models\lora_tables\`, scripts, docs
- Excluded: base `Vision-Braille-Qwen3-8B` weights (only `README_DOWNLOAD.txt` placeholder) — **NO_BASE_WEIGHTS_OK**

## Gradio health
- Mode: `CBT_QWEN_STUB=1` (UI up without loading 8B)
- Direct: `python apps\gradio_demo.py` → HTTP 200 on `http://127.0.0.1:7860/` → **SMOKE_PASS** (stopped after check)
- Via `scripts\windows\Start-BrailleDemo.bat` → HTTP 200 → **BAT_SMOKE_PASS** (python killed after check)

## Preflight on this machine
- venv `.venv-qwen`, demo script, LoRA, base config: all present
