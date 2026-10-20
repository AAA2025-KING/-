# Adapter holdout eval — `lora_tables_win_v3` (200 steps)

**Date:** 2026-10-20 (Asia/Shanghai)  
**Host:** Windows-RTX5060-8GB (`LAPTOP-979NM299`)  
**Status:** Success — 128/128 samples, no OOM

## Setup

| Item | Value |
|------|--------|
| Base | `models/Vision-Braille-Qwen3-8B` (4-bit NF4) |
| Adapter | `outputs/lora_tables_win_v3` (root; same as `checkpoint-200`, ~83MB) |
| Holdout | `data/synthetic_tables/tables.jsonl` — **all** 8 tables (t01–t08) |
| Samples | **120 cells** + **8** flat_partial = 128 |
| Generate | greedy, cell `max_new=32` / flat `64`, `repetition_penalty=1.15` |
| Peak VRAM | **5.91 GB** / 7.96 GB |
| Elapsed | **153.3 s** (load + 128 inferences) |

Full per-sample table: `data/synthetic_tables/eval_qwen8b_adapter_v3_report.md`  
Predictions: `data/synthetic_tables/eval_qwen8b_adapter_v3_predictions.jsonl`

## Aggregate (cells only)

| Metric | Adapter v3 (holdout all) |
|--------|--------------------------|
| N cells | **120** |
| Exact-match | **93.3%** (112/120) |
| Exact-match (ignore spaces) | **93.3%** |
| Mean CER (raw) | **0.2069** |
| Mean CER (no spaces) | **0.1861** |
| Mean CER excl. 1 runaway (CER≥5) | **0.0490** (N=119) |
| N flats | 8 (7/8 exact) |

### Per-table (cells) — v3 vs v2

| table | N | v3 EM | v3 CER | v2 EM | v2 CER |
|-------|---|-------|--------|-------|--------|
| t01 | 16 | **100%** | 0.000 | 94% | 0.062 |
| t02 | 16 | **94%** | 0.031 | 94% | 0.062 |
| t03 | 16 | **88%** | 0.094 | 81% | 0.156 |
| t04 | 20 | **90%** | 1.000 | 75% | 0.400 |
| t05 | 16 | **88%** | 0.115 | 62% | 0.365 |
| t06 | 12 | **92%** | 0.083 | 100% | 0.000 |
| t07 | 12 | **100%** | 0.000 | 83% | 0.083 |
| t08 | 12 | **100%** | 0.000 | 75% | 0.167 |

## vs prior v2 (`checkpoint-80`)

| | Adapter v2 (ckpt-80) | Adapter v3 (200 steps) | Δ |
|--|----------------------|------------------------|---|
| Exact-match | 82.5% (99/120) | **93.3% (112/120)** | **+10.8 pp** |
| Mean CER (raw) | 0.1778 | 0.2069 | +0.029 (one runaway) |
| Mean CER excl. CER≥5 | — | **0.0490** | much better typical errors |
| Peak VRAM | 5.91 GB | 5.91 GB | same |
| Elapsed | 150.2 s | 153.3 s | ~same |

**One-liner:** v3 raises holdout exact-match from **82.5% → 93.3%**; raw mean CER ticks up only because **one** cell (`t04-r0-c3` 最低) dumped garbage (`fragistics` / tool markup, CER=19). Excluding that outlier, mean CER is **0.049**.

## Example rows

### Exact

| id | ref | pred | CER |
|----|-----|------|-----|
| t01-r0-c0 | 姓名 | 姓名 | 0 |
| t01-r0-c1 | 语文 | 语文 | 0 |
| t01-r0-c2 | 数学 | 数学 | 0 |
| t01-r0-c3 | 英语 | 英语 | 0 |
| t01-r1-c0 | 张三 | 张三 | 0 |
| t01-r1-c1 | 92 | 92 | 0 |

### Near-miss / errors

| id | ref | pred | CER |
|----|-----|------|-----|
| t02-r0-c2 | 单价 | 单位 | 0.5 |
| t03-r0-c0 | 节次 | 解此 | 1.0 |
| t03-r0-c3 | 教室 | 教师 | 0.5 |
| t04-r0-c4 | 及格率 | 几个绿 | 1.0 |
| t05-r1-c0 | 赵六 | 兆六 | 0.5 |
| t05-r1-c1 | 显微镜 | 线位机1 | 1.3333 |
| t06-r3-c0 | 五 | 吴 | 1.0 |

### Worst (runaway)

| id | ref | pred | CER |
|----|-----|------|-----|
| t04-r0-c3 | 最低 | `组别 \| fragistics \| </tool_response> 格會員` | 19.0 |
| t05-r1-c1 | 显微镜 | `线位机1` | 1.3333 |
| t03-r0-c0 | 节次 | `解此` | 1.0 |

## Takeaway

- Longer train (200 vs 80) clearly helps EM on this synthetic holdout.
- Remaining misses are mostly short header homophones / near-homophones (数量→数位, 教室→教师, 周次→周知, etc.).
- One generation runaway remains; consider stronger stop / lower max_new or post-truncation for production.
- No new training in this step.

