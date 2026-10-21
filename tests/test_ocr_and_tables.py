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
    assert ">姓名</th>" in html
    assert ">张三</td>" in html


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


def test_parse_flat_newlines_and_bare_pipes():
    grid = parse_flat("序号 | 科目 | 周一\n1 | 语文 | 92")
    assert len(grid) == 2
    assert grid[0] == ["序号", "科目", "周一"]
    assert grid[1] == ["1", "语文", "92"]
    bare = parse_flat("a|b|c||d|e|f")
    assert bare == [["a", "b", "c"], ["d", "e", "f"]]
    assert is_flat_table("序号 | 科目\n1 | 语文")


def test_sanitize_and_resplit_blob_cell():
    from chinese_braille_toolkit.tables import sanitize_cell_text

    dirty = "王 </tool_response> </tool_call> 五"
    assert "tool" not in sanitize_cell_text(dirty).lower()
    assert "王" in sanitize_cell_text(dirty)

    blob = "序号 | 科目 | 周一 || 1 | 语文 | 王 </tool_response> 五"

    def fake(br: str, context: str | None = None) -> str:
        # Simulate whole-table translate that returns a pipe table
        return blob if "|" not in br or len(br) > 10 else f"ZH({br})"

    # Single-cell input (mis-parsed blob) → translate_table should re-split
    out = translate_table("⠂⠂⠂⠂⠂⠂⠂⠂长串盲文无分隔符", fake)
    assert len(out["cells"]) == 2
    assert out["cells"][0][0] == "序号"
    assert "tool" not in out["cells"][1][2].lower()

def test_parse_flat_whitespace_data_row_matches_header():
    """After ||, space-separated tokens must align under header columns."""
    s = "序号 | 科目 | 周一 | 周二 | 周三 | 周四 | 周五 || 1 语文 数学"
    grid = parse_flat(s)
    assert len(grid) == 2
    assert len(grid[0]) == 7
    assert len(grid[1]) == 7
    assert grid[1][0] == "1"
    assert grid[1][1] == "语文"
    assert grid[1][2] == "数学"
    assert grid[1][3] == ""
    assert grid[1][6] == ""


def test_translate_table_keeps_input_shape_no_resplit():
    """Known input shape: output is exact same rows/cols; no blob re-split."""
    braille = [
        ["⠁", "⠃", "⠉", "⠙", "⠑", "⠋", "⠛"],
        ["⠁ ⠃ ⠉", "", "", "", "", "", ""],
    ]

    mapping = {
        "⠁": "序号",
        "⠃": "科目",
        "⠉": "周一",
        "⠙": "周二",
        "⠑": "周三",
        "⠋": "周四",
        "⠛": "周五",
        "⠁ ⠃ ⠉": "1 语文 数学",
    }

    def fake(br: str, context: str | None = None) -> str:
        return mapping.get(br, f"ZH({br})")

    out = translate_table(braille, fake)
    assert len(out["cells"]) == 2
    assert len(out["cells"][0]) == 7
    assert len(out["cells"][1]) == 7
    assert out["cells"][0] == ["序号", "科目", "周一", "周二", "周三", "周四", "周五"]
    # Do NOT spread "1 语文 数学" across other columns — stays in cell [1][0].
    assert out["cells"][1][0] == "1 语文 数学"
    assert out["cells"][1][1] == ""
    assert out["cells"][1][2] == ""



def test_expand_pipe_cells_splits_header_blob():
    """API-style 1-cell pipe header must expand to 7 columns."""
    from chinese_braille_toolkit.tables import expand_pipe_cells

    raw = [
        ["序号 | 科目 | 周一 | 周二 | 周三 | 周四 | 周五"],
        ["1语文 数学"],
    ]
    # Note: "1语文" may be glued; prefer spaced form too.
    g = expand_pipe_cells(raw)
    assert len(g[0]) == 7
    assert g[0] == ["序号", "科目", "周一", "周二", "周三", "周四", "周五"]
    assert len(g[1]) == 7

    raw2 = [
        ["序号 | 科目 | 周一 | 周二 | 周三 | 周四 | 周五", "", "", "", "", "", ""],
        ["1 语文 数学", "", "", "", "", "", ""],
    ]
    g2 = expand_pipe_cells(raw2)
    assert g2[0] == ["序号", "科目", "周一", "周二", "周三", "周四", "周五"]
    assert g2[1][0] == "1"
    assert g2[1][1] == "语文"
    assert g2[1][2] == "数学"
    assert g2[1][6] == ""


