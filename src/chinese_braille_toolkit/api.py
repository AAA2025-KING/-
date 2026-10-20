"""Public API for chinese-braille-toolkit.

``detect`` / ``pipeline`` use classical OpenCV OCR when available.
``translate(..., backend="qwen8b")`` loads Vision-Braille-Qwen3-8B with an
optional LoRA adapter when CUDA (or ``CBT_QWEN_ALLOW_CPU``) and local weights
are available; otherwise returns a scaffold string for offline smoke tests.
Table restore: flat braille (`` | `` / `` || ``) → cell-by-cell translate.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from . import ocr
from . import tables as tables_mod
from .backends import mt5, qwen8b

PathLike = str | Path


def detect(image: PathLike, mode: str = "auto") -> str:
    """Detect braille cells in a chart/image and return Unicode braille text."""
    return ocr.detect_braille(image, mode=mode)


def detect_detailed(image: PathLike, mode: str = "auto") -> dict[str, Any]:
    """Detect braille and return ``braille``, ``rows``, ``method``, ``confidence``."""
    return ocr.detect_braille_detailed(image, mode=mode)


def translate(
    braille: str,
    context: str | None = None,
    backend: str = "auto",
    *,
    adapter_path: str | Path | None = None,
    model_path: str | Path | None = None,
    quant: str = "4bit",
    max_new_tokens: int = 32,
) -> str:
    """Translate Chinese braille to Han characters with optional context."""
    chosen = _resolve_backend(backend)
    if chosen == "qwen8b":
        return qwen8b.translate(
            braille,
            context=context,
            adapter_path=adapter_path,
            model_path=model_path,
            quant=quant,
            max_new_tokens=max_new_tokens,
        )
    return mt5.translate(braille, context=context)


def translate_table(
    cells_or_flat: Any,
    context: str | None = None,
    backend: str = "auto",
    **translate_kw: Any,
) -> dict[str, Any]:
    """Translate a flat braille table (or 2-D cells) cell-by-cell.

    Returns dict with ``cells``, ``flat_zh``, ``markdown``, ``csv``, ``html``,
    ``braille_cells``.
    """
    chosen = _resolve_backend(backend)

    def _fn(br: str, context: str | None = None) -> str:
        return translate(br, context=context, backend=chosen, **translate_kw)

    return tables_mod.translate_table(cells_or_flat, _fn, context=context)


def pipeline(
    image: PathLike,
    backend: str = "auto",
    *,
    as_table: bool = True,
    mode: str = "auto",
    context: str | None = None,
    **translate_kw: Any,
) -> dict[str, Any]:
    """Run detect → translate and return a structured result.

    When ``as_table`` is True and detected braille looks like a flat table
    (or multi-cell rows), translates cell-by-cell and includes a ``table`` dict.
    """
    chosen = _resolve_backend(backend)
    detail = detect_detailed(image, mode=mode)
    braille = str(detail.get("braille") or "")
    conf = detail.get("confidence")
    method = detail.get("method")

    out: dict[str, Any] = {
        "braille": braille,
        "text": "",
        "backend": chosen,
        "confidence": conf,
        "ocr_method": method,
    }

    if not braille:
        out["text"] = ""
        return out

    use_table = as_table and (
        tables_mod.is_flat_table(braille)
        or (isinstance(detail.get("rows"), list) and any(len(r) > 1 for r in detail["rows"]))
    )

    if use_table:
        # Prefer flat string; if only cell rows from OCR, convert
        if tables_mod.is_flat_table(braille):
            table = translate_table(braille, context=context, backend=chosen, **translate_kw)
        else:
            # rows of single-char cells → treat each char as a cell; join spaces
            # already in lined form. Build flat from rows.
            rows = detail.get("rows") or []
            flat = tables_mod.cells_to_flat([["".join(r)] if isinstance(r, list) else [str(r)] for r in rows])
            # Better: each unicode char is one cell for OCR multi-cell rows
            grid = []
            for r in rows:
                if isinstance(r, list):
                    grid.append([c for c in r])
                else:
                    grid.append([str(r)])
            table = translate_table(grid, context=context, backend=chosen, **translate_kw)
        out["table"] = {
            "cells": table["cells"],
            "markdown": table["markdown"],
            "csv": table["csv"],
            "html": table["html"],
            "flat_zh": table["flat_zh"],
        }
        out["text"] = table["flat_zh"]
    else:
        out["text"] = translate(braille, context=context, backend=chosen, **translate_kw)

    return out


def _resolve_backend(backend: str) -> str:
    name = (backend or "auto").strip().lower()
    if name == "auto":
        # Prefer light path until GPU probe + size heuristics land.
        return "mt5"
    if name in {"mt5", "qwen8b"}:
        return name
    raise ValueError(
        f"Unknown backend {backend!r}; expected 'auto', 'mt5', or 'qwen8b'."
    )
