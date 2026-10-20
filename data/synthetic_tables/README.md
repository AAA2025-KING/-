# Synthetic Chinese Braille TABLE evaluation set

## Purpose

Public Chinese Braille corpora (e.g. Violet-yo 10per-Tone) are mostly
**sentence/passage** pairs. This folder provides **small synthetic tables**
so the toolkit can exercise table-shaped inputs (grades, sales, schedule,
stats) before real embossed chart OCR data exists.

## Files

- `tables.jsonl` — one JSON object per line (see schema below)
- `eval_smoke_report.md` — produced by `scripts/eval_table_smoke.py`
- This `README.md`

## Schema (per line)

```json
{
  "id": "t01",
  "title_zh": "...",
  "format": "markdown|csv_cells",
  "cells": [[{"zh": "姓名", "braille": "...", "tone": "none|partial|full"}, ...], ...],
  "flat_zh": "row-major joined reference text",
  "flat_braille": "row-major joined braille with separators",
  "notes": "..."
}
```

## Synthesis method

1. Hand-authored Chinese table grids (headers + a few data rows).
2. Convert each cell with **pypinyin**:
   - Default: `Style.BRAILLE_MAINLAND` (no tone) — mimics common tone omission.
   - With probability ≈10% per CJK syllable: `Style.BRAILLE_MAINLAND_TONE`.
3. Arabic digits → Chinese Braille numbers (`⠼` + a–j patterns).
4. Syllables inside a cell are joined with ASCII spaces.
5. **Cell separator:** ` | ` (space-pipe-space).
6. **Row separator** in flat fields: ` || `.

Regenerate:

```bash
python scripts/build_synthetic_tables.py
```

## Limitations (read before scoring models)

- pypinyin Braille is **approximately** aligned with mainland Chinese Braille
  (GF 0019-ish). It is **not** professional proofreading or embosser QA.
- Multi-character words are converted character-by-character; word grouping
  may differ from published Braille textbooks.
- Layout / ruling lines / spatial table structure are **not** encoded — only
  cell text in row-major order. Chart OCR is a separate step.
- Decimal points in numbers (e.g. `5.0`) keep ASCII `.` between Braille digit
  groups; real embossers may use a Braille decimal mark.
- These tables are **synthetic**. Do not treat BLEU/CER here as paper-grade
  benchmarks; use them for pipeline smoke and relative comparisons.

## License note

Synthetic content in this folder is generated for evaluation scaffolding.
Downstream model weights (mT5 / Qwen Braille) have their own licenses
(often non-commercial) — check before redistribution or paid services.
