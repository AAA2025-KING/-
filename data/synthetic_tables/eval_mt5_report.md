# mT5 real translation eval (synthetic tables)

- Model: `Violet-yo/mt5-small-ft-Chinese-Braille`
- Device: CPU (torch)
- Tokenizer: `use_fast=False` (model card)
- Generate: `max_length=280` encode, `max_new_tokens=300`, `num_beams=5`
- Elapsed: **62.6s** (load + 9 inferences)
- Subset: t01 header row + first data row (8 cells) + 1 partial flat row
- Predictions JSONL: `data/synthetic_tables/eval_mt5_predictions.jsonl`

## Status

**Success:** model downloaded and ran on CPU; 9/9 samples produced predictions. No OOM.

**Quality:** poor on this synthetic-table subset — **0% exact match**, mean CER ≫ 1 because `max_new_tokens=300` (model-card default for news sentences) triggers severe **repetition loops** on 2–4 character table cells. Best cell was `张三` → `31711 张 张 三.` (CER=5). Partial flat row vaguely recovered some headers/`张三`/`92`/`85` but still wrong (CER≈1.55).

**Implication for the package:** do not wire raw mT5 generate() for table cells without length caps / repetition penalty / domain fine-tune; prefer sentence/passage inputs or a dedicated table-cell model.

## Aggregate (cells only)

- N cells: **8**
- Exact-match rate: **0.0%**
- Exact-match (ignore spaces): **0.0%**
- Mean CER (raw): **117.1250**
- Mean CER (no spaces): **70.3750**

## Per-sample

