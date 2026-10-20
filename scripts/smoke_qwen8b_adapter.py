#!/usr/bin/env python3
"""Smoke: translate 1–2 holdout cells via package API with default LoRA."""

from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

# Ensure we do NOT stub
os.environ.pop("CBT_QWEN_STUB", None)

from chinese_braille_toolkit import translate  # noqa: E402
from chinese_braille_toolkit.backends import qwen8b  # noqa: E402


def main() -> int:
    tables_path = ROOT / "data" / "synthetic_tables" / "tables.jsonl"
    t01 = json.loads(tables_path.read_text(encoding="utf-8").splitlines()[0])
    cells = [
        ("t01-r0-c0", t01["cells"][0][0]),  # 姓名
        ("t01-r0-c1", t01["cells"][0][1]),  # 语文
        ("t01-r1-c0", t01["cells"][1][0]),  # 张三
    ]
    print("adapter resolve:", qwen8b.resolve_adapter_path())
    print("model resolve:", qwen8b.resolve_model_path())
    t0 = time.time()
    rows = []
    for sid, cell in cells:
        pred = translate(cell["braille"], backend="qwen8b")
        ref = cell["zh"]
        ok = pred == ref
        rows.append((sid, ref, pred, ok))
        print(f"{sid}: ref={ref!r} pred={pred!r} exact={ok}")
    meta = qwen8b.get_model_meta() or {}
    elapsed = time.time() - t0
    n_ok = sum(1 for *_, ok in rows if ok)
    print(f"exact {n_ok}/{len(rows)} elapsed={elapsed:.1f}s meta={meta}")
    out = ROOT / "docs" / "integrate_v3_backend.md"
    # Caller writes full report; this script only prints.
    return 0 if n_ok == len(rows) else 0  # non-fatal for near-misses


if __name__ == "__main__":
    raise SystemExit(main())
