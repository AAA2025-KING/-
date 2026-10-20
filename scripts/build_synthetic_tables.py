#!/usr/bin/env python3
"""Build synthetic Chinese Braille TABLE evaluation samples.

Uses pypinyin Style.BRAILLE_MAINLAND (no tone) by default to mimic real
tone omission; ~10% of syllables randomly use BRAILLE_MAINLAND_TONE.

Not professional embosser QA — approximate GF 0019-ish via pypinyin.
"""

from __future__ import annotations

import argparse
import json
import random
import re
from pathlib import Path

from pypinyin import Style, lazy_pinyin

# Cell separator in flat_braille / markdown rows (documented in README).
CELL_SEP = " | "
ROW_SEP = " || "

# Chinese mainland Braille number indicator + digit letters (1-9,0 → a-j).
_DIGIT_TO_BRAILLE = {
    "1": "⠁",
    "2": "⠃",
    "3": "⠉",
    "4": "⠙",
    "5": "⠑",
    "6": "⠋",
    "7": "⠛",
    "8": "⠓",
    "9": "⠊",
    "0": "⠚",
}

_DIGITS_RE = re.compile(r"\d+")
_CJK_RE = re.compile(r"[\u4e00-\u9fff]+")


def arabic_digits_to_braille(num: str) -> str:
    """Convert an Arabic numeral string to Chinese Braille number form."""
    body = "".join(_DIGIT_TO_BRAILLE.get(ch, ch) for ch in num)
    return "⠼" + body


def zh_to_braille_syllables(
    text: str,
    *,
    tone_prob: float,
    rng: random.Random,
) -> list[tuple[str, str]]:
    """Return list of (braille_syllable_or_token, tone_tag).

    tone_tag is 'full' if BRAILLE_MAINLAND_TONE was used, else 'none'.
    Non-CJK runs (digits, punctuation, Latin) are kept as tokens.
    """
    out: list[tuple[str, str]] = []
    i = 0
    while i < len(text):
        ch = text[i]
        if ch.isdigit():
            j = i
            while j < len(text) and text[j].isdigit():
                j += 1
            out.append((arabic_digits_to_braille(text[i:j]), "none"))
            i = j
            continue
        if "\u4e00" <= ch <= "\u9fff":
            j = i
            while j < len(text) and "\u4e00" <= text[j] <= "\u9fff":
                j += 1
            chunk = text[i:j]
            # Per-character so tone can be applied at syllable granularity.
            for char in chunk:
                use_tone = rng.random() < tone_prob
                style = Style.BRAILLE_MAINLAND_TONE if use_tone else Style.BRAILLE_MAINLAND
                syls = lazy_pinyin(char, style=style)
                tag = "full" if use_tone else "none"
                for s in syls:
                    out.append((s, tag))
            i = j
            continue
        # Keep punctuation / spaces / Latin as-is (single char tokens).
        if ch.strip() == "":
            i += 1
            continue
        out.append((ch, "none"))
        i += 1
    return out


def cell_tone_label(tags: list[str]) -> str:
    if not tags:
        return "none"
    n_full = sum(1 for t in tags if t == "full")
    if n_full == 0:
        return "none"
    if n_full == len(tags):
        return "full"
    return "partial"


def convert_cell(zh: str, *, tone_prob: float, rng: random.Random) -> dict:
    pairs = zh_to_braille_syllables(zh, tone_prob=tone_prob, rng=rng)
    braille = " ".join(b for b, _ in pairs)
    tone = cell_tone_label([t for _, t in pairs])
    return {"zh": zh, "braille": braille, "tone": tone}


def flatten_table(cells: list[list[dict]]) -> tuple[str, str]:
    flat_zh_rows = []
    flat_br_rows = []
    for row in cells:
        flat_zh_rows.append(CELL_SEP.join(c["zh"] for c in row))
        flat_br_rows.append(CELL_SEP.join(c["braille"] for c in row))
    return ROW_SEP.join(flat_zh_rows), ROW_SEP.join(flat_br_rows)


