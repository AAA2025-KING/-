"""Braille chart / image detection (classical OpenCV + Unicode-text fallback)."""

from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Any

PathLike = str | Path

# U+2800–U+283F
_BRAILLE_RE = re.compile(r"[\u2800-\u283f]+(?:\s+[\u2800-\u283f]+)*")

# Dot bit masks (standard 6-dot):
#  1 4
#  2 5
#  3 6
_DOT_BITS = {
    (0, 0): 0x01,  # 1
    (1, 0): 0x02,  # 2
    (2, 0): 0x04,  # 3
    (0, 1): 0x08,  # 4
    (1, 1): 0x10,  # 5
    (2, 1): 0x20,  # 6
}


def _stub_enabled() -> bool:
    return (os.environ.get("CBT_OCR_STUB") or "").strip().lower() in {
        "1",
        "true",
        "yes",
        "on",
    }


def _require_cv() -> tuple[Any, Any]:
    try:
        import cv2  # type: ignore
        import numpy as np  # type: ignore
    except ImportError as exc:  # pragma: no cover
        raise ImportError(
            "OCR 需要 opencv-python-headless、numpy、Pillow。"
            ' 请执行: pip install "opencv-python-headless>=4.8" numpy Pillow'
            "  （或 pip install -e \".[ocr]\"）。"
            " 若仅想跑脚手架，设置环境变量 CBT_OCR_STUB=1。"
        ) from exc
    return cv2, np


def _load_gray(image: PathLike | Any, cv2: Any, np: Any) -> Any:
    """Load grayscale ndarray from path, bytes, PIL Image, or ndarray."""
    if hasattr(image, "shape"):
        arr = np.asarray(image)
        if arr.ndim == 3:
            return cv2.cvtColor(arr, cv2.COLOR_BGR2GRAY) if arr.shape[2] >= 3 else arr[:, :, 0]
        return arr
    if hasattr(image, "convert"):  # PIL
        from PIL import Image
        import io

        pil = image.convert("L") if not isinstance(image, Image.Image) else image.convert("L")
        return np.array(pil)
    path = Path(image)
    if not path.is_file():
        raise FileNotFoundError(f"image not found: {path}")
    data = np.fromfile(str(path), dtype=np.uint8)
    bgr = cv2.imdecode(data, cv2.IMREAD_COLOR)
    if bgr is None:
        # Fallback via Pillow (handles some formats OpenCV misses)
        from PIL import Image

        return np.array(Image.open(path).convert("L"))
    return cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)