| id | kind | braille | ref_zh | pred | exact | CER | CER_ns |
|----|------|---------|--------|------|-------|-----|--------|
| `t01-r0-c0` | cell | `⠓⠊⠼ ⠍⠊⠼⠂` | 姓名 | 98989 西 米 米 / 米 / 米 / 米 / 米 / 米 / 米 /… | False | 151.5 | 77.0 |
| `t01-r0-c1` | cell | `⠬ ⠒` | 语文 | 2 问 : 语文 语文 语文 语文 语文 语文 语文 语文 语文 语文 语… | False | 222.5 | 147.5 |
| `t01-r0-c2` | cell | `⠱⠥ ⠓⠾` | 数学 | 入学 学位 入学 学业 学, 入学, 入学, 入学, 入学, 入学, 入学… | False | 150.5 | 112.0 |
| `t01-r0-c3` | cell | `⠊⠼ ⠬⠄` | 英语 | 3 / 1 / 1 / 1 / 1 / 1 / 1 / 1 / 1 / 1… | False | 199.5 | 100.0 |
| `t01-r1-c0` | cell | `⠌⠦ ⠎⠧⠁` | 张三 | 31711 张 张 三. | False | 5.0 | 3.5 |
| `t01-r1-c1` | cell | `⠼⠊⠃` | 92 | 92692 2 、 9 、 9 、 9 、 9 、 9 、 9 、 9 、… | False | 121.5 | 61.5 |
| `t01-r1-c2` | cell | `⠼⠓⠓` | 88 | 8888888 88 88 88 88 88 88 88 88 88 88… | False | 57.0 | 39.0 |
| `t01-r1-c3` | cell | `⠼⠓⠑` | 85 | 85853 85, 85, 85, 85, 85, 85, 85, 85,… | False | 29.5 | 22.5 |
| `t01-flat-header-row1` | flat_partial | `⠓⠊⠼ ⠍⠊⠼⠂ \| ⠬ ⠒ \| ⠱⠥ ⠓⠾ \| ⠊⠼ ⠬⠄ \|\| ⠌⠦ ⠎⠧⠁…` | 姓名 \| 语文 \| 数学 \| 英语 \|\| 张三 \| 92 \| 88 \| 85 | 88585 西 米 米 / 余文 / 余文 ( 英语 数学 ) / 余 (… | False | 1.5526 | 1.6667 |

## Notes

- Synthetic Braille from pypinyin `Style.BRAILLE_MAINLAND` (~10% tone); may differ from the model's 10per-Tone training distribution.
- Short table cells (2–4 chars / numbers) are out-of-domain vs news sentences the model was fine-tuned on; low exact-match is expected.
- Separators `|` / `||` in the partial flat row are not Braille tokens the model saw in training.
- Full 8-table flat eval skipped intentionally to control time/disk.
- Chart OCR is out of scope; this only scores translation step 2.
- CER > 1 is expected when hypotheses are far longer than refs due to repetition; treat mean CER here as a failure signal, not a calibrated metric.
- Next ablation (optional): re-run with `max_new_tokens≈16` and `repetition_penalty=1.2` for cells; or evaluate on HF 10per-Tone test sentences where the model is in-domain.

## Inputs / outputs detail

### `t01-r0-c0`

- braille: `⠓⠊⠼ ⠍⠊⠼⠂`
- ref_zh: `姓名`
- pred: `98989 西 米 米 / 米 / 米 / 米 / 米 / 米 / 米 / 米 / 米 / 米 / 米 / 米 / 米 / 米 / 米 / 米 / 米 / 米 / 米 / 米 / 米 / 米 / 米 / 米 / 米 / 米 / 米 / 米 / 米 / 米 / 米 / 米 / 米 / 米 / 米 / 米 / 米 / 米 / 米 / 米 / 米 / 米 / 米 / 米 / 米 / 米 / 米 / 米 / 米 / 米 / 米 / 米 / 米 / 米 / 米 / 米 / 米 / 米 / 米 / 米 / 米 / 米 / 米 / 米 / 米 / 米 / 米 / 米 / 米 / 米 / 米 / 米 / 米 / 米`
- tone: partial; exact=False; CER=151.5; CER_ns=77.0

### `t01-r0-c1`

- braille: `⠬ ⠒`
- ref_zh: `语文`
- pred: `2 问 : 语文 语文 语文 语文 语文 语文 语文 语文 语文 语文 语文 语文 语文 语文 语文 语文 语文 语文 语文 语文 语文 语文 语文 语文 语文 语文 语文 语文 语文 语文 语文 语文 语文 语文 语文 语文 语文 语文 语文 语文 语文 语文 语文 语文 语文 语文 语文 语文 语文 语文 语文 语文 语文 语文 语文 语文 语文 语文 语文 语文 语文 语文 语文 语文 语文 语文 语文 语文 语文 语文 语文 语文 语文 语文 语文 语文 语文 语文 语文 语文 语文 语文 语文 语文 语文 语文 语文 语文 语文 语文 语文 语文 语文 语文 语文 语文 语文 语文 语文 语文 语文 语文 语文 语文 语文 语文 语文 语文 语文 语文 语文 语文 语文 语文 语文 语文 语文 语文 语文 语文 语文 语文 语文 语文 语文 语文 语文 语文 语文 语文 语文 语文 语文 语文 语文 语文 语文 语文 语文 语文 语文 语文 语文 语文 语文 语文 语文 `
- tone: none; exact=False; CER=222.5; CER_ns=147.5

### `t01-r0-c2`

- braille: `⠱⠥ ⠓⠾`
- ref_zh: `数学`
- pred: `入学 学位 入学 学业 学, 入学, 入学, 入学, 入学, 入学, 入学, 入学, 入学, 入学, 入学, 入学, 入学, 入学, 入学, 入学, 入学, 入学, 入学, 入学, 入学, 入学, 入学, 入学, 入学, 入学, 入学, 入学, 入学, 入学, 入学, 入学, 入学, 入学, 入学, 入学, 入学, 入学, 入学, 入学, 入学, 入学, 入学, 入学, 入学, 入学, 入学, 入学, 入学, 入学, 入学, 入学, 入学, 入学, 入学, 入学, 入学, 入学, 入学, 入学, 入学, 入学, 入学, 入学, 入学, 入学, 入学, 入学, 入学, 入学, 入学, 入学, 入学 `
- tone: none; exact=False; CER=150.5; CER_ns=112.0

### `t01-r0-c3`

- braille: `⠊⠼ ⠬⠄`
- ref_zh: `英语`
- pred: `3 / 1 / 1 / 1 / 1 / 1 / 1 / 1 / 1 / 1 / 1 / 1 / 1 / 1 / 1 / 1 / 1 / 1 / 1 / 1 / 1 / 1 / 1 / 1 / 1 / 1 / 1 / 1 / 1 / 1 / 1 / 1 / 1 / 1 / 1 / 1 / 1 / 1 / 1 / 1 / 1 / 1 / 1 / 1 / 1 / 1 / 1 / 1 / 1 / 1 / 1 / 1 / 1 / 1 / 1 / 1 / 1 / 1 / 1 / 1 / 1 / 1 / 1 / 1 / 1 / 1 / 1 / 1 / 1 / 1 / 1 / 1 / 1 / 1 / 1 / 1 / 1 / 1 / 1 / 1 / 1 / 1 / 1 / 1 / 1 / 1 / 1 / 1 / 1 / 1 / 1 / 1 / 1 / 1 / 1 / 1 / 1 / 1 / 1 / 1 /`
- tone: partial; exact=False; CER=199.5; CER_ns=100.0

### `t01-r1-c0`

- braille: `⠌⠦ ⠎⠧⠁`
- ref_zh: `张三`
- pred: `31711 张 张 三.`
- tone: partial; exact=False; CER=5.0; CER_ns=3.5

### `t01-r1-c1`

- braille: `⠼⠊⠃`
- ref_zh: `92`
- pred: `92692 2 、 9 、 9 、 9 、 9 、 9 、 9 、 9 、 9 、 9 、 9 、 9 、 9 、 9 、 9 、 9 、 9 、 9 、 9 、 9 、 9 、 9 、 9 、 9 、 9 、 9 、 9 、 9 、 9 、 9 、 9 、 9 、 9 、 9 、 9 、 9 、 9 、 9 、 9 、 9 、 9 、 9 、 9 、 9 、 9 、 9 、 9 、 9 、 9 、 9 、 9 、 9 、 9 、 9 、 9 、 9 、 9 、 9 、 9 、 9 。`
- tone: none; exact=False; CER=121.5; CER_ns=61.5

### `t01-r1-c2`

- braille: `⠼⠓⠓`
- ref_zh: `88`
- pred: `8888888 88 88 88 88 88 88 88 88 88 88 88 88 88 88 88 88 88 88 88 88 88 88 88 88 88 88 88 88 88 88 88 88 88 88 88 88.`
- tone: none; exact=False; CER=57.0; CER_ns=39.0

### `t01-r1-c3`

- braille: `⠼⠓⠑`
- ref_zh: `85`
- pred: `85853 85, 85, 85, 85, 85, 85, 85, 85, 85, 85, 85, 85, 85, 85.`
- tone: none; exact=False; CER=29.5; CER_ns=22.5

### `t01-flat-header-row1`

- braille: `⠓⠊⠼ ⠍⠊⠼⠂ | ⠬ ⠒ | ⠱⠥ ⠓⠾ | ⠊⠼ ⠬⠄ || ⠌⠦ ⠎⠧⠁ | ⠼⠊⠃ | ⠼⠓⠓ | ⠼⠓⠑`
- ref_zh: `姓名 | 语文 | 数学 | 英语 || 张三 | 92 | 88 | 85`
- pred: `88585 西 米 米 / 余文 / 余文 ( 英语 数学 ) / 余 ( 张 三 / 92 / 82 / 85 / 85 ), 张三 / 92 / 85 / 85 。`
- tone: mixed; exact=False; CER=1.5526; CER_ns=1.6667
