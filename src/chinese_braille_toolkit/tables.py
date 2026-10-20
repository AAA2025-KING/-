"""Flat braille table parse / restore helpers.

Flat format (same as ``data/synthetic_tables/tables.jsonl``):
  cell separator: `` | ``
  row separator: `` || ``

Also accepts common variants: bare ``|``, ``||`` without spaces, newlines
as row breaks, and whitespace-separated data rows when pipes are missing
(common after whole-table model decode).
"""

from __future__ import annotations

import csv
import html
import io
import re
from collections.abc import Callable, Sequence
from typing import Any

CELL_SEP = " | "
ROW_SEP = " || "

# Model / chat-template leaks sometimes appear inside cell generations.
_LEAK_RE = re.compile(
    r"</?\s*tool_?response\s*>|"
    r"</?\s*tool_?calls?\s*>|"
    r"</?\s*quote\b[^>]*>|"
    r"<quote\b[^>]*>?|"
    r"<\|/?[^|>]+\|>|"
    r"\[/?INST\]|"
    r"<<\s*/?\s*SYS\s*>>",
    re.IGNORECASE,
)

_WS_SPLIT_RE = re.compile(r"\s+")


def _strip_cell_edge_pipes(cell: str) -> str:
    """Remove leftover markdown border pipes stuck to a cell."""
    t = (cell or "").strip()
    if t.startswith("|"):
        t = t.lstrip("|").strip()
    if t.endswith("|"):
        t = t.rstrip("|").strip()
    return t


def _trim_markdown_pipe_borders(cells: list[str]) -> list[str]:
    """Drop empty leading/trailing cells from ``| a | b |`` / ``|a|b|`` pastes.

    Also strips a single edge ``|`` that CELL_SEP split left on the first/last
    cell (e.g. ``| 盲文 | 盲文 |`` → ``["| 盲文", "盲文 |"]``).
    """
    if not cells:
        return cells
    out = [_strip_cell_edge_pipes(c) for c in cells]
    while out and out[0] == "":
        out.pop(0)
    while out and out[-1] == "":
        out.pop()
    return out if out else [""]


def _is_markdown_separator_row(cells: Sequence[str]) -> bool:
    """True for GitHub-style ``| --- | --- |`` separator rows."""
    if not cells:
        return False
    for c in cells:
        s = str(c or "").strip().strip("|").strip()
        if not s:
            continue
        if not re.fullmatch(r":?-{3,}:?", s):
            return False
    return True



def sanitize_cell_text(text: str) -> str:
    """Strip leaked tool/chat markers from a cell translation.

    Also collapses multi-line / pipe-joined hallucinations that should never
    appear inside a single restored table cell.
    """
    t = (text or "").strip()
    if not t:
        return ""
    t = _LEAK_RE.sub("", t)
    if "\n" in t:
        t = t.split("\n", 1)[0].strip()
    if "|" in t:
        t = t.split("|", 1)[0].strip()
    # Collapse leftover double spaces from tag removal; keep intentional content.
    t = re.sub(r"[ \t]{2,}", " ", t)
    return t.strip(" |\t")


# Common school/schedule tokens for splitting jammed Chinese like "语文数学".
_CJK_TOKEN_LIST = [
    "信息技术",
    "及格率",
    "语文",
    "数学",
    "英语",
    "物理",
    "化学",
    "生物",
    "历史",
    "地理",
    "政治",
    "体育",
    "音乐",
    "美术",
    "品德",
    "科学",
    "综合",
    "科目",
    "姓名",
    "序号",
    "分数",
    "成绩",
    "平均",
    "最高",
    "最低",
    "周一",
    "周二",
    "周三",
    "周四",
    "周五",
    "周六",
    "周日",
    "星期",
    "节次",
    "时间",
    "课程",
    "教室",
    "商品",
    "数量",
    "单价",
    "金额",
    "区域",
    "总位",
    "占用",
    "空闲",
]
_CJK_TOKENS = tuple(sorted(_CJK_TOKEN_LIST, key=len, reverse=True))
_CJK_PURE_RE = re.compile(r"^[\u4e00-\u9fff\d]+$")
_DIGIT_CJK_RE = re.compile(r"^(\d+)([\u4e00-\u9fff].*)$")


def looks_like_jammed_zh(text: str) -> bool:
    """True for whitespace blobs, digit+CJK glue, or lexicon-splittable CJK compounds."""
    t = (text or "").strip()
    if not t or any("\u2800" <= ch <= "\u283f" for ch in t):
        return False
    if "|" in t:
        return False
    if _WS_SPLIT_RE.search(t):
        return True
    if _DIGIT_CJK_RE.match(t):
        return True
    if _CJK_PURE_RE.match(t) and len(t) >= 4:
        parts = split_jammed_cjk(t)
        return len(parts) > 1
    return False


