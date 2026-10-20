# Windows CUDA QLoRA retrain v2 report

**Time (Asia/Shanghai):** 2026-10-20 12:52:35 → 13:46:10 (≈53–54 min train wall clock after load)  
**Goal:** Continue / finish the interrupted 80-step QLoRA retrain on 500 synthetic table samples. **No new job was started** — watched the existing process.

## Outcome: COMPLETED

| Item | Result |
|------|--------|
| Status | **Completed** — progress reached **80/80**, then process exited |
| Host | Windows LAPTOP-979NM299 (machine `38a1cb3e-3b52-4f26-943c-9333b6184171`) |
| GPU | NVIDIA GeForce RTX 5060 Laptop GPU, 8151 MiB |
| During run | ~7637 MiB VRAM, GPU util often ~97%, ~32–45 s/it |
| After exit | VRAM **12 MiB**, util 0%; **no** leftover `python.exe` |
| Base model | `models\Vision-Braille-Qwen3-8B` |
| Mode | QLoRA **4-bit**, cuda=True, trainable **43,646,976** / 8,232,711,168 (**0.5302%**) |
| Data | `data/train_tables.jsonl` — **500** ShareGPT examples (formatted/tokenized OK) |
| max_steps | **80 / 80** |
| OOM? | **No** |
| Final loss | **Not recorded** in `train_v2.log` / `train_v2.err` (no `{'loss': ...}` lines; tqdm only). `trainer_state.json` was **not** written under `checkpoint-80`. |
| Adapter | `outputs\lora_tables_win_v2\checkpoint-80\adapter_model.safetensors` (**87,361,592** bytes ≈ 83.3 MB) |
| Also present | `checkpoint-80\adapter_config.json`, tokenizer files, `optimizer.pt`, `training_args.bin` |
| Root `outputs\lora_tables_win_v2\` | Has TRL `README.md` + logs; **no** root-level `adapter_model.safetensors` — use **checkpoint-80** |

## Timeline (Asia/Shanghai)

| When | Event |
|------|--------|
| 12:52:35 | Job started (`train_v2.meta.txt`); launcher PID 29672, worker python **25792** |
| ~12:52–13:46 | Training; err log advanced through 13→…→80/80 |
| 13:46:10 | `checkpoint-80\adapter_model.safetensors` written; err shows `100%\|…\| 80/80 [53:10<00:00, 39.43s/it]` |
| ~13:47 | python gone; nvidia-smi memory.used ≈ 12 MiB |

## Watch notes

- Parent agent interrupt did **not** kill the Windows train; PID 25792 kept running until natural finish.
- Agent briefly lost machine connectivity once mid-poll; retried successfully.
- Did **not** kill the process (progress was continuous past 70; never stuck >15 min).

## Caveats

1. **Loss curve unavailable** from redirected logs — for next run, tee Trainer logging explicitly or ensure `logging_steps` metrics hit a file / `trainer_state.json` is saved.
2. Prefer loading adapter from **`outputs\lora_tables_win_v2\checkpoint-80`**, not the output root.
3. Still a **domain smoke finetune** (synthetic tables, 80 steps) — re-eval holdout `data/synthetic_tables/` before claiming quality.

## Next suggested step

Run holdout eval with the new adapter vs base Qwen3-8B / prior short adapter (`lora_tables_win_short`).

## Artifacts

- Logs: `outputs\lora_tables_win_v2\train_v2.log`, `train_v2.err`
- Adapter: `outputs\lora_tables_win_v2\checkpoint-80\`