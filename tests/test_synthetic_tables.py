"""Validate synthetic Braille table evaluation data."""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TABLES_PATH = ROOT / "data" / "synthetic_tables" / "tables.jsonl"


def _load_tables() -> list[dict]:
    assert TABLES_PATH.is_file(), f"missing {TABLES_PATH}; run scripts/build_synthetic_tables.py"
    tables = []
    for line_no, line in enumerate(TABLES_PATH.read_text(encoding="utf-8").splitlines(), 1):
        line = line.strip()
        if not line:
            continue
        obj = json.loads(line)
        assert isinstance(obj, dict), f"line {line_no} not an object"
        tables.append(obj)
    return tables


def test_at_least_five_tables():
    tables = _load_tables()
    assert len(tables) >= 5


def test_table_schema_and_nonempty():
    required = {
        "id",
        "title_zh",
        "format",
        "cells",
        "flat_zh",
        "flat_braille",
        "notes",
    }
    tables = _load_tables()
    ids = set()
    for t in tables:
        missing = required - set(t)
        assert not missing, f"{t.get('id')}: missing {missing}"
        assert t["id"] not in ids
        ids.add(t["id"])
        assert t["title_zh"].strip()
        assert t["format"]
        assert t["flat_zh"].strip()
        assert t["flat_braille"].strip()
        assert " | " in t["flat_braille"] or "||" in t["flat_braille"]
        assert isinstance(t["cells"], list) and len(t["cells"]) >= 2
        for row in t["cells"]:
            assert isinstance(row, list) and row
            for cell in row:
                assert set(cell.keys()) >= {"zh", "braille", "tone"}
                assert cell["zh"] != ""
                assert cell["braille"].strip() != ""
                assert cell["tone"] in {"none", "partial", "full"}


def test_cell_count_reasonable():
    tables = _load_tables()
    n_cells = sum(len(row) for t in tables for row in t["cells"])
    assert n_cells >= 20
