#!/usr/bin/env python3
"""Build error_corrections.jsonl from v3 holdout misses; merge into train_tables_with_errors.jsonl."""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SYSTEM = "你是一个中国盲文翻译助手，请把通用盲文转换成为汉字。"
USER_TMPL = "请把以下通用盲文转换成为汉字：\n盲文内容是:\n{braille}"
ASSIST_TMPL = "对应的中文内容是：\n{zh}"

preds = ROOT / "data" / "synthetic_tables" / "eval_qwen8b_adapter_v3_predictions.jsonl"
out_err = ROOT / "data" / "error_corrections.jsonl"
train_path = ROOT / "data" / "train_tables.jsonl"
merged_path = ROOT / "data" / "train_tables_with_errors.jsonl"

errs = []
for line in preds.open(encoding="utf-8"):
    if not line.strip():
        continue
    o = json.loads(line)
    if not o.get("exact_match"):
        errs.append(o)

corrections = []
for e in errs:
    braille = e["braille"]
    zh = e["ref_zh"]
    sid = e.get("sample_id") or f"{e['table_id']}-r{e.get('row')}-c{e.get('col')}"
    kind = e.get("kind") or "cell"
    corrections.append(
        {
            "id": f"errfix-{sid}",
            "kind": kind,
            "table_id": e.get("table_id"),
            "conversations": [
                {"from": "system", "value": SYSTEM},
                {"from": "human", "value": USER_TMPL.format(braille=braille)},
                {"from": "gpt", "value": ASSIST_TMPL.format(zh=zh)},
            ],
            "braille": braille,
            "zh": zh,
            "note": "v3 holdout correction; was pred=%r; cer=%s" % (e.get("pred"), e.get("cer")),
            "source_pred": e.get("pred"),
            "source_cer": e.get("cer"),
            "source_sample_id": sid,
        }
    )

out_err.write_text(
    "\n".join(json.dumps(c, ensure_ascii=False) for c in corrections) + "\n",
    encoding="utf-8",
)
n_cell = sum(1 for c in corrections if c["kind"] == "cell")
print(f"wrote {out_err} n={len(corrections)} cell={n_cell} other={len(corrections)-n_cell}")

train = [json.loads(l) for l in train_path.open(encoding="utf-8") if l.strip()]
seen = set()
merged = []
dupes = 0
for row in train + corrections:
    key = (row.get("braille") or "", row.get("zh") or "")
    if key in seen:
        dupes += 1
        continue
    seen.add(key)
    merged.append(row)

merged_path.write_text(
    "\n".join(json.dumps(r, ensure_ascii=False) for r in merged) + "\n",
    encoding="utf-8",
)
print(f"train={len(train)} corrections={len(corrections)} merged={len(merged)} dupes_skipped={dupes}")