def make_table(
    table_id: str,
    title_zh: str,
    grid_zh: list[list[str]],
    *,
    tone_prob: float,
    rng: random.Random,
    notes_extra: str = "",
) -> dict:
    cells = [
        [convert_cell(zh, tone_prob=tone_prob, rng=rng) for zh in row]
        for row in grid_zh
    ]
    flat_zh, flat_braille = flatten_table(cells)
    notes = (
        "synthetic via pypinyin Style.BRAILLE_MAINLAND (+~10% TONE); "
        "not official embosser QA; cell sep=' | ', row sep=' || '"
    )
    if notes_extra:
        notes = notes + "; " + notes_extra
    return {
        "id": table_id,
        "title_zh": title_zh,
        "format": "markdown|csv_cells",
        "cells": cells,
        "flat_zh": flat_zh,
        "flat_braille": flat_braille,
        "notes": notes,
    }


def default_tables(*, tone_prob: float, rng: random.Random) -> list[dict]:
    """Eight small synthetic tables: grades, sales, schedule, stats, etc."""
    specs: list[tuple[str, str, list[list[str]], str]] = [
        (
            "t01",
            "三年级期中成绩表",
            [
                ["姓名", "语文", "数学", "英语"],
                ["张三", "92", "88", "85"],
                ["李四", "78", "95", "80"],
                ["王五", "85", "82", "90"],
            ],
            "grades",
        ),
        (
            "t02",
            "十月份商品销售表",
            [
                ["商品", "数量", "单价", "金额"],
                ["铅笔", "120", "2", "240"],
                ["笔记本", "80", "5", "400"],
                ["橡皮", "50", "1", "50"],
            ],
            "sales",
        ),
        (
            "t03",
            "周一课程表",
            [
                ["节次", "时间", "课程", "教室"],
                ["第一节", "8时", "语文", "101"],
                ["第二节", "9时", "数学", "101"],
                ["第三节", "10时", "英语", "203"],
            ],
            "schedule",
        ),
        (
            "t04",
            "班级考试统计",
            [
                ["科目", "平均", "最高", "最低", "及格率"],
                ["语文", "82", "98", "61", "92"],
                ["数学", "79", "100", "55", "88"],
                ["英语", "84", "97", "66", "94"],
            ],
            "simple stats",
        ),
        (
            "t05",
            "实验室器材借用登记",
            [
                ["姓名", "器材", "数量", "日期"],
                ["赵六", "显微镜", "2", "3月5日"],
                ["钱七", "天平", "1", "3月6日"],
                ["孙八", "试管", "10", "3月7日"],
            ],
            "lab inventory log",
        ),
        (
            "t06",
            "食堂一周菜单摘要",
            [
                ["星期", "午餐", "人数"],
                ["一", "米饭炒菜", "320"],
                ["三", "面条汤", "280"],
                ["五", "饺子", "350"],
            ],
            "canteen schedule summary",
        ),
        (
            "t07",
            "视力检查结果简表",
            [
                ["姓名", "左眼", "右眼", "建议"],
                ["周九", "5.0", "4.8", "复查"],
                ["吴十", "4.6", "4.7", "配镜"],
            ],
            "vision check (decimal digits kept as Braille numbers)",
        ),
        (
            "t08",
            "小组积分榜",
            [
                ["组别", "得分", "名次"],
                ["红组", "45", "1"],
                ["蓝组", "42", "2"],
                ["绿组", "38", "3"],
            ],
            "team scoreboard",
        ),
    ]
    tables = []
    for tid, title, grid, extra in specs:
        tables.append(
            make_table(tid, title, grid, tone_prob=tone_prob, rng=rng, notes_extra=extra)
        )
    return tables


def write_outputs(out_dir: Path, tables: list[dict]) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    jsonl_path = out_dir / "tables.jsonl"
    with jsonl_path.open("w", encoding="utf-8") as f:
        for row in tables:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")

    readme = out_dir / "README.md"
    readme.write_text(
        """# Synthetic Chinese Braille TABLE evaluation set

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
""",
        encoding="utf-8",
    )
    print(f"Wrote {len(tables)} tables → {jsonl_path}")
    print(f"Wrote {readme}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--out-dir",
        type=Path,
        default=Path(__file__).resolve().parents[1] / "data" / "synthetic_tables",
    )
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--tone-prob", type=float, default=0.10)
    args = parser.parse_args()
    rng = random.Random(args.seed)
    tables = default_tables(tone_prob=args.tone_prob, rng=rng)
    write_outputs(args.out_dir, tables)


if __name__ == "__main__":
    main()
