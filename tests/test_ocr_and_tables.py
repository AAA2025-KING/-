"""Tests for flat-table helpers and classical OCR on rendered sample."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from chinese_braille_toolkit import tables
from chinese_braille_toolkit.tables import (
    cells_to_csv,
    cells_to_flat,
    cells_to_html,
    cells_to_markdown,
    is_flat_table,
    parse_flat,
    translate_table,
)

ROOT = Path(__file__).resolve().parents[1]
SAMPLE = ROOT / "data" / "samples" / "t01_row_braille.png"
TABLES = ROOT / "data" / "synthetic_tables" / "tables.jsonl"


def _t01_flat() -> str:
    with TABLES.open(encoding="utf-8") as f:
        for line in f:
            obj = json.loads(line)
            if obj["id"] == "t01":
                return obj["flat_braille"]
    raise AssertionError("t01 missing")


def test_parse_flat_roundtrip():
    flat = _t01_flat()
    grid = parse_flat(flat)
    assert len(grid) == 4
    assert len(grid[0]) == 4
    assert grid[0][0] == "⠓⠊⠼ ⠍⠊⠼⠂"
    assert grid[1][1] == "⠼⠊⠃"
    back = cells_to_flat(grid)
    assert back == flat
    assert is_flat_table(flat)
    assert not is_flat_table("⠓⠊⠼ ⠍⠊⠼⠂")


def test_cells_formats():
    cells = [["姓名", "语文"], ["张三", "92"]]
    md = cells_to_markdown(cells)
    assert "| 姓名 | 语文 |" in md
    assert "---" in md
    csv = cells_to_csv(cells)
    assert "姓名" in csv and "92" in csv
    html = cells_to_html(cells)
    assert "<th>姓名</th>" in html
    assert "<td>张三</td>" in html


def test_translate_table_with_stub_fn():
    flat = "⠁ | ⠃ || ⠉ | ⠙"

    def fake(br: str, context: str | None = None) -> str:
        return f"ZH({br})"

    out = translate_table(flat, fake, context="成绩表")
    assert out["cells"] == [["ZH(⠁)", "ZH(⠃)"], ["ZH(⠉)", "ZH(⠙)"]]
    assert "ZH(⠁)" in out["flat_zh"]
    assert "<table" in out["html"]
    assert out["braille_cells"][0][0] == "⠁"


def test_ocr_sample_image():
    cv2 = pytest.importorskip("cv2")
    pytest.importorskip("numpy")
    pytest.importorskip("PIL")

    if not SAMPLE.is_file():
        # Generate on the fly
        import runpy

        runpy.run_path(str(ROOT / "scripts" / "render_braille_sample.py"), run_name="__main__")
    assert SAMPLE.is_file(), f"missing sample {SAMPLE}"

    from chinese_braille_toolkit.ocr import detect_braille_detailed

    detail = detect_braille_detailed(SAMPLE, mode="opencv")
    assert detail["method"] == "opencv_dots"
    braille = detail.get("braille") or ""
    rows = detail.get("rows") or []
    # Expect some braille chars detected
    assert any("\u2800" <= c <= "\u283f" for c in braille) or rows
    # First header token of t01 starts with ⠓ (U+2813)
    joined = braille + "".join("".join(r) for r in rows)
    # Soft check: at least a few dots formed non-blank cells
    non_blank = [c for c in joined if "\u2800" < c <= "\u283f"]
    assert len(non_blank) >= 3, f"too few cells: {detail}"


FILLED_HOLLOW = ROOT / "data" / "samples" / "user_upload_debug.png"


def test_ocr_filled_vs_hollow_glyphs():
    """Charts with hollow rings for unraised dots must keep a single cell-row."""
    pytest.importorskip("cv2")
    pytest.importorskip("numpy")
    pytest.importorskip("PIL")

    assert FILLED_HOLLOW.is_file(), f"missing sample {FILLED_HOLLOW}"

    from chinese_braille_toolkit.ocr import detect_braille_detailed

    detail = detect_braille_detailed(FILLED_HOLLOW, mode="opencv")
    assert detail["method"] == "opencv_dots"
    rows = detail.get("rows") or []
    braille = detail.get("braille") or ""
    # One logical braille line (not 3 fine-dot rows misread as cell rows)
    assert len(rows) == 1, f"expected 1 cell-row, got {len(rows)}: {detail}"
    assert len(rows[0]) >= 5, f"too few cells: {detail}"
    conf = detail.get("confidence")
    assert conf is not None and float(conf) >= 0.5, f"low confidence: {detail}"
    # Must not be dominated by ⠒ (dots 2+5) from treating every ring as a raised mid-dot
    joined = braille + "".join(rows[0])
    non_blank = [c for c in joined if "\u2800" < c <= "\u283f"]
    assert non_blank, f"no braille chars: {detail}"
    n_254 = sum(1 for c in non_blank if c == "\u2812")  # ⠒
    assert n_254 / len(non_blank) < 0.35, f"too many ⠒ ({n_254}/{len(non_blank)}): {detail}"
