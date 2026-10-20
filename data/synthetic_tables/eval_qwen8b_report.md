# Qwen3-8B real translation eval (synthetic tables)

- Model: `C:\Users\LENOVO\Desktop\chinese-braille-toolkit\models\Vision-Braille-Qwen3-8B`
- Host: **Windows-RTX5060-8GB**
- Quantization: **4bit-nf4**
- CUDA: `True` gpu=`NVIDIA GeForce RTX 5060 Laptop GPU` VRAM=7.96GB peak_alloc=5.746GB
- Chat template: model-card system + user (`盲文内容是:` ASCII colon); strip `对应的中文内容是：`
- Generate: greedy (`do_sample=False`), `max_new_tokens` cell=32 / flat=64, `repetition_penalty=1.15`
- License note: CC BY-NC-SA 4.0 — research eval only
- Elapsed: **36.3s** (load + 9 inferences)
- Subset: same as mT5 — t01 header + first data row (8 cells) + 1 partial flat
- Predictions JSONL: `data\synthetic_tables\eval_qwen8b_predictions.jsonl`

## Status

**Success:** 9/9 samples produced predictions. No OOM.

## Aggregate (cells only)

- N cells: **8**
- Exact-match rate: **0.0%**
- Exact-match (ignore spaces): **0.0%**
- Mean CER (raw): **10.0000**
- Mean CER (no spaces): **10.0000**

## Per-sample

| id | kind | braille | ref_zh | pred | exact | CER | CER_ns |
|----|------|---------|--------|------|-------|-----|--------|
| `t01-r0-c0` | cell | `⠓⠊⠼ ⠍⠊⠼⠂` | 姓名 | 西1米1.8分贝贝贝贝贝贝…………………………………………… | False | 15.0 | 15.0 |
| `t01-r0-c1` | cell | `⠬ ⠒` | 语文 | 余问。 | False | 1.5 | 1.5 |
| `t01-r0-c2` | cell | `⠱⠥ ⠓⠾` | 数学 | 数论学是数学的一个分支，研究自然界的规律和关系。它包括代数、几何、拓扑等概念。 | False | 18.5 | 18.5 |
| `t01-r0-c3` | cell | `⠊⠼ ⠬⠄` | 英语 | 一○与 | False | 1.5 | 1.5 |
| `t01-r1-c0` | cell | `⠌⠦ ⠎⠧⠁` | 张三 | 张三１。 | False | 1.0 | 1.0 |
| `t01-r1-c1` | cell | `⠼⠊⠃` | 92 | 921.8.16.17.18.19.20.21.22. | False | 12.5 | 12.5 |
| `t01-r1-c2` | cell | `⠼⠓⠓` | 88 | 88.16.4.101953.11.2.4.10195 | False | 12.5 | 12.5 |
| `t01-r1-c3` | cell | `⠼⠓⠑` | 85 | 85.1964年夏天,夏天,夏天,夏天,夏天,夏天,夏天,夏天,夏天,夏天 | False | 17.5 | 17.5 |
| `t01-flat-header-row1` | flat_partial | `⠓⠊⠼ ⠍⠊⠼⠂ \| ⠬ ⠒ \| ⠱⠥ ⠓⠾ \| ⠊⠼ ⠬⠄ \|\| ⠌⠦ ⠎⠧⠁…` | 姓名 \| 语文 \| 数学 \| 英语 \|\| 张三 \| 92 \| 88 \| 85 | 西1米/\|语文\|数学\|92\|88\|85 | False | 0.6316 | 0.4583 |

## Notes

- Same synthetic Braille as mT5 run (pypinyin ~10% tone); OOD vs model's passage training.
- Short table cells + `|` separators are out-of-domain; compare primarily vs mT5 on this set.
- Generation capped to avoid the repetition loops seen in mT5 with max_new_tokens=300.
- Chart OCR out of scope; translation step 2 only.

## Inputs / outputs detail

### `t01-r0-c0`

- braille: `⠓⠊⠼ ⠍⠊⠼⠂`
- ref_zh: `姓名`
- pred: `西1米1.8分贝贝贝贝贝贝……………………………………………`
- tone: partial; exact=False; CER=15.0; CER_ns=15.0

### `t01-r0-c1`

- braille: `⠬ ⠒`
- ref_zh: `语文`
- pred: `余问。`
- tone: none; exact=False; CER=1.5; CER_ns=1.5

### `t01-r0-c2`

- braille: `⠱⠥ ⠓⠾`
- ref_zh: `数学`
- pred: `数论学是数学的一个分支，研究自然界的规律和关系。它包括代数、几何、拓扑等概念。`
- tone: none; exact=False; CER=18.5; CER_ns=18.5

### `t01-r0-c3`

- braille: `⠊⠼ ⠬⠄`
- ref_zh: `英语`
- pred: `一○与`
- tone: partial; exact=False; CER=1.5; CER_ns=1.5

### `t01-r1-c0`

- braille: `⠌⠦ ⠎⠧⠁`
- ref_zh: `张三`
- pred: `张三１。`
- tone: partial; exact=False; CER=1.0; CER_ns=1.0

### `t01-r1-c1`

- braille: `⠼⠊⠃`
- ref_zh: `92`
- pred: `921.8.16.17.18.19.20.21.22.`
- tone: none; exact=False; CER=12.5; CER_ns=12.5

### `t01-r1-c2`

- braille: `⠼⠓⠓`
- ref_zh: `88`
- pred: `88.16.4.101953.11.2.4.10195`
- tone: none; exact=False; CER=12.5; CER_ns=12.5

### `t01-r1-c3`

- braille: `⠼⠓⠑`
- ref_zh: `85`
- pred: `85.1964年夏天,夏天,夏天,夏天,夏天,夏天,夏天,夏天,夏天,夏天`
- tone: none; exact=False; CER=17.5; CER_ns=17.5

### `t01-flat-header-row1`

- braille: `⠓⠊⠼ ⠍⠊⠼⠂ | ⠬ ⠒ | ⠱⠥ ⠓⠾ | ⠊⠼ ⠬⠄ || ⠌⠦ ⠎⠧⠁ | ⠼⠊⠃ | ⠼⠓⠓ | ⠼⠓⠑`
- ref_zh: `姓名 | 语文 | 数学 | 英语 || 张三 | 92 | 88 | 85`
- pred: `西1米/|语文|数学|92|88|85`
- tone: mixed; exact=False; CER=0.6316; CER_ns=0.4583

## Compare vs mT5 (same subset)

| metric | mT5-small (CPU) | Qwen3-8B 4bit (RTX 5060) |
|--------|-----------------|---------------------------|
| Host | CPU | Windows CUDA RTX 5060 8GB |
| Exact-match (8 cells) | 0.0% | 0.0% |
| Mean CER (cells) | 117.13 | **10.00** |
| Mean CER nospace | 70.38 | **10.00** |
| Flat partial CER | 1.55 | **0.63** |
| Best cell | 张三 CER=5.0 | 张三→`张三１。` CER=1.0 |
| Elapsed | 62.6s | 36.3s (GPU) |
| Peak VRAM | n/a | 5.75 GB / 7.96 GB |

**Takeaway:** Qwen3-8B 4-bit runs fine on this 8GB laptop and cuts cell CER by ~10× vs mT5 on the synthetic table subset, but **still 0% exact**. Short table cells remain OOD (hallucination/expansion: 数学→数论学长文; 数字后乱续). Flat row recovered some headers/numbers better. Next: in-domain HF 10per-Tone sentences, or table-cell fine-tune / constrained decoding.