def split_jammed_cjk(text: str, target_cols: int | None = None) -> list[str]:
    """Greedy-split jammed Chinese compounds: 语文数学 → [语文, 数学].

    Leaves braille / pipe / spaced text unchanged. Optional ``target_cols``
    merges overflow so we do not overspread past the table width.
    """
    s = (text or "").strip()
    if not s:
        return [""]
    if "|" in s or _WS_SPLIT_RE.search(s):
        return [s]
    if any("\u2800" <= ch <= "\u283f" for ch in s):
        return [s]
    if not _CJK_PURE_RE.match(s):
        return [s]

    parts: list[str] = []
    rest = s
    m = _DIGIT_CJK_RE.match(rest)
    if m:
        parts.append(m.group(1))
        rest = m.group(2)

    i = 0
    while i < len(rest):
        if target_cols and len(parts) >= target_cols:
            parts[-1] = parts[-1] + rest[i:]
            break
        matched = False
        for tok in _CJK_TOKENS:
            if rest.startswith(tok, i):
                parts.append(tok)
                i += len(tok)
                matched = True
                break
        if matched:
            continue
        # Fallback: 2-char CJK chunk when more content remains.
        if i + 2 <= len(rest) and all(
            "\u4e00" <= ch <= "\u9fff" for ch in rest[i : i + 2]
        ):
            parts.append(rest[i : i + 2])
            i += 2
            continue
        if parts:
            parts[-1] = parts[-1] + rest[i:]
        else:
            parts.append(rest[i:])
        break

    if target_cols and target_cols > 0 and len(parts) > target_cols:
        parts = parts[: target_cols - 1] + ["".join(parts[target_cols - 1 :])]
    if len(parts) <= 1:
        return [s]
    return parts


def _col_match_score(n: int, target: int | None) -> int:
    """Higher is better alignment to target column count."""
    if target is None or target <= 0:
        return n
    if n == target:
        return 10_000 + n
    if n < target:
        # Prefer more columns when under-width (closer to target).
        return 100 * n
    # Overshoot: still usable but penalize extras.
    return 100 * target - 10 * (n - target)


def _split_row_part(part: str, target_cols: int | None = None) -> list[str]:
    """Split one flat row into cells; optionally fall back to whitespace.

    Braille cells often contain internal spaces (e.g. ``⠓⠊⠼ ⠍⠊⠼⠂``), so
    whitespace splitting is used only when there are no pipes, or when the
    pipe split is short of ``target_cols``.
    """
    part = (part or "").strip()
    if not part:
        return [""]

    has_pipe = "|" in part
    if CELL_SEP in part:
        pipe_cells = [c.strip() for c in part.split(CELL_SEP)]
    elif has_pipe:
        pipe_cells = [c.strip() for c in part.split("|")]
    else:
        pipe_cells = [part]

    if has_pipe:
        pipe_cells = _trim_markdown_pipe_borders(pipe_cells)

    # Default: keep pipe (or single-blob) split — do not smash in-cell spaces.
    if has_pipe:
        if not target_cols or len(pipe_cells) >= target_cols:
            return pipe_cells
        # Under-width vs header: try whitespace on the whole part / single blob.
        candidates: list[list[str]] = [pipe_cells]
        if len(pipe_cells) == 1 and _WS_SPLIT_RE.search(pipe_cells[0]):
            ws_one = [c for c in _WS_SPLIT_RE.split(pipe_cells[0]) if c != ""]
            if ws_one:
                candidates.append(ws_one)
        return max(
            candidates,
            key=lambda cells: (
                _col_match_score(len(cells), target_cols),
                len(cells),
            ),
        )

    # No pipes: whitespace is the only separator (Chinese model data rows).
    if target_cols and _WS_SPLIT_RE.search(part):
        ws_cells = [c for c in _WS_SPLIT_RE.split(part) if c != ""]
        if _col_match_score(len(ws_cells), target_cols) > _col_match_score(
            len(pipe_cells), target_cols
        ):
            return ws_cells
    elif not target_cols and _WS_SPLIT_RE.search(part):
        # Still allow ws split when this is clearly multi-token Chinese/ASCII
        # (no braille dots). Braille rows without pipes stay as one cell.
        if not any("\u2800" <= ch <= "\u283f" for ch in part):
            ws_cells = [c for c in _WS_SPLIT_RE.split(part) if c != ""]
            if len(ws_cells) > 1:
                return ws_cells
    return pipe_cells