def test_translate_table_keeps_pipe_inside_cell_when_shape_known():
    """Multi-row 1-col input is a known shape — do not expand pipes to more cols."""
    braille = [["⠁"], ["⠃"]]

    def fake(br: str, context: str | None = None) -> str:
        if br == "⠁":
            return "序号 | 科目 | 周一 | 周二 | 周三 | 周四 | 周五"
        return "1 语文 数学"

    out = translate_table(braille, fake)
    assert len(out["cells"]) == 2
    assert len(out["cells"][0]) == 1
    assert len(out["cells"][1]) == 1
    assert out["cells"][0][0] == "序号 | 科目 | 周一 | 周二 | 周三 | 周四 | 周五"
    assert out["cells"][1][0] == "1 语文 数学"



def test_repair_jammed_cjk_subjects_two_col():
    """Helper may still lexicon-split; translate_table with known 2x2 must not."""
    from chinese_braille_toolkit.tables import repair_short_rows, split_jammed_cjk, translate_table

    assert split_jammed_cjk("语文数学") == ["语文", "数学"]
    g = repair_short_rows([["科目", "周一"], ["语文数学", ""]], target_width=2)
    assert g == [["科目", "周一"], ["语文", "数学"]]

    def fake(br: str, context: str | None = None) -> str:
        return {
            "⠁": "科目",
            "⠃": "周一",
            "⠉": "语文数学",  # model wrongly merges both subjects
            "⠙": "",
        }.get(br, "")

    out = translate_table([["⠁", "⠃"], ["⠉", "⠙"]], fake)
    # Known 2x2 shape: leave "语文数学" in its cell; do not steal col 2.
    assert out["cells"] == [["科目", "周一"], ["语文数学", ""]]
    assert out["flat_zh"] == "科目 | 周一 || 语文数学 | "


def test_normalize_grid_pad_truncate():
    from chinese_braille_toolkit.tables import normalize_grid

    g = normalize_grid([["a", "b", "c"], ["1", "2"]], width=3)
    assert g == [["a", "b", "c"], ["1", "2", ""]]
    g2 = normalize_grid([["a", "b", "c", "d"], ["1", "2", "3", "4"]], width=3)
    assert g2 == [["a", "b", "c"], ["1", "2", "3"]]

def test_translate_table_preserves_2x2_and_4x4_shape():
    """2x2 and 4x4 stay exact; no merge/split after translate."""
    def id_map(br: str, context: str | None = None) -> str:
        return f"ZH({br})"

    g2 = [["⠁", "⠃"], ["⠉", "⠙"]]
    out2 = translate_table(g2, id_map)
    assert [[len(r) for r in out2["cells"]]] == [[2, 2]] or (
        len(out2["cells"]) == 2 and all(len(r) == 2 for r in out2["cells"])
    )
    assert out2["cells"] == [["ZH(⠁)", "ZH(⠃)"], ["ZH(⠉)", "ZH(⠙)"]]

    g4 = [[f"{r}{c}" for c in range(4)] for r in range(4)]
    out4 = translate_table(g4, id_map)
    assert len(out4["cells"]) == 4
    assert all(len(r) == 4 for r in out4["cells"])
    assert out4["cells"][2][3] == "ZH(23)"


def test_parse_flat_markdown_border_pipes_t01():
    """Markdown ``| cell | cell |`` must not invent empty columns (was 4x6 bug)."""
    with TABLES.open(encoding="utf-8") as f:
        t01 = next(json.loads(line) for line in f if json.loads(line)["id"] == "t01")
    expected = [[c["braille"] for c in row] for row in t01["cells"]]
    # Spaced markdown borders (CELL_SEP present)
    md_spaced = "\n".join("| " + " | ".join(r) + " |" for r in expected)
    g1 = parse_flat(md_spaced)
    assert [len(r) for r in g1] == [4, 4, 4, 4], g1
    assert g1 == expected
    # Bare pipes (no spaces around |) — classic 6-col bug with empties
    md_bare = "\n".join("|" + "|".join(r) + "|" for r in expected)
    g2 = parse_flat(md_bare)
    assert [len(r) for r in g2] == [4, 4, 4, 4], g2
    assert g2 == expected
    # With separator row
    md_sep = (
        "| " + " | ".join(expected[0]) + " |\n"
        + "| --- | --- | --- | --- |\n"
        + "| " + " | ".join(expected[1]) + " |"
    )
    g3 = parse_flat(md_sep)
    assert len(g3) == 2
    assert g3[0] == expected[0]
    assert g3[1] == expected[1]
    # Canonical flat still exact
    assert parse_flat(t01["flat_braille"]) == expected





