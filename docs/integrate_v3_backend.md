# Integrate LoRA v3 into `backend="qwen8b"`

**Date:** 2026-10-20 (Asia/Shanghai)  
**Host (smoke):** Windows RTX 5060 Laptop 8GB (`LAPTOP-979NM299`)  
**Status:** Done — package API loads PeftModel by default when adapter is present

## What changed

| Path | Change |
|------|--------|
| `src/chinese_braille_toolkit/backends/qwen8b.py` | Real 4-bit base load + optional `PeftModel.from_pretrained`; singleton cache; scaffold fallback without CUDA / under pytest / `CBT_QWEN_STUB=1` |
| `src/chinese_braille_toolkit/api.py` | Forwards `adapter_path`, `model_path`, `quant`, `max_new_tokens` to qwen8b |
| `pyproject.toml` | `[qwen]` extra now includes `peft`, `bitsandbytes`, `sentencepiece` |
| `models/lora_tables/` | Default adapter dir (copy of `outputs/lora_tables_win_v3` weights) |
| `README.md` / `docs/FT.md` | Document default adapter path + env overrides |
| `scripts/smoke_qwen8b_adapter.py` | Package-API smoke for 1–3 holdout cells |

## Default adapter path

Resolution order for LoRA:

1. `translate(..., adapter_path=...)` — pass `""` to force **base-only**
2. Env `CBT_QWEN_ADAPTER` (empty string disables)
3. **`models/lora_tables/`** when `adapter_config.json` + weights exist ← default after this integrate
4. No adapter (base model only)

Base model:

1. `model_path=` kwarg  
2. Env `CBT_QWEN_MODEL`  
3. `models/Vision-Braille-Qwen3-8B`  
4. HF id `Violet-yo/Vision-Braille-Qwen3-8B`

## Usage

```bash
pip install -e ".[qwen]"
# ensure models/lora_tables/ has adapter_config.json + adapter_model.safetensors
```

```python
from chinese_braille_toolkit import translate

text = translate("⠓⠊⠼ ⠍⠊⠼⠂", backend="qwen8b")  # → 姓名
# explicit:
translate("…", backend="qwen8b", adapter_path="outputs/lora_tables_win_v3")
translate("…", backend="qwen8b", adapter_path="")  # base only
```

## Smoke results (Windows CUDA)

Command (from project root, `.venv-qwen`):

```text
PYTHONPATH=src python -u scripts/smoke_qwen8b_adapter.py
```

| id | braille | ref | pred | exact |
|----|---------|-----|------|-------|
| t01-r0-c0 | ⠓⠊⠼ ⠍⠊⠼⠂ | 姓名 | 姓名 | ✅ |
| t01-r0-c1 | ⠬ ⠒ | 语文 | 语文 | ✅ |
| t01-r1-c0 | ⠌⠦ ⠎⠧⠁ | 张三 | 张三 | ✅ |

- **Exact:** 3/3  
- **Elapsed:** ~16 s (cold load + 3 cells)  
- **VRAM:** ~5.67 GB base → **5.83 GB** after adapter  
- **Adapter:** `models/lora_tables` (`r=16`, `alpha=32`, Peft LORA)  
- **Quant:** 4bit-nf4  

JSON dump: `outputs/smoke_integrate_v3_results.json`

## Notes

- Offline / pytest still get `[scaffold-qwen8b]…` (no accidental 8B CPU load).  
- No new training in this step; weights are the existing `lora_tables_win_v3` (200-step) adapter.  
- Full holdout stay at prior eval: **93.3% EM / 120 cells** (`docs/eval_adapter_v3_report.md`).
