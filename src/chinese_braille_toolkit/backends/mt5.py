"""mT5-small Chinese braille translation backend (stub).

Target model (not loaded in scaffold):
https://huggingface.co/Violet-yo/mt5-small-ft-Chinese-Braille
"""

from __future__ import annotations


def translate(braille: str, context: str | None = None) -> str:
    """Placeholder translate via mt5. Does not download or run the model."""
    ctx = f" context={context!r}" if context else ""
    preview = braille if len(braille) <= 80 else braille[:77] + "..."
    return f"[scaffold-mt5]{ctx} input={preview!r}"
