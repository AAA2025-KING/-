#!/usr/bin/env python3
"""Download Vision-Braille-Qwen3-8B via urllib (works when HF xet client stalls)."""
from __future__ import annotations

import os
import sys
import time
import urllib.request
from pathlib import Path

REPO = "Violet-yo/Vision-Braille-Qwen3-8B"
BASE = os.environ.get("HF_ENDPOINT", "https://hf-mirror.com").rstrip("/")
ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "models" / "Vision-Braille-Qwen3-8B"

FILES = [
    "config.json",
    "generation_config.json",
    "model.safetensors.index.json",
    "tokenizer.json",
    "tokenizer_config.json",
    "special_tokens_map.json",
    "added_tokens.json",
    "chat_template.jinja",
    "merges.txt",
    "vocab.json",
    "model-00001-of-00004.safetensors",
    "model-00002-of-00004.safetensors",
    "model-00003-of-00004.safetensors",
    "model-00004-of-00004.safetensors",
]

# Expected sizes for the four shards (from HEAD)
EXPECTED = {
    "model-00001-of-00004.safetensors": 4900586528,
    "model-00002-of-00004.safetensors": None,
    "model-00003-of-00004.safetensors": None,
    "model-00004-of-00004.safetensors": None,
}


def download_one(name: str) -> Path:
    OUT.mkdir(parents=True, exist_ok=True)
    dest = OUT / name
    part = OUT / (name + ".part")
    url = f"{BASE}/{REPO}/resolve/main/{name}"

    existing = dest.stat().st_size if dest.is_file() else 0
    if existing > 0 and name in EXPECTED and EXPECTED[name] and existing == EXPECTED[name]:
        print(f"SKIP {name} already complete ({existing} bytes)", flush=True)
        return dest
    if existing > 1024 and name.endswith(".json") or name.endswith(".txt") or name.endswith(".jinja"):
        if dest.is_file() and existing > 0:
            print(f"SKIP {name} exists ({existing} bytes)", flush=True)
            return dest

    # Resume from .part if present
    start = part.stat().st_size if part.is_file() else 0
    headers = {"User-Agent": "Mozilla/5.0 chinese-braille-toolkit-dl/1.0"}
    if start > 0:
        headers["Range"] = f"bytes={start}-"
        print(f"RESUME {name} from {start}", flush=True)
    else:
        print(f"START {name}", flush=True)

    req = urllib.request.Request(url, headers=headers)
    t0 = time.time()
    with urllib.request.urlopen(req, timeout=120) as resp:
        # If server ignored Range and returned 200, restart
        status = getattr(resp, "status", 200)
        if start > 0 and status == 200:
            print(f"server ignored Range; restarting {name}", flush=True)
            start = 0
            part.unlink(missing_ok=True)
        mode = "ab" if start > 0 and status == 206 else "wb"
        if mode == "wb":
            start = 0
        total_hdr = resp.headers.get("Content-Length")
        total = int(total_hdr) + start if total_hdr else None
        n = start
        last_print = t0
        with open(part, mode) as f:
            while True:
                chunk = resp.read(1024 * 1024)
                if not chunk:
                    break
                f.write(chunk)
                n += len(chunk)
                now = time.time()
                if now - last_print >= 5:
                    mb = n / 1024 / 1024
                    speed = (n - start) / 1024 / 1024 / max(now - t0, 0.01)
                    if total:
                        pct = 100.0 * n / total
                        print(f"  {name}: {mb:.1f}/{total/1024/1024:.1f} MB ({pct:.1f}%) @ {speed:.2f} MB/s", flush=True)
                    else:
                        print(f"  {name}: {mb:.1f} MB @ {speed:.2f} MB/s", flush=True)
                    last_print = now

    part.replace(dest)
    print(f"DONE {name} size={dest.stat().st_size} elapsed={time.time()-t0:.1f}s", flush=True)
    return dest


def main() -> int:
    print(f"OUT={OUT}", flush=True)
    print(f"BASE={BASE}", flush=True)
    t0 = time.time()
    for name in FILES:
        try:
            download_one(name)
        except Exception as exc:
            print(f"FAIL {name}: {type(exc).__name__}: {exc}", flush=True)
            return 1
    print(f"ALL_DONE elapsed={time.time()-t0:.1f}s", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