def _detect_dots(gray: Any, cv2: Any, np: Any) -> list[tuple[float, float, float]]:
    """Return list of (x, y, radius) for **filled** dark braille dots.

    Charts that draw unraised positions as hollow rings (outlined circles) are
    common in Chinese braille teaching materials. Those rings must not count as
    raised dots: we keep only blobs with a high fill ratio and a dark interior.
    Solid-only renders (e.g. ``t01_row_braille.png``) still pass unchanged.
    """
    # Invert if background is dark (dots bright) so work is always light-bg / dark-ink
    mean = float(np.mean(gray))
    work = gray.copy()
    if mean < 127:
        work = 255 - work

    blurred = cv2.GaussianBlur(work, (5, 5), 0)
    binary = cv2.adaptiveThreshold(
        blurred,
        255,
        cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY_INV,
        21,
        8,
    )
    # Clean small noise
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
    binary = cv2.morphologyEx(binary, cv2.MORPH_OPEN, kernel, iterations=1)
    # Light erode: thin ring outlines shrink away; filled disks remain as blobs
    erode_k = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (2, 2))
    binary = cv2.erode(binary, erode_k, iterations=1)

    contours, _ = cv2.findContours(binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    h, w = gray.shape[:2]
    area_img = float(h * w)
    dots: list[tuple[float, float, float]] = []
    for cnt in contours:
        area = cv2.contourArea(cnt)
        if area < 4 or area > area_img * 0.02:
            continue
        (cx, cy), radius = cv2.minEnclosingCircle(cnt)
        if radius < 1.0 or radius > min(h, w) * 0.08:
            continue
        # Prefer roughly circular blobs
        peri = cv2.arcLength(cnt, True)
        if peri <= 0:
            continue
        circularity = 4.0 * np.pi * area / (peri * peri)
        if circularity < 0.35:
            continue
        # Reject hollow rings: contour must fill most of its enclosing circle
        circle_area = float(np.pi * radius * radius)
        fill_ratio = float(area / circle_area) if circle_area > 0 else 0.0
        if fill_ratio < 0.45:
            continue
        # Interior of filled disks is dark on ``work``; ring interiors are bright
        r_in = max(1, int(round(radius * 0.4)))
        x0, y0 = int(round(cx)), int(round(cy))
        y1, y2 = max(0, y0 - r_in), min(h, y0 + r_in + 1)
        x1, x2 = max(0, x0 - r_in), min(w, x0 + r_in + 1)
        patch = work[y1:y2, x1:x2]
        if patch.size == 0:
            continue
        if float(np.mean(patch)) > 90.0:
            continue
        dots.append((float(cx), float(cy), float(radius)))
    return dots



def _normalize_ink_gray(gray: Any, np: Any) -> tuple[Any, bool]:
    """Return (light-bg/dark-ink gray, was_inverted)."""
    mean = float(np.mean(gray))
    if mean < 127:
        return 255 - gray, True
    return gray.copy(), False


def _ink_binary(
    work: Any,
    cv2: Any,
    *,
    close_dashes: bool = False,
) -> Any:
    """Adaptive threshold to white-ink / black-bg binary; optional dash closing."""
    blurred = cv2.GaussianBlur(work, (5, 5), 0)
    binary = cv2.adaptiveThreshold(
        blurred,
        255,
        cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY_INV,
        21,
        8,
    )
    open_k = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
    binary = cv2.morphologyEx(binary, cv2.MORPH_OPEN, open_k, iterations=1)
    if close_dashes:
        # Connect short gaps in dashed / broken ring outlines before hole find.
        close_k = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
        binary = cv2.morphologyEx(binary, cv2.MORPH_CLOSE, close_k, iterations=2)
    return binary


def _count_hollow_ring_holes(gray: Any, cv2: Any, np: Any) -> int:
    """Count braille-sized holes inside ring-like ink (CCOMP children)."""
    work, _ = _normalize_ink_gray(gray, np)
    h, w = work.shape[:2]
    closed = _ink_binary(work, cv2, close_dashes=True)
    _contours, hier = cv2.findContours(closed, cv2.RETR_CCOMP, cv2.CHAIN_APPROX_SIMPLE)
    if hier is None:
        return 0
    hier_arr = hier[0]
    max_r = min(h, w) * 0.08
    n = 0
    for i, cnt in enumerate(_contours):
        if hier_arr[i][3] < 0:
            continue
        area = cv2.contourArea(cnt)
        if area < 4:
            continue
        (_cx, _cy), radius = cv2.minEnclosingCircle(cnt)
        if 1.0 <= radius <= max_r * 0.85:
            n += 1
    return n


def solidify_hollow_rings(gray: Any, cv2: Any | None = None, np: Any | None = None) -> Any:
    """Turn hollow / dashed braille rings into solid dark disks.

    Textbook charts often draw raised dots as empty circles or dashed outlines.
    Classical filled-dot OCR rejects those; this preprocess paints solid blobs at
    ring centers (hole centers in a CCOMP hierarchy, plus bright-interior
    top-level rings after mild morphological closing).

    Returns a new grayscale image (same polarity as input). Does not modify
    ``gray`` in place.
    """
    if cv2 is None or np is None:
        cv2, np = _require_cv()
    work, inverted = _normalize_ink_gray(gray, np)
    h, w = work.shape[:2]
    closed = _ink_binary(work, cv2, close_dashes=True)
    contours, hier = cv2.findContours(closed, cv2.RETR_CCOMP, cv2.CHAIN_APPROX_SIMPLE)
    out = work.copy()
    if hier is None:
        return (255 - out) if inverted else out

    hier_arr = hier[0]
    max_r = min(h, w) * 0.08
    centers: list[tuple[float, float, float]] = []

    def _paint(cx: float, cy: float, radius: float) -> None:
        if radius < 1.5 or radius > max_r:
            return
        for x, y, rr in centers:
            lim = max(radius, rr) * 0.7
            if (cx - x) ** 2 + (cy - y) ** 2 < lim * lim:
                return
        x0, y0 = int(round(cx)), int(round(cy))
        rad_draw = max(2, int(round(radius)))
        cv2.circle(out, (x0, y0), rad_draw, 0, thickness=-1)
        centers.append((cx, cy, radius))

    for i, cnt in enumerate(contours):
        area = float(cv2.contourArea(cnt))
        (cx, cy), radius = cv2.minEnclosingCircle(cnt)
        peri = float(cv2.arcLength(cnt, True)) or 1.0
        circularity = 4.0 * float(np.pi) * area / (peri * peri)
        parent = int(hier_arr[i][3])
        child = int(hier_arr[i][2])

        # Hole inside a ring outline → fill slightly larger than the hole.
        if parent >= 0:
            if circularity < 0.3 or area < 4:
                continue
            if radius < 1.0 or radius > max_r * 0.85:
                continue
            _paint(float(cx), float(cy), float(radius) * 1.35)
            continue

        # Top-level: dashed arcs that closed into a near-disk with bright center.
        if child >= 0:
            # Holes already handled; skip large merged parents.
            continue
        if radius < 1.5 or radius > max_r:
            continue
        if circularity < 0.28 or area < 8 or area > float(h * w) * 0.02:
            continue
        r_in = max(1, int(round(radius * 0.35)))
        x0, y0 = int(round(cx)), int(round(cy))
        y1, y2 = max(0, y0 - r_in), min(h, y0 + r_in + 1)
        x1, x2 = max(0, x0 - r_in), min(w, x0 + r_in + 1)
        patch = work[y1:y2, x1:x2]
        if patch.size == 0:
            continue
        imean = float(np.mean(patch))
        circle_area = float(np.pi * radius * radius)
        fill_ratio = float(area / circle_area) if circle_area > 0 else 0.0
        if imean > 110.0 or fill_ratio < 0.55:
            _paint(float(cx), float(cy), float(radius) * 0.85)

    return (255 - out) if inverted else out


def _should_solidify_hollow(
    gray: Any,
    filled_dots: list[tuple[float, float, float]],
    cv2: Any,
    np: Any,
) -> bool:
    """Auto: solidify when filled-dot OCR is weak vs hollow-ring evidence.

    Skips mixed charts (filled = raised, hollow = unraised) that already yield
    many solid dots — solidifying those hollow rings would invent false dots.
    """
    n_solid = len(filled_dots)
    if n_solid < 3:
        return True
    n_holes = _count_hollow_ring_holes(gray, cv2, np)
    if n_holes >= 6 and n_solid < n_holes * 0.35:
        return True
    return False



def _cluster_rows(ys: list[float], tol: float) -> list[list[int]]:
    """Cluster point indices by y into horizontal rows."""
    order = sorted(range(len(ys)), key=lambda i: ys[i])
    rows: list[list[int]] = []
    for idx in order:
        if not rows:
            rows.append([idx])
            continue
        prev = rows[-1]
        if abs(ys[idx] - ys[prev[0]]) <= tol:
            prev.append(idx)
        else:
            rows.append([idx])
    return rows


def _dots_to_cells(
    dots: list[tuple[float, float, float]],
    np: Any,
) -> tuple[list[list[str]], float]:
    """Cluster dots into 2×3 braille cells; return rows of Unicode chars + confidence."""
    if len(dots) < 1:
        return [], 0.0, []

    xs = [d[0] for d in dots]
    ys = [d[1] for d in dots]
    radii = [d[2] for d in dots]
    med_r = float(np.median(radii)) if radii else 3.0
    # Typical inter-dot spacing ≈ 2–3× radius for rendered samples; use adaptive.
    # Estimate vertical pitch from nearest-neighbour dy.
    if len(dots) >= 2:
        dys = []
        for i, (x, y, _) in enumerate(dots):
            best = 1e18
            for j, (x2, y2, _) in enumerate(dots):
                if i == j:
                    continue
                dy = abs(y2 - y)
                dx = abs(x2 - x)
                if dy < best and dy > med_r * 0.5 and dx < med_r * 4:
                    best = dy
            if best < 1e17:
                dys.append(best)
        pitch_y = float(np.median(dys)) if dys else med_r * 2.5
        dxs = []
        for i, (x, y, _) in enumerate(dots):
            best = 1e18
            for j, (x2, y2, _) in enumerate(dots):
                if i == j:
                    continue
                dx = abs(x2 - x)
                dy = abs(y2 - y)
                if dx < best and dx > med_r * 0.5 and dy < med_r * 4:
                    best = dx
            if best < 1e17:
                dxs.append(best)
        pitch_x = float(np.median(dxs)) if dxs else pitch_y
    else:
        pitch_y = med_r * 2.5
        pitch_x = pitch_y

    # Cell height ≈ 2 * pitch_y (3 rows of dots → 2 gaps)
    cell_h = pitch_y * 2.0
    cell_w = pitch_x * 1.0  # 2 columns → 1 gap; may refine

    # Group into cell rows by y of top-of-cell estimate
    # First cluster all dots into fine rows (dot rows)
    row_tol = pitch_y * 0.45
    fine_rows = _cluster_rows(ys, row_tol)
    # Merge every 3 consecutive fine rows into a braille cell row
    cell_row_groups: list[list[list[int]]] = []
    i = 0
    while i < len(fine_rows):
        group = fine_rows[i : i + 3]
        if len(group) >= 1:
            cell_row_groups.append(group)
        i += 3

    unicode_rows: list[list[str]] = []
    row_x_all: list[list[float]] = []
    matched = 0
    expected_slots = 0

    for group in cell_row_groups:
        # Flatten indices in this cell-row
        idxs = [ix for fr in group for ix in fr]
        if not idxs:
            continue
        # Sort by x
        idxs.sort(key=lambda k: xs[k])
        # Cluster into columns (dot columns); then pair into cells (2 cols each)
        col_tol = pitch_x * 0.45
        cols: list[list[int]] = []
        for ix in idxs:
            if not cols:
                cols.append([ix])
                continue
            if abs(xs[ix] - xs[cols[-1][0]]) <= col_tol:
                cols[-1].append(ix)
            else:
                cols.append([ix])

        # Estimate cell width from column spacing
        if len(cols) >= 2:
            col_xs = [float(np.mean([xs[k] for k in c])) for c in cols]
            gaps = [col_xs[j + 1] - col_xs[j] for j in range(len(col_xs) - 1)]
            med_gap = float(np.median(gaps)) if gaps else pitch_x
        else:
            med_gap = pitch_x
            col_xs = [float(np.mean([xs[k] for k in c])) for c in cols]

        # Group columns into cells: within-cell gap ≈ pitch_x, between-cell larger
        cells_cols: list[list[int]] = []  # each entry: list of column indices into cols
        j = 0
        while j < len(cols):
            if j + 1 < len(cols) and (col_xs[j + 1] - col_xs[j]) < med_gap * 1.55:
                cells_cols.append([j, j + 1])
                j += 2
            else:
                # Single column cell (only left or right dots present)
                cells_cols.append([j])
                j += 1

        # Also detect large gaps for table column separators
        row_chars: list[str] = []
        cell_x_centers: list[float] = []
        y0 = float(np.mean([ys[k] for k in idxs]))
        # Reference top-left of cell row
        for cell_col_idxs in cells_cols:
            # Collect dots in this cell
            cell_dots = [k for ci in cell_col_idxs for k in cols[ci]]
            if not cell_dots:
                row_chars.append("\u2800")
                cell_x_centers.append(0.0)
                continue
            cx0 = min(xs[k] for k in cell_dots)
            cy0 = min(ys[k] for k in cell_dots)
            # Use median of fine-row ys in group for row origins
            fine_y = []
            for fr in group:
                if fr:
                    fine_y.append(float(np.mean([ys[k] for k in fr])))
            while len(fine_y) < 3:
                # Pad missing rows using pitch
                fine_y.append(fine_y[-1] + pitch_y if fine_y else y0)

            bit = 0
            expected_slots += 6
            for k in cell_dots:
                # Map to nearest of 3×2 grid
                dy = ys[k] - fine_y[0]
                row_i = int(round(dy / pitch_y)) if pitch_y > 0 else 0
                row_i = max(0, min(2, row_i))
                # Column within cell
                if len(cell_col_idxs) == 1:
                    # Decide left/right by relative x within cell span
                    col_i = 0
                    # If only one column of dots, check which side relative to cell center estimate
                    # Prefer left (col 0) by default; if dots are sparse right-only, still col 0
                else:
                    # Which of the two columns?
                    cxs = [col_xs[ci] for ci in cell_col_idxs]
                    col_i = 0 if abs(xs[k] - cxs[0]) <= abs(xs[k] - cxs[1]) else 1
                key = (row_i, col_i)
                if key in _DOT_BITS:
                    bit |= _DOT_BITS[key]
                    matched += 1
            ch = chr(0x2800 + bit)
            row_chars.append(ch)
            cell_x_centers.append(float(np.mean([xs[k] for k in cell_dots])))

        unicode_rows.append(row_chars)
        row_x_all.append(cell_x_centers)

    conf = (matched / expected_slots) if expected_slots else 0.0
    conf = max(0.0, min(1.0, conf * 0.85 + 0.15))  # mild prior when dots found
    return unicode_rows, conf, row_x_all


def _group_row_by_gaps(
    chars: list[str],
    xs: list[float],
    *,
    col_gap_factor: float = 1.35,
) -> list[str]:
    """Group consecutive braille chars into tokens using x-gap heuristics.

    Small gaps → same token (concatenated). Large gaps → new table column (`` | ``).
    """
    if not chars:
        return []
    if len(chars) == 1 or not xs or len(xs) != len(chars):
        return ["".join(chars)] if not xs else list(chars)

    gaps = [xs[i + 1] - xs[i] for i in range(len(xs) - 1)]
    if not gaps:
        return ["".join(chars)]
    # Within-token gaps cluster low; column gaps are outliers above ~1.3× base.
    sg = sorted(gaps)
    # Use lower 50% mean as within-token baseline (robust when few columns).
    low = sg[: max(1, (len(sg) + 1) // 2)]
    base = sum(low) / len(low)
    thresh = base * col_gap_factor

    tokens: list[str] = []
    buf = [chars[0]]
    for i, g in enumerate(gaps):
        if g >= thresh:
            tokens.append("".join(buf))
            buf = [chars[i + 1]]
        else:
            buf.append(chars[i + 1])
    tokens.append("".join(buf))
    return tokens


def _rows_to_braille_text(
    rows: list[list[str]],
    row_xs: list[list[float]] | None = None,
    *,
    as_flat_table: bool = False,
) -> str:
    """Join cell rows into multiline braille, optionally flat table with | / ||."""
    if not rows:
        return ""
    if not as_flat_table:
        return "\n".join("".join(r) for r in rows)

    if all(len(r) <= 1 for r in rows):
        return "\n".join("".join(r) for r in rows)

    flat_rows = []
    for i, r in enumerate(rows):
        xs = row_xs[i] if row_xs and i < len(row_xs) else []
        tokens = _group_row_by_gaps(list(r), list(xs)) if xs else list(r)
        flat_rows.append(" | ".join(tokens))
    return " || ".join(flat_rows)


def _opencv_detect(
    image: PathLike | Any,
    *,
    solidify_hollow: bool | str = True,
) -> dict[str, Any]:
    """Filled-dot OCR; optionally solidify hollow/dashed rings and retry.

    ``solidify_hollow``:
      - True / ``"auto"``: solidify only when the first pass is weak or the
        image looks like hollow/dashed line-art (many ring holes, few solids).
      - ``"always"``: always run solidify and keep the denser dot set.
      - False / ``"off"``: never solidify (mixed filled+hollow charts stay safe).

    Unicode digital-table screenshots never reach this path.
    """
    cv2, np = _require_cv()
    gray = _load_gray(image, cv2, np)
    dots = _detect_dots(gray, cv2, np)
    used_solidify = False

    flag = solidify_hollow
    if isinstance(flag, str):
        flag_l = flag.strip().lower()
        always = flag_l in {"always", "force", "on"}
        auto_on = flag_l in {"auto", "true", "yes", "1"}
        off = flag_l in {"off", "false", "no", "0"}
    else:
        always = False
        auto_on = bool(flag)
        off = flag is False

    if not off and (always or (auto_on and _should_solidify_hollow(gray, dots, cv2, np))):
        solidified = solidify_hollow_rings(gray, cv2, np)
        dots2 = _detect_dots(solidified, cv2, np)
        if always or len(dots2) > len(dots):
            dots = dots2
            used_solidify = True

    method = "opencv_dots_solidified" if used_solidify else "opencv_dots"
    if not dots:
        return {
            "braille": "",
            "rows": [],
            "method": method,
            "confidence": 0.0,
            "detail": "no dots found",
            "solidified": used_solidify,
        }
    cell_rows, conf, row_xs = _dots_to_cells(dots, np)
    # Prefer flat table when multiple cells per row
    multi = any(len(r) > 1 for r in cell_rows)
    text = _rows_to_braille_text(cell_rows, row_xs, as_flat_table=multi)
    # Also keep newline form
    lined = "\n".join("".join(r) for r in cell_rows)
    return {
        "braille": text or lined,
        "rows": cell_rows,
        "method": method,
        "confidence": round(float(conf), 3),
        "lined": lined,
        "n_dots": len(dots),
        "solidified": used_solidify,
    }


def _load_bgr(image: PathLike | Any, cv2: Any, np: Any) -> Any:
    """Load BGR ndarray from path / PIL / ndarray."""
    if hasattr(image, "shape"):
        arr = np.asarray(image)
        if arr.ndim == 2:
            return cv2.cvtColor(arr, cv2.COLOR_GRAY2BGR)
        if arr.shape[2] >= 3:
            # assume RGB if from PIL-ish; callers pass BGR from cv2 usually
            return arr[:, :, :3].copy()
        return cv2.cvtColor(arr[:, :, 0], cv2.COLOR_GRAY2BGR)
    if hasattr(image, "convert"):
        from PIL import Image

        rgb = np.array(image.convert("RGB"))
        return cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR)
    path = Path(image)
    if not path.is_file():
        raise FileNotFoundError(f"image not found: {path}")
    data = np.fromfile(str(path), dtype=np.uint8)
    bgr = cv2.imdecode(data, cv2.IMREAD_COLOR)
    if bgr is None:
        from PIL import Image

        rgb = np.array(Image.open(path).convert("RGB"))
        return cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR)
    return bgr


def _line_centers(mask: Any, axis: int, np: Any) -> list[int]:
    """Return centers of thick runs along projection of ``mask``."""
    proj = mask.sum(axis=1).astype(float) if axis == 0 else mask.sum(axis=0).astype(float)
    if float(proj.max()) <= 0:
        return []
    thr = float(proj.max()) * 0.3
    idxs = np.where(proj >= thr)[0]
    if len(idxs) == 0:
        return []
    groups: list[tuple[int, int]] = []
    start = int(idxs[0])
    prev = int(idxs[0])
    for i in idxs[1:]:
        i = int(i)
        if i - prev > 2:
            groups.append((start, prev))
            start = i
        prev = i
    groups.append((start, prev))
    return [int((a + b) // 2) for a, b in groups]


def _cluster_1d(vals: list[float], idxs: list[int], tol: float) -> list[list[int]]:
    order = sorted(idxs, key=lambda i: vals[i])
    groups: list[list[int]] = []
    for i in order:
        if not groups or abs(vals[i] - vals[groups[-1][0]]) > tol:
            groups.append([i])
        else:
            groups[-1].append(i)
    return groups


def _global_dot_pitch(
    dots: list[tuple[float, float]],
    *,
    horiz: bool,
    np: Any,
    max_orth: float = 16.0,
) -> float:
    pitches: list[float] = []
    for i, (x, y) in enumerate(dots):
        best = 1e18
        for j, (x2, y2) in enumerate(dots):
            if i == j:
                continue
            dx, dy = abs(x2 - x), abs(y2 - y)
            if horiz:
                if dx > 1.5 and dy < max_orth and dx < best:
                    best = dx
            else:
                if dy > 1.5 and dx < max_orth and dy < best:
                    best = dy
        if best < 1e17:
            pitches.append(float(best))
    if not pitches:
        return 6.0
    m = float(np.percentile(pitches, 15))
    small = [p for p in pitches if p <= m * 1.6]
    return float(np.median(small if small else pitches[: max(1, len(pitches) // 5)]))


def _decode_digital_cell(
    cell_dots: list[tuple[float, float]],
    pitch_x: float,
    pitch_y: float,
    np: Any,
) -> str:
    """Decode one table-cell of font-rendered braille dots to Unicode (+ spaces)."""
    if not cell_dots:
        return ""
    xs_ = [d[0] for d in cell_dots]
    ys_ = [d[1] for d in cell_dots]
    y0, y1 = min(ys_), max(ys_)
    span = y1 - y0
    if span > pitch_y * 1.4:
        fine_y = [y0, y0 + span / 2.0, y1]
    else:
        fine_y = [y0 - pitch_y, y0, y0 + pitch_y]

    col_groups = _cluster_1d(xs_, list(range(len(cell_dots))), pitch_x * 0.5)
    col_xs = [float(np.mean([xs_[k] for k in g])) for g in col_groups]
    if len(col_xs) >= 2:
        gaps = [col_xs[i + 1] - col_xs[i] for i in range(len(col_xs) - 1)]
        sg = sorted(gaps)
        low = sg[: max(1, (len(sg) + 1) // 2)]
        within = min(sum(low) / len(low), pitch_x * 1.3)
        pair_thresh = within * 1.75
    else:
        pair_thresh = pitch_x * 1.75

    chars_cols: list[list[int]] = []
    j = 0
    while j < len(col_groups):
        if j + 1 < len(col_groups) and (col_xs[j + 1] - col_xs[j]) <= pair_thresh:
            chars_cols.append([j, j + 1])
            j += 2
        else:
            chars_cols.append([j])
            j += 1

    out_chars: list[str] = []
    for ccols in chars_cols:
        idxs = [k for c in ccols for k in col_groups[c]]
        bit = 0
        cxs = [col_xs[c] for c in ccols]
        for k in idxs:
            row_i = int(np.argmin([abs(ys_[k] - fy) for fy in fine_y]))
            if len(ccols) == 1:
                col_i = 0
            else:
                col_i = 0 if abs(xs_[k] - cxs[0]) <= abs(xs_[k] - cxs[1]) else 1
            bit |= _DOT_BITS.get((row_i, col_i), 0)
        out_chars.append(chr(0x2800 + bit))

    if len(out_chars) <= 1:
        return "".join(out_chars)

    # Syllable spaces: gap between last col of char i and first of i+1.
    # Single-column chars inflate that gap by ~pitch_x (missing right col).
    tokens: list[str] = []
    buf = [out_chars[0]]
    for i in range(len(chars_cols) - 1):
        left = chars_cols[i]
        right = chars_cols[i + 1]
        gap = col_xs[right[0]] - col_xs[left[-1]]
        if len(left) == 1:
            gap -= pitch_x
        if gap >= pitch_x * 2.45:
            tokens.append("".join(buf))
            buf = [out_chars[i + 1]]
        else:
            buf.append(out_chars[i + 1])
    tokens.append("".join(buf))
    return " ".join(tokens)


def _digital_table_screenshot_detect(image: PathLike | Any) -> dict[str, Any] | None:
    """Detect Unicode braille inside an HTML/UI table screenshot.

    Screen-font braille (U+2800 glyphs) is not embossed paper: classical filled-
    dot OCR mis-clusters font dots across cell borders. Here we:

    1. Find the table grid via long horizontal/vertical edge runs
    2. Collect dark ink blobs (individual font dots)
    3. Decode each grid cell with a global 2×3 pitch estimate

    Returns None when the image does not look like a digital braille table.
    """
    try:
        cv2, np = _require_cv()
    except ImportError:
        return None

    try:
        bgr = _load_bgr(image, cv2, np)
    except Exception:
        return None
    gray = cv2.cvtColor(bgr, cv2.COLOR_BGR2GRAY)
    h, w = gray.shape[:2]
    mean = float(np.mean(gray))
    # Digital screenshots are bright pages; reject dark photos here.
    if mean < 180 or h < 40 or w < 80:
        return None

    absy = np.abs(cv2.Sobel(gray, cv2.CV_32F, 0, 1, ksize=3))
    absx = np.abs(cv2.Sobel(gray, cv2.CV_32F, 1, 0, ksize=3))
    ymax = float(absy.max()) or 1.0
    xmax = float(absx.max()) or 1.0
    _, hbin = cv2.threshold((absy / ymax * 255).astype(np.uint8), 40, 255, cv2.THRESH_BINARY)
    _, vbin = cv2.threshold((absx / xmax * 255).astype(np.uint8), 40, 255, cv2.THRESH_BINARY)
    hk = cv2.getStructuringElement(cv2.MORPH_RECT, (max(8, w // 8), 1))
    vk = cv2.getStructuringElement(cv2.MORPH_RECT, (1, max(8, h // 8)))
    hl = cv2.morphologyEx(hbin, cv2.MORPH_OPEN, hk)
    vl = cv2.morphologyEx(vbin, cv2.MORPH_OPEN, vk)
    ys = _line_centers(hl, 0, np)
    xs = _line_centers(vl, 1, np)
    if len(ys) < 3 or len(xs) < 3:
        return None
    n_rows, n_cols = len(ys) - 1, len(xs) - 1
    if n_rows < 1 or n_cols < 1 or n_rows * n_cols > 80:
        return None

    # Dark font dots (reject mid-gray grid lines)
    _, ink = cv2.threshold(gray, 100, 255, cv2.THRESH_BINARY_INV)
    nlab, _labels, stats, centroids = cv2.connectedComponentsWithStats(ink, connectivity=8)
    dots: list[tuple[float, float]] = []
    for i in range(1, nlab):
        area = int(stats[i, cv2.CC_STAT_AREA])
        if 3 <= area <= 80:
            dots.append((float(centroids[i, 0]), float(centroids[i, 1])))
    if len(dots) < 6:
        return None

    pitch_x = _global_dot_pitch(dots, horiz=True, np=np)
    pitch_y = _global_dot_pitch(dots, horiz=False, np=np)
    if pitch_x < 2 or pitch_y < 2:
        return None

    pad = 2
    grid: list[list[str]] = []
    nonempty = 0
    for ri in range(n_rows):
        row: list[str] = []
        y0, y1 = ys[ri] + pad, ys[ri + 1] - pad
        for ci in range(n_cols):
            x0, x1 = xs[ci] + pad, xs[ci + 1] - pad
            cell = [d for d in dots if x0 <= d[0] <= x1 and y0 <= d[1] <= y1]
            text = _decode_digital_cell(cell, pitch_x, pitch_y, np)
            if text.strip():
                nonempty += 1
            row.append(text)
        grid.append(row)

    if nonempty < max(2, (n_rows * n_cols) // 4):
        return None

    flat = " || ".join(" | ".join(r) for r in grid)
    # Also expose token rows (one string per table cell)
    conf = min(0.95, 0.55 + 0.02 * nonempty)
    return {
        "braille": flat,
        "rows": grid,
        "method": "digital_table_unicode",
        "confidence": round(float(conf), 3),
        "n_dots": len(dots),
        "grid": [n_rows, n_cols],
        "detail": "screenshot of Unicode braille table cells",
    }


def _unicode_screenshot_detect(image: PathLike | Any) -> dict[str, Any] | None:
    """Extract Unicode braille from digital screenshots (tables or plain OCR).

    Prefer grid+dot decoding for HTML table screenshots; fall back to
    pytesseract when it actually returns U+2800–U+283F characters.
    """
    digital = _digital_table_screenshot_detect(image)
    if digital and digital.get("braille"):
        return digital

    try:
        from PIL import Image
        import numpy as np
    except ImportError:
        return None

    if hasattr(image, "convert"):
        pil = image.convert("RGB")
    elif hasattr(image, "shape"):
        arr = image
        if getattr(arr, "ndim", 0) == 2:
            pil = Image.fromarray(arr)
        else:
            pil = Image.fromarray(arr[:, :, ::-1] if arr.shape[2] >= 3 else arr)
    else:
        path = Path(image)
        if not path.is_file():
            return None
        pil = Image.open(path).convert("RGB")

    try:
        import pytesseract  # type: ignore

        text = pytesseract.image_to_string(pil, lang="eng") or ""
        found = _BRAILLE_RE.findall(text)
        if found:
            braille = "\n".join(found)
            return {
                "braille": braille,
                "rows": [
                    [c for c in line if "\u2800" <= c <= "\u283f"]
                    for line in braille.splitlines()
                ],
                "method": "pytesseract_unicode",
                "confidence": 0.55,
            }
    except Exception:
        pass

    return None


def detect_braille_detailed(
    image: PathLike | Any,
    mode: str = "auto",
) -> dict[str, Any]:
    """Detect braille and return a detailed dict.

    Keys: ``braille``, ``rows``, ``method``, ``confidence``.
    """
    mode = (mode or "auto").strip().lower()
    if _stub_enabled():
        name = Path(image).name if isinstance(image, (str, Path)) else "array"
        return {
            "braille": f"⠁[scaffold-ocr:{name}]",
            "rows": [["⠁"]],
            "method": "stub",
            "confidence": None,
        }

    errors: list[str] = []
    uni: dict[str, Any] | None = None

    # Try digital Unicode-braille table screenshots first. Font-rendered glyphs
    # fool classical filled-dot OCR into confident but wrong layouts.
    if mode in {"auto", "unicode", "screenshot", "digital"}:
        try:
            uni = _unicode_screenshot_detect(image)
        except Exception as exc:  # noqa: BLE001
            errors.append(f"unicode: {type(exc).__name__}: {exc}")
            uni = None
        if uni and uni.get("braille"):
            if mode != "auto" or uni.get("method") == "digital_table_unicode":
                return uni

    # Photo / line-art branch (skip Unicode digital path's solidify).
    solidify_flag: bool | str = True
    if mode in {"solidify", "hollow", "dashed"}:
        mode = "opencv"
        solidify_flag = "always"
    elif mode in {"opencv", "dots"}:
        solidify_flag = True
    elif mode == "auto":
        solidify_flag = True

    if mode in {"auto", "opencv", "dots"}:
        try:
            result = _opencv_detect(image, solidify_hollow=solidify_flag)
            if result.get("braille") or mode != "auto":
                if (
                    mode == "auto"
                    and uni
                    and uni.get("braille")
                    and (
                        float(result.get("confidence") or 0) < 0.6
                        or (
                            isinstance(result.get("rows"), list)
                            and any(len(r) > 8 for r in result["rows"])
                        )
                    )
                ):
                    return uni
                return result
        except ImportError:
            if mode != "auto":
                raise
            errors.append("opencv missing")
        except Exception as exc:  # noqa: BLE001
            if mode != "auto":
                raise
            errors.append(f"opencv: {type(exc).__name__}: {exc}")

    if uni and uni.get("braille"):
        return uni

    # Final: if OpenCV missing entirely, raise clear error (unless stub)
    try:
        _require_cv()
    except ImportError:
        raise

    return {
        "braille": "",
        "rows": [],
        "method": "none",
        "confidence": 0.0,
        "errors": errors,
    }


def detect_braille(image: PathLike | Any, mode: str = "auto") -> str:
    """Return Unicode braille text detected in ``image``.

    Parameters
    ----------
    image:
        Path, ndarray, or PIL Image.
    mode:
        ``auto`` | ``opencv`` | ``unicode`` | ``solidify`` (force hollow solidify).
    """
    if _stub_enabled():
        name = Path(image).name if isinstance(image, (str, Path)) else "array"
        return f"⠁[scaffold-ocr:{name}]"
    detail = detect_braille_detailed(image, mode=mode)
    return str(detail.get("braille") or "")
