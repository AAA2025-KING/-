"""Smoke tests: imports and pipeline shape without downloading models."""

from __future__ import annotations

import os

import pytest

from chinese_braille_toolkit import __version__, detect, pipeline, translate


def test_version():
    assert __version__.startswith("0.1")


def test_detect_stub(tmp_path, monkeypatch):
    monkeypatch.setenv("CBT_OCR_STUB", "1")
    # Re-import path uses env at call time
    img = tmp_path / "page.png"
    img.write_bytes(b"")
    out = detect(img)
    assert isinstance(out, str)
    assert "scaffold-ocr" in out
    assert "page.png" in out


def test_detect_empty_image_no_crash(tmp_path):
    """Invalid/empty file should not crash; may return empty or raise clearly."""
    pytest.importorskip("cv2")
    img = tmp_path / "empty.png"
    img.write_bytes(b"not-an-image")
    try:
        out = detect(img)
        assert isinstance(out, str)
    except (ValueError, OSError, FileNotFoundError):
        pass


def test_translate_backends():
    braille = "⠑⠁"
    mt5 = translate(braille, backend="mt5")
    qwen = translate(braille, context="新闻", backend="qwen8b")
    auto = translate(braille, backend="auto")
    assert "scaffold-mt5" in mt5
    assert "scaffold-qwen8b" in qwen
    assert "新闻" in qwen
    assert "scaffold-mt5" in auto  # auto → mt5 in scaffold


def test_pipeline_keys(tmp_path, monkeypatch):
    monkeypatch.setenv("CBT_OCR_STUB", "1")
    img = tmp_path / "chart.jpg"
    img.write_bytes(b"")
    result = pipeline(img, backend="auto")
    required = {"braille", "text", "backend", "confidence"}
    assert required <= set(result.keys())
    assert isinstance(result["braille"], str)
    assert isinstance(result["text"], str)
    assert result["backend"] == "mt5"


def test_unknown_backend_raises():
    try:
        translate("⠁", backend="nope")
    except ValueError as exc:
        assert "nope" in str(exc)
    else:
        raise AssertionError("expected ValueError for unknown backend")