def normalize_grid(
    cells: Sequence[Sequence[str]],
    width: int | None = None,
) -> list[list[str]]:
    """Pad / truncate every row to ``width`` (default: first-row or max cols)."""
    if not cells:
        return []
    rows = [[sanitize_cell_text(str(c)) for c in row] for row in cells]
    if width is None or width <= 0:
        width = len(rows[0]) if rows[0] else max((len(r) for r in rows), default=0)
    if width <= 0:
        return rows
    out: list[list[str]] = []
    for row in rows:
        if len(row) < width:
            out.append(row + [""] * (width - len(row)))
        else:
            out.append(row[:width])
    return out


def expand_pipe_in_row(row: Sequence[str]) -> list[str]:
    """Split any cell whose text contains ``|`` into multiple cells."""
    raw = [sanitize_cell_text(str(c)) for c in (row or [])]
    nonempty = [(j, c) for j, c in enumerate(raw) if c]
    # One pipe-joined blob + empty pads (common after align-to-width).
    if len(nonempty) == 1 and "|" in nonempty[0][1]:
        blob = nonempty[0][1]
        parts = blob.split(CELL_SEP) if CELL_SEP in blob else blob.split("|")
        return [sanitize_cell_text(p) for p in parts]
    # One whitespace blob + empty pads — collapse to the blob for later ws split.
    if (
        len(nonempty) == 1
        and _WS_SPLIT_RE.search(nonempty[0][1] or "")
        and len(raw) > 1
        and all(not c for j, c in enumerate(raw) if j != nonempty[0][0])
    ):
        return [nonempty[0][1]]
    out: list[str] = []
    for cell in raw:
        if "|" in cell:
            parts = cell.split(CELL_SEP) if CELL_SEP in cell else cell.split("|")
            out.extend(sanitize_cell_text(p) for p in parts)
        else:
            out.append(cell)
    return out


def expand_pipe_cells(
    cells: Sequence[Sequence[str]],
    prefer_width: int | None = None,
) -> list[list[str]]:
    """Normalize pass: expand pipe-joined cells; pad rows to resulting width.

    Example::
        [["序号 | 科目 | 周一 | 周二 | 周三 | 周四 | 周五"], ["1 语文 数学"]]
        → 7-column header + whitespace-aligned data row.
    """
    if not cells:
        return []
    rows = [expand_pipe_in_row(row) for row in cells]
    width = prefer_width if prefer_width and prefer_width > 0 else 0
    width = max(width, max((len(r) for r in rows), default=0))
    if rows and len(rows[0]) > width:
        width = len(rows[0])
    fixed: list[list[str]] = []
    for i, row in enumerate(rows):
        if width and len(row) >= width:
            fixed.append(row[:width])
            continue
        if len(row) == 1 and _WS_SPLIT_RE.search(row[0] or ""):
            ws = _split_row_part(row[0], target_cols=width or None)
            if (not width) or _col_match_score(len(ws), width) > _col_match_score(
                len(row), width
            ):
                row = [sanitize_cell_text(c) for c in ws]
                if len(row) > width:
                    width = len(row)
        fixed.append(row)
    width = max(width, max((len(r) for r in fixed), default=0))
    return normalize_grid(fixed, width=width if width > 0 else None)


