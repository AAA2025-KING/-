#!/usr/bin/env python3
"""Merge user + holdout corrections into data/train_tables_with_errors.jsonl.

Usage:
  python scripts/merge_user_corrections.py
  python scripts/merge_user_corrections.py --prepare-retrain --max-steps 80
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from chinese_braille_toolkit import corrections as corr_mod  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="合并纠错样本到训练集")
    p.add_argument("--no-user", action="store_true", help="不合并 data/user_corrections.jsonl")
    p.add_argument("--no-holdout", action="store_true", help="不合并 data/error_corrections.jsonl")
    p.add_argument("--prepare-retrain", action="store_true", help="写出 outputs/retrain_request.json")
    p.add_argument("--max-steps", type=int, default=None, help="再训推荐步数")
    p.add_argument("--stats", action="store_true", help="只打印统计")
    args = p.parse_args(argv)

    if args.stats:
        print(json.dumps(corr_mod.correction_stats(), ensure_ascii=False, indent=2))
        return 0

    mr = corr_mod.merge_into_train(
        include_user=not args.no_user,
        include_holdout_errors=not args.no_holdout,
    )
    print(json.dumps(mr, ensure_ascii=False, indent=2))

    if args.prepare_retrain:
        prep = corr_mod.write_retrain_request(mr, max_steps=args.max_steps)
        print("--- retrain request ---")
        print(json.dumps(prep["commands"], ensure_ascii=False, indent=2))
        print(f"wrote {prep.get('request_path')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