DIGITAL_TABLE = ROOT / "data" / "samples" / "t01_digital_table_screenshot.png"


def test_ocr_digital_table_screenshot():
    """Webpage Unicode braille table screenshot → exact t01 flat grid."""
    pytest.importorskip("cv2")
    pytest.importorskip("numpy")
    pytest.importorskip("PIL")

    assert DIGITAL_TABLE.is_file(), f"missing sample {DIGITAL_TABLE}"

    from chinese_braille_toolkit.ocr import detect_braille_detailed
    from chinese_braille_toolkit.tables import parse_flat

    detail = detect_braille_detailed(DIGITAL_TABLE, mode="auto")
    assert detail["method"] == "digital_table_unicode", detail
    braille = detail.get("braille") or ""
    grid = parse_flat(braille)
    assert len(grid) == 4 and len(grid[0]) == 4
    # Header cells of synthetic t01
    assert grid[0][0] == "⠓⠊⠼ ⠍⠊⠼⠂"
    assert grid[0][1] == "⠬ ⠒"
    assert grid[1][1] == "⠼⠊⠃"
    assert grid[2][0] == "⠇⠊ ⠎"


def _synthetic_hollow_dashed_braille():
    """White page with hollow + dashed raised dots (no filled disks)."""
    import cv2
    import numpy as np

    img = np.full((140, 280), 255, np.uint8)
    # Cell 1: ⠓ (dots 1,2,5) as hollow rings
    pos = [(50, 40), (50, 60), (50, 80), (70, 40), (70, 60), (70, 80)]
    for i in (0, 1, 4):
        cv2.circle(img, pos[i], 7, 0, 2)
    # Cell 2: ⠁ (dot 1) as dashed ring
    cx, cy, r = 140, 40, 7
    pts = [
        (int(cx + r * np.cos(np.deg2rad(a))), int(cy + r * np.sin(np.deg2rad(a))))
        for a in range(0, 360, 3)
    ]
    for i in range(0, len(pts) - 1, 6):
        cv2.line(img, pts[i], pts[min(i + 3, len(pts) - 1)], 0, 2)
    # Cell 3: ⠛ (dots 1,2,4,5) thin hollow rings
    pos3 = [(220, 40), (220, 60), (220, 80), (240, 40), (240, 60), (240, 80)]
    for i in (0, 1, 3, 4):
        cv2.circle(img, pos3[i], 6, 0, 1)
    return img


def test_ocr_hollow_and_dashed_solidify():
    """Hollow/dashed textbook rings become detectable after solidify preprocess."""
    pytest.importorskip("cv2")
    pytest.importorskip("numpy")
    pytest.importorskip("PIL")

    from chinese_braille_toolkit.ocr import (
        _detect_dots,
        _require_cv,
        detect_braille_detailed,
        solidify_hollow_rings,
    )

    cv2, np = _require_cv()
    img = _synthetic_hollow_dashed_braille()
    # Raw filled-dot detector should see little or nothing
    assert len(_detect_dots(img, cv2, np)) < 3

    solidified = solidify_hollow_rings(img, cv2, np)
    assert len(_detect_dots(solidified, cv2, np)) >= 6

    detail = detect_braille_detailed(img, mode="solidify")
    assert detail.get("solidified") is True
    assert detail["method"] == "opencv_dots_solidified"
    braille = detail.get("braille") or ""
    rows = detail.get("rows") or []
    joined = braille + "".join("".join(r) for r in rows)
    # Expect ⠓, ⠁, ⠛ among detected cells
    for ch in ("⠓", "⠁", "⠛"):
        assert ch in joined, f"missing {ch!r} in {detail}"

    # Auto path should also solidify (few solid dots)
    auto = detect_braille_detailed(img, mode="auto")
    assert auto.get("solidified") is True
    assert auto["method"] == "opencv_dots_solidified"


def test_ocr_mixed_filled_hollow_does_not_auto_solidify():
    """Filled=raised / hollow=unraised charts must keep opencv_dots (no invent)."""
    pytest.importorskip("cv2")
    pytest.importorskip("numpy")
    pytest.importorskip("PIL")
    assert FILLED_HOLLOW.is_file(), f"missing sample {FILLED_HOLLOW}"

    from chinese_braille_toolkit.ocr import detect_braille_detailed

    detail = detect_braille_detailed(FILLED_HOLLOW, mode="opencv")
    assert detail["method"] == "opencv_dots"
    assert detail.get("solidified") is False
    rows = detail.get("rows") or []
    assert len(rows) == 1