def repair_short_rows(
    cells: Sequence[Sequence[str]],
    target_width: int | None = None,
) -> list[list[str]]:
    """Split whitespace / jammed-CJK blobs when a row is under header width.

    Handles both ``1 语文 数学`` (spaces) and ``语文数学`` (no spaces) when
    neighboring cells are empty — e.g. 2-col schedule with 语文|数学 collapsed.
    """
    if not cells:
        return []
    width = target_width or (len(cells[0]) if cells else 0)
    if not width:
        return [list(r) for r in cells]
    out: list[list[str]] = []
    for i, row_in in enumerate(cells):
        row = [sanitize_cell_text(str(c)) for c in row_in]
        while len(row) < width:
            row.append("")
        nonempty = [(j, c) for j, c in enumerate(row) if str(c or "").strip()]
        blob_idx = None
        blob_text = ""
        if len(nonempty) == 1 and looks_like_jammed_zh(nonempty[0][1] or ""):
            blob_idx, blob_text = nonempty[0]
        elif len(row) == 1 and looks_like_jammed_zh(row[0] or ""):
            blob_idx, blob_text = 0, row[0]
        if blob_idx is not None:
            # Prefer whitespace / pipe split first; then jammed CJK lexicon.
            ws = _split_row_part(blob_text, target_cols=width)
            if len(ws) <= 1 or (
                len(ws) == 1 and looks_like_jammed_zh(ws[0] or "")
            ):
                cjk = split_jammed_cjk(blob_text, target_cols=width)
                if _col_match_score(len(cjk), width) > _col_match_score(len(ws), width):
                    ws = cjk
            if _col_match_score(len(ws), width) > _col_match_score(
                len(nonempty) or len(row), width
            ):
                new_row = row[:]
                while len(new_row) < width:
                    new_row.append("")
                # Clear the blob cell and following empties we will refill.
                for k in range(blob_idx, min(width, blob_idx + max(len(ws), 1))):
                    new_row[k] = ""
                for k, part in enumerate(ws):
                    pos = blob_idx + k
                    if pos >= width:
                        break
                    new_row[pos] = sanitize_cell_text(part)
                row = new_row
        else:
            # Partial jam across several nonempty cells: ["语文数学","",…] already
            # handled above; also expand digit+CJK inside individual cells.
            expanded: list[str] = []
            did = False
            for c in row:
                t = str(c or "").strip()
                if t and looks_like_jammed_zh(t) and not _WS_SPLIT_RE.search(t):
                    toks = split_jammed_cjk(t)
                    if len(toks) > 1:
                        expanded.extend(toks)
                        did = True
                        continue
                expanded.append(c)
            if did and _col_match_score(len(expanded), width) > _col_match_score(
                len(row), width
            ):
                row = expanded
        out.append(row)
    return normalize_grid(out, width=width)


def parse_flat(
    text: str,
    cell_sep: str = CELL_SEP,
    row_sep: str = ROW_SEP,
    *,
    target_cols: int | None = None,
) -> list[list[str]]:
    """Parse a flat table string into a 2-D grid of cell strings.

    Accepts canonical `` | `` / `` || ``, bare pipes, newline row breaks, and
    whitespace-separated data rows when pipe count is short of the header.
    """
    del cell_sep  # kept for API compat; splitter uses CELL_SEP / bare |
    raw = (text or "").strip()
    if not raw:
        return []
    raw = raw.replace("\r\n", "\n").replace("\r", "\n")

    # Normalize row separators into canonical row_sep.
    if row_sep not in raw:
        if "||" in raw:
            raw = row_sep.join(p.strip() for p in raw.split("||"))
        elif "\n" in raw:
            lines = [ln.strip() for ln in raw.split("\n")]
            lines = [ln for ln in lines if ln != ""]
            raw = row_sep.join(lines)

    rows: list[list[str]] = []
    for row_part in raw.split(row_sep):
        part = row_part.strip()
        # First row establishes target width when not provided.
        row_target = target_cols
        if row_target is None and rows:
            row_target = len(rows[0])
        cells = _split_row_part(part, target_cols=row_target)
        if len(cells) == 1 and cells[0] == "" and not rows:
            continue
        if _is_markdown_separator_row(cells):
            continue
        rows.append([sanitize_cell_text(c) for c in cells])

    if not rows:
        return []

    width = target_cols if target_cols and target_cols > 0 else len(rows[0])
    # Re-pass short data rows now that header width is known.
    if width > 1:
        fixed: list[list[str]] = [rows[0]]
        for row in rows[1:]:
            if len(row) >= width:
                fixed.append(row[:width])
                continue
            if len(row) == 1 and _WS_SPLIT_RE.search(row[0]):
                ws = _split_row_part(row[0], target_cols=width)
                if _col_match_score(len(ws), width) > _col_match_score(len(row), width):
                    fixed.append(ws)
                    continue
            fixed.append(row)
        rows = fixed

    return normalize_grid(rows, width=width if width > 0 else None)


def is_flat_table(text: str, cell_sep: str = CELL_SEP, row_sep: str = ROW_SEP) -> bool:
    """True when ``text`` looks like a flat table (row sep or multiple cell seps)."""
    s = text or ""
    if row_sep in s or "||" in s:
        return True
    if s.count(cell_sep) >= 2:
        return True
    pipe_count = s.count("|")
    if pipe_count >= 2:
        return True
    # Newline + at least one pipe often means a pasted 2-D table.
    if "\n" in s and pipe_count >= 1:
        return True
    return False


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


def _grid_score(cells: Sequence[Sequence[str]]) -> int:
    if not cells:
        return 0
    cols = max((len(r) for r in cells), default=0)
    # Prefer rectangular grids (all rows same width as header).
    header_w = len(cells[0]) if cells else 0
    rect_bonus = sum(1 for r in cells if len(r) == header_w) * 10
    return len(cells) * 100 + cols + rect_bonus


