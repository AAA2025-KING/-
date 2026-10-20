"""Flat braille table parse / restore helpers.

Flat format (same as ``data/synthetic_tables/tables.jsonl``):
  cell separator: `` | ``
  row separator: `` || ``
"""

from __future__ import annotations

import csv
import html
import io
from collections.abc import Callable, Sequence
from typing import Any

CELL_SEP = " | "
ROW_SEP = " || "


def parse_flat(
    text: str,
    cell_sep: str = CELL_SEP,
    row_sep: str = ROW_SEP,
) -> list[list[str]]:
    """Parse a flat table string into a 2-D grid of cell strings."""
    raw = (text or "").strip()
    if not raw:
        return []
    rows: list[list[str]] = []
    for row_part in raw.split(row_sep):
        cells = [c.strip() for c in row_part.split(cell_sep)]
        # Keep empty trailing cells only if intentional; strip empty last if whole empty
        if len(cells) == 1 and cells[0] == "" and not rows:
            continue
        rows.append(cells)
    return rows


def is_flat_table(text: str, cell_sep: str = CELL_SEP, row_sep: str = ROW_SEP) -> bool:
    """True when ``text`` looks like a flat table (row sep or multiple cell seps)."""
    s = text or ""
    if row_sep in s:
        return True
    # At least two cell separators ⇒ ≥3 cells on one line (table-like).
    return s.count(cell_sep) >= 2


def cells_to_flat(
    cells: Sequence[Sequence[str]],
    cell_sep: str = CELL_SEP,
    row_sep: str = ROW_SEP,
) -> str:
    """Serialize a 2-D grid back to flat format."""
    return row_sep.join(cell_sep.join(str(c) for c in row) for row in cells)


def cells_to_markdown(cells: Sequence[Sequence[str]]) -> str:
    """Render a markdown pipe table (first row as header)."""
    if not cells:
        return ""
    width = max(len(r) for r in cells)
    norm = [list(r) + [""] * (width - len(r)) for r in cells]
    header = norm[0]
    lines = [
        "| " + " | ".join(header) + " |",
        "| " + " | ".join("---" for _ in header) + " |",
    ]
    for row in norm[1:]:
        lines.append("| " + " | ".join(row) + " |")
    return "\n".join(lines)


def cells_to_csv(cells: Sequence[Sequence[str]]) -> str:
    """Render CSV (RFC-ish via csv module)."""
    buf = io.StringIO()
    writer = csv.writer(buf)
    for row in cells:
        writer.writerow([str(c) for c in row])
    return buf.getvalue()


def cells_to_html(cells: Sequence[Sequence[str]], *, caption: str | None = None) -> str:
    """Render a simple HTML table (first row as ``<th>``).

    Each cell gets ``data-r`` / ``data-c`` (0-based), ``tabindex="0"``, and
    class ``cbt-cell`` so the web UI can locate and announce cells.
    """
    if not cells:
        return '<table class="cbt-table"></table>'
    parts: list[str] = ['<table class="cbt-table">']
    if caption:
        parts.append(f"<caption>{html.escape(caption)}</caption>")
    for i, row in enumerate(cells):
        tag = "th" if i == 0 else "td"
        cells_html = "".join(
            f'<{tag} class="cbt-cell" data-r="{i}" data-c="{j}" tabindex="0">'
            f"{html.escape(str(c))}</{tag}>"
            for j, c in enumerate(row)
        )
        parts.append(f"<tr>{cells_html}</tr>")
    parts.append("</table>")
    return "\n".join(parts)


def translate_table(
    cells_or_flat: Sequence[Sequence[str]] | str,
    translate_fn: Callable[..., str],
    context: str | None = None,
    *,
    cell_sep: str = CELL_SEP,
    row_sep: str = ROW_SEP,
) -> dict[str, Any]:
    """Translate a braille table **cell-by-cell**, then rebuild Chinese formats.

    Parameters
    ----------
    cells_or_flat:
        Either a 2-D list of braille cell strings, or a flat braille string.
    translate_fn:
        ``(braille, context=...) -> zh`` callable (e.g. ``api.translate``).
    context:
        Optional global context prepended / used for the header row.
    """
    if isinstance(cells_or_flat, str):
        braille_cells = parse_flat(cells_or_flat, cell_sep=cell_sep, row_sep=row_sep)
    else:
        braille_cells = [list(row) for row in cells_or_flat]

    if not braille_cells:
        empty: list[list[str]] = []
        return {
            "cells": empty,
            "flat_zh": "",
            "markdown": "",
            "csv": "",
            "html": cells_to_html(empty),
            "braille_cells": empty,
        }

    zh_cells: list[list[str]] = []
    header_zh: list[str] = []

    for r_idx, row in enumerate(braille_cells):
        zh_row: list[str] = []
        for c_idx, cell_br in enumerate(row):
            br = (cell_br or "").strip()
            if not br:
                zh_row.append("")
                continue
            # Context: global + column header (after header row translated).
            ctx_parts: list[str] = []
            if context:
                ctx_parts.append(context)
            if r_idx == 0:
                # Header row: use global context / "表头"
                if not context:
                    ctx_parts.append("表头")
            else:
                if c_idx < len(header_zh) and header_zh[c_idx]:
                    ctx_parts.append(header_zh[c_idx])
                elif c_idx < len(braille_cells[0]) and braille_cells[0][c_idx]:
                    ctx_parts.append(f"列:{braille_cells[0][c_idx]}")
            cell_ctx = " / ".join(ctx_parts) if ctx_parts else None
            try:
                zh = translate_fn(br, context=cell_ctx)
            except TypeError:
                # Some backends only accept positional context.
                zh = translate_fn(br, cell_ctx)  # type: ignore[misc,call-arg]
            zh_row.append((zh or "").strip())
        if r_idx == 0:
            header_zh = list(zh_row)
        zh_cells.append(zh_row)

    flat_zh = cells_to_flat(zh_cells, cell_sep=cell_sep, row_sep=row_sep)
    return {
        "cells": zh_cells,
        "flat_zh": flat_zh,
        "markdown": cells_to_markdown(zh_cells),
        "csv": cells_to_csv(zh_cells),
        "html": cells_to_html(zh_cells),
        "braille_cells": braille_cells,
    }
