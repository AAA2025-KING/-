#!/usr/bin/env python3
"""Render a small synthetic braille-dot image for OCR smoke tests.

Draws the first row of table t01 (成绩表表头) as classical 6-dot cells,
plus a second data row (张三 | 92 | 88 | 85), under data/samples/.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "data" / "samples"
OUT_PATH = OUT_DIR / "t01_row_braille.png"

# Dot bit → (row, col) in 2×3 grid (row 0..2 top→bottom, col 0..1 left→right)
_BITS = [
    (0x01, 0, 0),
    (0x02, 1, 0),
    (0x04, 2, 0),
    (0x08, 0, 1),
    (0x10, 1, 1),
    (0x20, 2, 1),
]


def braille_char_to_bits(ch: str) -> int:
    o = ord(ch)
    if 0x2800 <= o <= 0x283F:
        return o - 0x2800
    return 0


def cell_tokens_from_flat_row(flat_row: str) -> list[str]:
    """Split a flat row on ' | '; each token may contain multiple braille chars + spaces."""
    return [t.strip() for t in flat_row.split(" | ")]


def expand_token_to_chars(token: str) -> list[str]:
    """Keep only braille chars (drop ASCII spaces between syllables)."""
    return [c for c in token if "\u2800" <= c <= "\u283f"]


def render(
    rows_tokens: list[list[str]],
    *,
    dot_r: int = 4,
    pitch: int = 14,
    cell_gap: int = 22,
    col_gap: int = 48,
    row_gap: int = 36,
    margin: int = 24,
    bg: tuple[int, int, int] = (255, 255, 255),
    fg: tuple[int, int, int] = (20, 20, 20),
) -> "Image.Image":
    from PIL import Image, ImageDraw

    # Precompute layout sizes
    cell_w = pitch + 2 * dot_r  # 2 cols
    cell_h = 2 * pitch + 2 * dot_r  # 3 rows

    row_widths = []
    for tokens in rows_tokens:
        n_cells = sum(len(expand_token_to_chars(t)) for t in tokens)
        n_tok = len(tokens)
        # width: cells + intra-token gaps + inter-token (column) gaps
        w = n_cells * cell_w + max(0, n_cells - n_tok) * cell_gap
        # actually simpler: for each token, chars with cell_gap, then col_gap between tokens
        w = 0
        for ti, tok in enumerate(tokens):
            chars = expand_token_to_chars(tok)
            w += len(chars) * cell_w + max(0, len(chars) - 1) * cell_gap
            if ti < len(tokens) - 1:
                w += col_gap
        row_widths.append(w)

    width = margin * 2 + (max(row_widths) if row_widths else cell_w)
    height = margin * 2 + len(rows_tokens) * cell_h + max(0, len(rows_tokens) - 1) * row_gap

    img = Image.new("RGB", (width, height), bg)
    draw = ImageDraw.Draw(img)

    y = margin
    for tokens in rows_tokens:
        x = margin
        for ti, tok in enumerate(tokens):
            chars = expand_token_to_chars(tok)
            for ci, ch in enumerate(chars):
                bits = braille_char_to_bits(ch)
                for mask, dr, dc in _BITS:
                    if bits & mask:
                        cx = x + dc * pitch + dot_r
                        cy = y + dr * pitch + dot_r
                        draw.ellipse(
                            (cx - dot_r, cy - dot_r, cx + dot_r, cy + dot_r),
                            fill=fg,
                        )
                x += cell_w
                if ci < len(chars) - 1:
                    x += cell_gap
            if ti < len(tokens) - 1:
                x += col_gap
        y += cell_h + row_gap

    return img


def main() -> int:
    tables_path = ROOT / "data" / "synthetic_tables" / "tables.jsonl"
    flat = None
    if tables_path.is_file():
        with tables_path.open(encoding="utf-8") as f:
            for line in f:
                obj = json.loads(line)
                if obj.get("id") == "t01":
                    flat = obj["flat_braille"]
                    break
    if not flat:
        flat = (
            "⠓⠊⠼ ⠍⠊⠼⠂ | ⠬ ⠒ | ⠱⠥ ⠓⠾ | ⠊⠼ ⠬⠄ || "
            "⠌⠦ ⠎⠧⠁ | ⠼⠊⠃ | ⠼⠓⠓ | ⠼⠓⠑"
        )

    parts = flat.split(" || ")
    rows = [cell_tokens_from_flat_row(p) for p in parts[:2]]  # header + first data

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    img = render(rows)
    img.save(OUT_PATH)
    print(f"wrote {OUT_PATH} ({img.size[0]}x{img.size[1]})")
    print("rows:", [" | ".join(r) for r in rows])
    return 0


if __name__ == "__main__":
    sys.exit(main())
