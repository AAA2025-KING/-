# Windows CUDA short QLoRA train report

**Time (Asia/Shanghai):** 2026-10-20 ~12:20–12:40  
**Goal:** dry-run + 15 QLoRA steps on RTX 5060

## Outcome: SUCCESS (train steps); save hang

| Item | Result |
|------|--------|
| Dry-run | OK — 43 examples, bits=4, r=16/α=32 |
| Host | **Windows LAPTOP-979NM299** (machine `38a1cb3e-…`) |
| GPU | NVIDIA GeForce RTX 5060 Laptop GPU, 8151 MiB |
| Venv | `.venv-qwen` — torch 2.11.0+cu128, CUDA True, bf16 True |
| Base model | `models\Vision-Braille-Qwen3-8B` (4/4 shards complete) |
| Mode | **QLoRA 4-bit NF4**, `device_map={"": 0}` (forced; `auto` had wrongly CPU-offloaded) |
| Steps | **15 / 15** (~11 min train; ~40–50 s/step) |
| OOM? | **No** |
| Peak VRAM (approx) | **~7730 / 8151 MiB** during run |
| Trainable params | 43,646,976 / 8,232,711,168 (**0.5302%**) |
| Mean train loss | **~5.42** (9.06 → 3.85; see curve) |
| Adapter | `outputs\lora_tables_win_short\` (+ `checkpoint-15\`) |

## Loss curve (per step)

| step | loss | token_acc | notes |
|------|------|-----------|-------|
| 1 | 9.064 | 0.210 | |
| 2 | 8.340 | 0.214 | |
| 3 | 7.554 | 0.210 | |
| 4 | 6.630 | 0.263 | |
| 5 | 6.846 | 0.365 | |
| 6 | 4.708 | 0.467 | epoch≈1 |
| 7 | 4.910 | 0.566 | |
| 8 | 4.071 | 0.640 | |
| 9 | 4.293 | 0.634 | |
| 10 | 4.307 | 0.671 | |
| 11 | 4.875 | 0.637 | |
| 12 | 3.052 | 0.741 | epoch≈2 |
| 13 | 4.866 | 0.637 | |
| 14 | 3.920 | 0.665 | |
| 15 | 3.853 | 0.669 | |

Trainer finished 15 steps; `checkpoint-15\adapter_model.safetensors` ≈ **83.3 MB** written at ~12:32.

## Caveats

1. **`trainer.save_model()` hung** after step 15 (GPU idle at 0%, VRAM still held). Process **PID 42312** (`python.exe`) could not be killed from the agent (Access Denied). Please end it in Task Manager if VRAM stays ~7.7 GB.
2. First attempt with `device_map="auto"` failed: HF dispatched layers to CPU. Script patched to force `{"": 0}` when CUDA + bits=4.
3. VMware Ubuntu VM was **left running** (~6+ GB system RAM). Train still fit; closing the VM would free RAM for larger runs.
4. This is a **smoke finetune** only (43 placeholder cells, 15 steps) — not production quality.

## Reproduce

```powershell
cd $env:USERPROFILE\Desktop\chinese-braille-toolkit
.\.venv-qwen\Scripts\Activate.ps1
python scripts\train_lora_tables.py --dry-run `
  --model-path models\Vision-Braille-Qwen3-8B --bits 4 --max-steps 15
python scripts\train_lora_tables.py --bits 4 --max-steps 15 --lora-r 16 --lora-alpha 32 `
  --model-path models\Vision-Braille-Qwen3-8B `
  --output-dir outputs\lora_tables_win_short
```

Log: `outputs\lora_tables_win_short_train.log`