def translate_table(
    cells_or_flat: Sequence[Sequence[str]] | str,
    translate_fn: Callable[..., str],
    context: str | None = None,
    *,
    cell_sep: str = CELL_SEP,
    row_sep: str = ROW_SEP,
    batch_translate_fn: Callable[..., list[str]] | None = None,
    batch_size: int = 8,
) -> dict[str, Any]:
    """Translate a braille table **cell-by-cell**, then rebuild Chinese formats.

    Output grid shape matches the input braille grid (same rows / column count).
    """
    if isinstance(cells_or_flat, str):
        braille_cells = parse_flat(cells_or_flat, cell_sep=cell_sep, row_sep=row_sep)
    else:
        braille_cells = [list(row) for row in cells_or_flat]
        # Normalize ragged input rows to header width when possible.
        if braille_cells:
            braille_cells = normalize_grid(braille_cells, width=len(braille_cells[0]))

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

    input_width = max(len(r) for r in braille_cells)
    zh_cells: list[list[str]] = [["" for _ in row] for row in braille_cells]

    # Flatten non-empty cells for optional batched GPU decode (big speedup).
    jobs: list[tuple[int, int, str]] = []
    for r_idx, row in enumerate(braille_cells):
        for c_idx, cell_br in enumerate(row):
            br = (cell_br or "").strip()
            if br:
                jobs.append((r_idx, c_idx, br))

    if jobs and batch_translate_fn is not None:
        texts = [br for _, _, br in jobs]
        try:
            try:
                translated = batch_translate_fn(
                    texts, context=context, batch_size=batch_size
                )
            except TypeError:
                translated = batch_translate_fn(texts, context)  # type: ignore[misc,call-arg]
        except Exception:
            translated = None
        if translated is not None and len(translated) == len(jobs):
            for (r_idx, c_idx, _), zh in zip(jobs, translated):
                zh_cells[r_idx][c_idx] = sanitize_cell_text(zh or "")
            jobs = []  # done

    if jobs:
        # Sequential fallback (or remaining after failed batch).
        header_zh: list[str] = list(zh_cells[0]) if zh_cells else []
        for r_idx, c_idx, br in jobs:
            if zh_cells[r_idx][c_idx]:
                continue
            ctx_parts: list[str] = []
            if context:
                ctx_parts.append(context)
            if r_idx == 0:
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
                zh = translate_fn(br, cell_ctx)  # type: ignore[misc,call-arg]
            zh_cells[r_idx][c_idx] = sanitize_cell_text(zh or "")
            if r_idx == 0:
                header_zh = list(zh_cells[0])

    # When input already has a known grid shape (any multi-cell / multi-row
    # table, including payload.cells from the web UI), keep EXACT shape:
    # each output cell is only that cell's translation. Never expand pipes,
    # lexicon-split jammed CJK, or whitespace-resplit — those heuristics
    # break 2x2 / 4x4 / NxM structure.
    shape_known = any(len(r) > 1 for r in braille_cells) or len(braille_cells) > 1
    resplit_from_blob = False
    if shape_known:
        aligned: list[list[str]] = []
        for i, br_row in enumerate(braille_cells):
            zh_row = zh_cells[i] if i < len(zh_cells) else []
            aligned.append(
                [
                    sanitize_cell_text(zh_row[j] if j < len(zh_row) else "")
                    for j in range(len(br_row))
                ]
            )
        zh_cells = aligned
        braille_cells = [list(r) for r in braille_cells]
    else:
        # Only for true 1x1 blob input: if the model emitted a pipe table, re-split.
        if (
            len(zh_cells) == 1
            and len(zh_cells[0]) == 1
            and is_flat_table(zh_cells[0][0])
            and _grid_score(parse_flat(zh_cells[0][0])) > 101
        ):
            zh_cells = parse_flat(zh_cells[0][0])
            resplit_from_blob = True
            zh_cells = expand_pipe_cells(zh_cells)
            zh_cells = repair_short_rows(
                zh_cells, target_width=len(zh_cells[0]) if zh_cells else 0
            )
            braille_cells = normalize_grid(
                braille_cells, width=max(len(braille_cells[0]), 1)
            )
        else:
            zh_cells = normalize_grid(zh_cells, width=1)
            braille_cells = normalize_grid(braille_cells, width=1)

    flat_zh = cells_to_flat(zh_cells, cell_sep=cell_sep, row_sep=row_sep)
    return {
        "cells": zh_cells,
        "flat_zh": flat_zh,
        "markdown": cells_to_markdown(zh_cells),
        "csv": cells_to_csv(zh_cells),
        "html": cells_to_html(zh_cells),
        "braille_cells": braille_cells,
    }
