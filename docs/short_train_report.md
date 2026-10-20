# Short LoRA train trial report

**Time (Asia/Shanghai):** 2026-10-20 ~11:53  
**Goal:** dry-run OK + a few optimizer steps (or clear blocker)

## Outcome: SUCCESS (box fallback)

| Item | Result |
|------|--------|
| Dry-run | OK on box and Windows (after UTF-8 / safer Braille preview); 43 examples |
| Host used for real steps | **box** `/workspace/chinese-braille-toolkit` (no GPU) |
| Windows (priority) | RTX 5060 CUDA OK, but base model incomplete (shards 2–3 still downloading ~2–3 MB/s) |
| Steps completed | **3 / 3** |
| OOM? | **No** |
| Mean train loss | **8.95** (step losses 8.741 → 9.048 → 9.06) |
| Trainable params | 21,823,488 (LoRA r=8, ~0.27%) |
| Adapter path | `/workspace/chinese-braille-toolkit/outputs/lora_tables_short/` |

## What worked

- Base model: local `models/Vision-Braille-Qwen3-8B` (complete on box)
- Mode: **4-bit NF4 on CPU** (`device_map={"": "cpu"}`) after `pip install kernels`
- Data: first 8 rows of `data/train_tables_placeholder.jsonl` (43 total)
- Runtime: ~48s for 3 steps (~16s/step on CPU)
- Artifacts: `adapter_model.safetensors` (~42 MB), `adapter_config.json`, `checkpoint-3/`, tokenizer files

## What failed / limits

1. **Windows CUDA train not run yet** — model shards incomplete:
   - `model-00002` / `model-00003` were still `.part` during this trial
   - `pip install -e ".[train]"` was in progress (peft/datasets/trl/pyarrow)
2. **bits=16 + disk offload on box** loads LoRA but **Trainer fails**:
   - `unknown device type for autocast in get_autocast_dispatch_key_from_device_type`
   - meta/disk-offloaded params are not trainable via standard SFTTrainer
3. **transformers 5.20** dropped `warmup_ratio` → script now uses `warmup_steps`
4. This smoke run is **not** a quality finetune (3 steps, tiny data, high loss)

## Commands (reproduce on box)

```bash
cd /workspace/chinese-braille-toolkit
.venv/bin/pip install -e ".[train]" 'kernels>=0.11.1'
.venv/bin/python scripts/train_lora_tables.py --dry-run \
  --model-path models/Vision-Braille-Qwen3-8B
# Working short train (CPU 4-bit):
.venv/bin/python scripts/train_lora_tables.py \
  --model-path models/Vision-Braille-Qwen3-8B \
  --bits 4 --max-steps 5 --lora-r 8 --lora-alpha 16 \
  --output-dir outputs/lora_tables_short
```

## Next (Windows CUDA)

When shards 2–3 finish under `Desktop\chinese-braille-toolkit\models\Vision-Braille-Qwen3-8B\`:

```powershell
cd $env:USERPROFILE\Desktop\chinese-braille-toolkit
.\.venv-qwen\Scripts\Activate.ps1
pip install -e ".[train]"
python scripts/train_lora_tables.py --dry-run --model-path models\Vision-Braille-Qwen3-8B
python scripts/train_lora_tables.py --bits 4 --max-steps 20 --lora-r 16 `
  --model-path models\Vision-Braille-Qwen3-8B --output-dir outputs\lora_tables_short
```
