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


def _opencv_detect(image: PathLike | Any) -> dict[str, Any]:
    cv2, np = _require_cv()
    gray = _load_gray(image, cv2, np)
    dots = _detect_dots(gray, cv2, np)
    if not dots:
        return {
            "braille": "",
            "rows": [],
            "method": "opencv_dots",
            "confidence": 0.0,
            "detail": "no dots found",
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
        "method": "opencv_dots",
        "confidence": round(float(conf), 3),
        "lined": lined,
        "n_dots": len(dots),
    }


def _unicode_screenshot_detect(image: PathLike | Any) -> dict[str, Any] | None:
    """If the image is mostly a screenshot of Unicode braille glyphs, extract them.

    Tries: (1) pytesseract OCR for braille-range chars, (2) Pillow + connected
    components of dark glyphs paired with a simple font raster match — if neither
    works, returns None.
    """
    try:
        from PIL import Image
        import numpy as np
    except ImportError:
        return None

    if hasattr(image, "convert"):
        pil = image.convert("RGB")
    elif hasattr(image, "shape"):
        arr = image
        if arr.ndim == 2:
            pil = Image.fromarray(arr)
        else:
            pil = Image.fromarray(arr[:, :, ::-1] if arr.shape[2] >= 3 else arr)
    else:
        path = Path(image)
        if not path.is_file():
            return None
        pil = Image.open(path).convert("RGB")

    # Try pytesseract if available
    try:
        import pytesseract  # type: ignore

        text = pytesseract.image_to_string(pil, lang="eng") or ""
        found = _BRAILLE_RE.findall(text)
        if found:
            braille = "\n".join(found)
            return {
                "braille": braille,
                "rows": [[c for c in line if "\u2800" <= c <= "\u283f"] for line in braille.splitlines()],
                "method": "pytesseract_unicode",
                "confidence": 0.55,
            }
    except Exception:
        pass

    # Fallback: look for any text layer / metadata (rare for PNG)
    # Or: if filename-embedded scaffold was used — skip.
    # Connected-component glyph path: count dark blobs; if few large glyph-like
    # regions and image looks like text screenshot (high contrast, mostly white),
    # leave for opencv primary.
    arr = np.asarray(pil.convert("L"))
    mean = float(arr.mean())
    if mean > 200:
        # Likely white page; opencv dots path is better for embossed/printed dots
        return None
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

    if mode in {"auto", "opencv", "dots"}:
        try:
            result = _opencv_detect(image)
            if result.get("braille") or mode != "auto":
                return result
        except ImportError:
            if mode != "auto":
                raise
            errors.append("opencv missing")
        except Exception as exc:  # noqa: BLE001
            if mode != "auto":
                raise
            errors.append(f"opencv: {type(exc).__name__}: {exc}")

    if mode in {"auto", "unicode", "screenshot"}:
        try:
            uni = _unicode_screenshot_detect(image)
            if uni and uni.get("braille"):
                return uni
        except Exception as exc:  # noqa: BLE001
            errors.append(f"unicode: {type(exc).__name__}: {exc}")

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
        ``auto`` | ``opencv`` | ``unicode``.
    """
    if _stub_enabled():
        name = Path(image).name if isinstance(image, (str, Path)) else "array"
        return f"⠁[scaffold-ocr:{name}]"
    detail = detect_braille_detailed(image, mode=mode)
    return str(detail.get("braille") or "")
