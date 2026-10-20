#!/usr/bin/env python3
"""Run real mT5 translation on a small synthetic-table subset (t01 cells).

Model: Violet-yo/mt5-small-ft-Chinese-Braille
Per model card: use_fast=False, max_length=280, num_beams=5, max_new_tokens=300.

Writes: data/synthetic_tables/eval_mt5_report.md
         data/synthetic_tables/eval_mt5_predictions.jsonl
"""

from __future__ import annotations

import json
import sys
import time
import traceback
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "synthetic_tables"
JSONL = DATA / "tables.jsonl"
REPORT = DATA / "eval_mt5_report.md"
PREDS = DATA / "eval_mt5_predictions.jsonl"
MODEL_ID = "Violet-yo/mt5-small-ft-Chinese-Braille"


def load_tables() -> list[dict]:
    tables = []
    for line in JSONL.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            tables.append(json.loads(line))
    return tables


def build_samples(tables: list[dict]) -> list[dict]:
    """t01 header row + first data row as individual cells; plus one flat row."""
    t01 = next(t for t in tables if t["id"] == "t01")
    samples: list[dict] = []
    # Header row (row 0)
    for col, cell in enumerate(t01["cells"][0]):
        samples.append(
            {
                "sample_id": f"t01-r0-c{col}",
                "table_id": "t01",
                "kind": "cell",
                "row": 0,
                "col": col,
                "braille": cell["braille"],
                "ref_zh": cell["zh"],
                "tone": cell["tone"],
            }
        )
    # First data row (row 1) — 张三 | 92 | 88 | 85
    for col, cell in enumerate(t01["cells"][1]):
        samples.append(
            {
                "sample_id": f"t01-r1-c{col}",
                "table_id": "t01",
                "kind": "cell",
                "row": 1,
                "col": col,
                "braille": cell["braille"],
                "ref_zh": cell["zh"],
                "tone": cell["tone"],
            }
        )
    # Optional: one flat header+first-data row (shorter than full flat)
    header_br = " | ".join(c["braille"] for c in t01["cells"][0])
    header_zh = " | ".join(c["zh"] for c in t01["cells"][0])
    row1_br = " | ".join(c["braille"] for c in t01["cells"][1])
    row1_zh = " | ".join(c["zh"] for c in t01["cells"][1])
    flat_partial_br = header_br + " || " + row1_br
    flat_partial_zh = header_zh + " || " + row1_zh
    samples.append(
        {
            "sample_id": "t01-flat-header-row1",
            "table_id": "t01",
            "kind": "flat_partial",
            "row": None,
            "col": None,
            "braille": flat_partial_br,
            "ref_zh": flat_partial_zh,
            "tone": "mixed",
        }
    )
    return samples


def cer(ref: str, hyp: str) -> float | None:
    if not ref:
        return None
    # Normalize: strip spaces for Chinese CER option also computed separately
    n, m = len(ref), len(hyp)
    dp = list(range(m + 1))
    for i in range(1, n + 1):
        prev, dp = dp, [i] + [0] * m
        for j in range(1, m + 1):
            cost = 0 if ref[i - 1] == hyp[j - 1] else 1
            dp[j] = min(dp[j - 1] + 1, prev[j] + 1, prev[j - 1] + cost)
    return dp[m] / n


def normalize_zh(s: str) -> str:
    """Remove whitespace for space-insensitive CER."""
    return "".join(s.split())


