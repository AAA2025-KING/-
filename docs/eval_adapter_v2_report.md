# Adapter holdout eval — `lora_tables_win_v2/checkpoint-80`

**Date:** 2026-10-20 (Asia/Shanghai)  
**Host:** Windows-RTX5060-8GB (`LAPTOP-979NM299`)  
**Status:** Success — 128/128 samples, no OOM

## Setup

| Item | Value |
|------|--------|
| Base | `models/Vision-Braille-Qwen3-8B` (4-bit NF4) |
| Adapter | `outputs/lora_tables_win_v2/checkpoint-80` (~83MB `adapter_model.safetensors`) |
| Holdout | `data/synthetic_tables/tables.jsonl` — **all** 8 tables (t01–t08) |
| Samples | **120 cells** + **8** flat_partial (header+row1 per table) = 128 |
| Generate | greedy, cell `max_new=32` / flat `64`, `repetition_penalty=1.15` |
| Peak VRAM | **5.91 GB** / 7.96 GB |
| Elapsed | **150.2 s** (load + 128 inferences) |

Full per-sample table: `data/synthetic_tables/eval_qwen8b_adapter_v2_report.md`  
Predictions: `data/synthetic_tables/eval_qwen8b_adapter_v2_predictions.jsonl`

## Aggregate (cells only)

| Metric | Adapter v2 (holdout all) |
|--------|--------------------------|
| N cells | **120** |
| Exact-match | **82.5%** (99/120) |
| Exact-match (ignore spaces) | **82.5%** |
| Mean CER (raw) | **0.1778** |
| Mean CER (no spaces) | **0.1694** |
| N flats | 8 |

### Per-table (cells)

| table | N | EM | mean CER |
|-------|---|----|----------|
| t01 | 16 | 94% | 0.062 |
| t02 | 16 | 94% | 0.062 |
| t03 | 16 | 81% | 0.156 |
| t04 | 20 | 75% | 0.400 |
| t05 | 16 | 62% | 0.365 |
| t06 | 12 | **100%** | 0.000 |
| t07 | 12 | 83% | 0.083 |
| t08 | 12 | 75% | 0.167 |

## vs prior base (t01-only)

Prior base report (`eval_qwen8b_report.md`): **t01 header+row1 only** — 8 cells, **0% EM**, mean CER **~10** (repetition / garbage).

Apples-to-apples on the **same 8 t01 cells** with adapter:

| | Base (t01 8 cells) | Adapter checkpoint-80 (same 8) | Adapter full holdout (120) |
|--|--------------------|--------------------------------|----------------------------|
| Exact-match | 0% | **87.5%** (7/8) | **82.5%** |
| Mean CER | ~10.0 | **0.125** | **0.178** |

Note: subset differs for the full holdout row (120 cells vs 8). Adapter clearly fixes the base’s short-cell collapse on this synthetic set.

## Example rows

### Best (exact)

| id | ref | pred | CER |
|----|-----|------|-----|
| t01-r0-c0 | 姓名 | 姓名 | 0 |
| t01-r0-c1 | 语文 | 语文 | 0 |
| t01-r0-c2 | 数学 | 数学 | 0 |
| t01-r1-c0 | 张三 | 张三 | 0 |
| t01-r1-c1 | 92 | 92 | 0 |

### Near-miss

| id | ref | pred | CER |
|----|-----|------|-----|
| t03-r0-c3 | 教室 | 教师 | 0.5 |
| t05-r2-c1 | 天平 | 天皮 | 0.5 |
| t07-r2-c0 | 吴十 | 五十 | 0.5 |
| t07-r2-c3 | 配镜 | 配籍 | 0.5 |

### Worst

| id | ref | pred | CER |
|----|-----|------|-----|
| t04-r0-c1 | 平均 | 品 \| 金额 | 3.0 |
| t04-r0-c3 | 最低 | 祖辈的遗 | 2.0 |
| t05-r1-c1 | 显微镜 | 县五类及 | 1.33 |
| t01-r0-c3 | 英语 | 一与 | 1.0 |
| t02-r0-c2 | 单价 | 担架 | 1.0 |

## Script change

`scripts/eval_qwen8b_tables.py` now supports `--adapter`, `--subset {t01,all}` (default `all`), `--report`, `--preds`. Adapter path recorded in report meta.

## One-line takeaway

**checkpoint-80** lifts holdout cell exact-match from base’s 0% (t01-only, CER~10) to **82.5% EM / mean CER 0.18** on all 120 holdout cells (~5.9GB peak, ~2.5 min). Remaining errors are mostly short homophone / OOV headers (e.g. 英语→一与, 单价→担架).
