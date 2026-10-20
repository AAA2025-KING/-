# Retrain v3 continue report (lora_tables_win_v3)

**Status:** SUCCESS  
**Timezone:** Asia/Shanghai (UTC+8)

## Summary

Fresh 200-step QLoRA table train finished. Resume-from-`checkpoint-80` was attempted earlier and failed (incomplete ckpt + bitsandbytes `paged_adamw_8bit` crash); this run used **adamw_torch** into a new `outputs\lora_tables_win_v3` directory.

| Field | Value |
|-------|--------|
| Start | 2026-10-20 **14:23:58** |
| End (adapter mtime) | 2026-10-20 **17:26:11** |
| Wall time | **~3h 02m** (`train_runtime` 10920 s ≈ 3.03 h) |
| Steps | **200/200** |
| Optimizer | `adamw_torch` |
| Bits | 4 (QLoRA) |
| PID | 2248 (child python 27356); both exited cleanly |
| Peak VRAM observed | **~7779 MiB**, util **100%** during train; **~12 MiB / 0%** after exit |
| Final `train_loss` | **1.629** |
| Epoch | 3.176 |
| Adapter | `outputs\lora_tables_win_v3\` (`adapter_model.safetensors` ≈ **83.3 MB**) |
| Checkpoints | `checkpoint-100`, `checkpoint-200` |
| Metrics | `outputs\lora_tables_win_v3\train_metrics.json` (41 entries) |

## Paths

- Project: `C:\Users\LENOVO\Desktop\chinese-braille-toolkit`
- Output / adapter root: `C:\Users\LENOVO\Desktop\chinese-braille-toolkit\outputs\lora_tables_win_v3`
- Final adapter: `...\lora_tables_win_v3\adapter_model.safetensors`
- Checkpoint-200: `...\lora_tables_win_v3\checkpoint-200\`
- Logs: `train_v3.log`, `train_v3.err`, `train_v3.meta.txt`

## Command

```text
python -u scripts\train_lora_tables.py --bits 4 --max-steps 200 --logging-steps 5 --optim adamw_torch --model-path models\Vision-Braille-Qwen3-8B --data-path data\train_tables.jsonl --output-dir outputs\lora_tables_win_v3
```

## Loss summary (logged every 5 steps)

| Band | Approx loss |
|------|-------------|
| First logged | 9.06 → 6.84 → 3.33 |
| Mid (~steps 100–150 band) | ~1.07 avg |
| Late (last 10 log points) | ~1.10 avg |
| Last logged step losses | 0.82 … 1.38 (final log point **1.375**) |
| Overall mean of step losses | **~1.629** (matches `train_loss`) |
| Min / max step loss | **0.811** / **9.058** |

Training progressed steadily; no stall. Progress bar reached `200/200` in ~3h01m before adapter save.

## Notes

- No holdout eval in this watch task.
- Do not restart training; artifacts are ready for a later eval against holdout synthetic tables if desired.