def main() -> int:
    if not JSONL.is_file():
        print(f"Missing {JSONL}", file=sys.stderr)
        return 1

    tables = load_tables()
    samples = build_samples(tables)
    print(f"Samples to translate: {len(samples)}")

    t0 = time.time()
    try:
        import torch
        from transformers import AutoModelForSeq2SeqLM, AutoTokenizer
    except Exception as exc:
        msg = f"Import failed: {type(exc).__name__}: {exc}"
        REPORT.write_text(
            f"# mT5 eval report\n\n**Failed:** {msg}\n",
            encoding="utf-8",
        )
        print(msg, file=sys.stderr)
        return 2

    try:
        print(f"Loading tokenizer/model: {MODEL_ID}")
        tokenizer = AutoTokenizer.from_pretrained(MODEL_ID, use_fast=False)
        model = AutoModelForSeq2SeqLM.from_pretrained(MODEL_ID)
        model.eval()
        device = torch.device("cpu")
        model.to(device)
        print(f"Model loaded on {device} in {time.time() - t0:.1f}s")
    except Exception as exc:
        tb = traceback.format_exc(limit=8)
        REPORT.write_text(
            "# mT5 eval report\n\n"
            f"**Failed to load model:** {type(exc).__name__}: {exc}\n\n"
            f"```\n{tb}\n```\n",
            encoding="utf-8",
        )
        print(f"Load failed: {exc}", file=sys.stderr)
        return 3

    results: list[dict] = []
    try:
        for s in samples:
            braille = s["braille"]
            inputs = tokenizer(
                braille,
                return_tensors="pt",
                max_length=280,
                padding=True,
                truncation=True,
            )
            inputs = {k: v.to(device) for k, v in inputs.items()}
            with torch.no_grad():
                out = model.generate(
                    input_ids=inputs["input_ids"],
                    attention_mask=inputs["attention_mask"],
                    max_new_tokens=300,
                    num_beams=5,
                )
            pred = tokenizer.decode(out[0], skip_special_tokens=True)
            ref = s["ref_zh"]
            c_raw = cer(ref, pred)
            c_ns = cer(normalize_zh(ref), normalize_zh(pred))
            exact = pred == ref
            exact_ns = normalize_zh(pred) == normalize_zh(ref)
            row = {
                **s,
                "pred": pred,
                "exact_match": exact,
                "exact_match_nospace": exact_ns,
                "cer": None if c_raw is None else round(c_raw, 4),
                "cer_nospace": None if c_ns is None else round(c_ns, 4),
            }
            results.append(row)
            print(
                f"  {s['sample_id']}: ref={ref!r} pred={pred!r} "
                f"CER={row['cer']} CER_ns={row['cer_nospace']}"
            )
    except Exception as exc:
        tb = traceback.format_exc(limit=8)
        # Keep any partial results
        if results:
            PREDS.write_text(
                "\n".join(json.dumps(r, ensure_ascii=False) for r in results) + "\n",
                encoding="utf-8",
            )
        REPORT.write_text(
            "# mT5 eval report\n\n"
            f"**Failed mid-inference after {len(results)} samples:** "
            f"{type(exc).__name__}: {exc}\n\n"
            f"```\n{tb}\n```\n",
            encoding="utf-8",
        )
        print(f"Infer failed: {exc}", file=sys.stderr)
        return 4

    elapsed = round(time.time() - t0, 1)
    PREDS.write_text(
        "\n".join(json.dumps(r, ensure_ascii=False) for r in results) + "\n",
        encoding="utf-8",
    )

    cell_results = [r for r in results if r["kind"] == "cell"]
    n = len(cell_results)
    exact_rate = sum(1 for r in cell_results if r["exact_match"]) / n if n else 0.0
    exact_ns_rate = (
        sum(1 for r in cell_results if r["exact_match_nospace"]) / n if n else 0.0
    )
    mean_cer = (
        sum(r["cer"] for r in cell_results if r["cer"] is not None) / n if n else None
    )
    mean_cer_ns = (
        sum(r["cer_nospace"] for r in cell_results if r["cer_nospace"] is not None) / n
        if n
        else None
    )

    lines = [
        "# mT5 real translation eval (synthetic tables)",
        "",
        f"- Model: `{MODEL_ID}`",
        f"- Device: CPU (torch)",
        f"- Tokenizer: `use_fast=False` (model card)",
        f"- Generate: `max_length=280` encode, `max_new_tokens=300`, `num_beams=5`",
        f"- Elapsed: **{elapsed}s** (load + {len(results)} inferences)",
        f"- Subset: t01 header row + first data row (8 cells) + 1 partial flat row",
        f"- Predictions JSONL: `{PREDS.relative_to(ROOT)}`",
        "",
        "## Aggregate (cells only)",
        "",
        f"- N cells: **{n}**",
        f"- Exact-match rate: **{exact_rate:.1%}**",
        f"- Exact-match (ignore spaces): **{exact_ns_rate:.1%}**",
        f"- Mean CER (raw): **{mean_cer:.4f}**" if mean_cer is not None else "- Mean CER: n/a",
        f"- Mean CER (no spaces): **{mean_cer_ns:.4f}**"
        if mean_cer_ns is not None
        else "- Mean CER (no spaces): n/a",
        "",
        "## Per-sample",
        "",
        "| id | kind | braille | ref_zh | pred | exact | CER | CER_ns |",
        "|----|------|---------|--------|------|-------|-----|--------|",
    ]
    for r in results:
        br = r["braille"].replace("|", "\\|")
        if len(br) > 48:
            br = br[:45] + "…"
        pred = str(r["pred"]).replace("|", "\\|")
        if len(pred) > 40:
            pred = pred[:37] + "…"
        ref = str(r["ref_zh"]).replace("|", "\\|")
        lines.append(
            f"| `{r['sample_id']}` | {r['kind']} | `{br}` | {ref} | {pred} | "
            f"{r['exact_match']} | {r['cer']} | {r['cer_nospace']} |"
        )

    lines += [
        "",
        "## Notes",
        "",
        "- Synthetic Braille from pypinyin `Style.BRAILLE_MAINLAND` (~10% tone); may differ from the model's 10per-Tone training distribution.",
        "- Short table cells (2–4 chars / numbers) are out-of-domain vs news sentences the model was fine-tuned on; low exact-match is expected.",
        "- Separators `|` / `||` in the partial flat row are not Braille tokens the model saw in training.",
        "- Full 8-table flat eval skipped intentionally to control time/disk.",
        "- Chart OCR is out of scope; this only scores translation step 2.",
        "",
        "## Inputs / outputs detail",
        "",
    ]
    for r in results:
        lines += [
            f"### `{r['sample_id']}`",
            "",
            f"- braille: `{r['braille']}`",
            f"- ref_zh: `{r['ref_zh']}`",
            f"- pred: `{r['pred']}`",
            f"- tone: {r['tone']}; exact={r['exact_match']}; "
            f"CER={r['cer']}; CER_ns={r['cer_nospace']}",
            "",
        ]

    REPORT.write_text("\n".join(lines), encoding="utf-8")
    print(f"Wrote {REPORT}")
    print(f"Wrote {PREDS}")
    print(
        f"DONE exact={exact_rate:.1%} exact_ns={exact_ns_rate:.1%} "
        f"mean_cer={mean_cer} mean_cer_ns={mean_cer_ns} elapsed={elapsed}s"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
