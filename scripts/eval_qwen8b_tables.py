#!/usr/bin/env python3
"""Run Vision-Braille-Qwen3-8B on synthetic-table holdout (optional LoRA adapter).

Model: Violet-yo/Vision-Braille-Qwen3-8B (CC BY-NC-SA — research eval OK)
Chat template per model card (Braille→中文). Prefer 4-bit on 8GB VRAM.

Writes (defaults; override with --report / --preds):
  data/synthetic_tables/eval_qwen8b_report.md
  data/synthetic_tables/eval_qwen8b_predictions.jsonl
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
import traceback
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "synthetic_tables"
JSONL = DATA / "tables.jsonl"
REPORT_DEFAULT = DATA / "eval_qwen8b_report.md"
PREDS_DEFAULT = DATA / "eval_qwen8b_predictions.jsonl"
MODEL_ID = "Violet-yo/Vision-Braille-Qwen3-8B"
DEFAULT_LOCAL = Path(__file__).resolve().parents[1] / "models" / "Vision-Braille-Qwen3-8B"

SYSTEM = "你是一个中国盲文翻译助手，请把通用盲文转换成为汉字。"
USER_TMPL = "请把以下通用盲文转换成为汉字：\n盲文内容是:\n{braille}"
ASSIST_PREFIX = "对应的中文内容是：\n"


def load_tables() -> list[dict]:
    tables = []
    for line in JSONL.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            tables.append(json.loads(line))
    return tables


def build_samples_t01(tables: list[dict]) -> list[dict]:
    """Same subset as eval_mt5_tables.py: t01 header + first data row + flat partial."""
    t01 = next(t for t in tables if t["id"] == "t01")
    samples: list[dict] = []
    for col, cell in enumerate(t01["cells"][0]):
        samples.append(
            {
                "sample_id": f"t01-r0-c{col}",
                "table_id": "t01",
                "kind": "cell",
                "row": 0,
                "col": col,
                "braille": cell["braille"],
                "ref_zh": cell["zh"],
                "tone": cell["tone"],
            }
        )
    for col, cell in enumerate(t01["cells"][1]):
        samples.append(
            {
                "sample_id": f"t01-r1-c{col}",
                "table_id": "t01",
                "kind": "cell",
                "row": 1,
                "col": col,
                "braille": cell["braille"],
                "ref_zh": cell["zh"],
                "tone": cell["tone"],
            }
        )
    header_br = " | ".join(c["braille"] for c in t01["cells"][0])
    header_zh = " | ".join(c["zh"] for c in t01["cells"][0])
    row1_br = " | ".join(c["braille"] for c in t01["cells"][1])
    row1_zh = " | ".join(c["zh"] for c in t01["cells"][1])
    samples.append(
        {
            "sample_id": "t01-flat-header-row1",
            "table_id": "t01",
            "kind": "flat_partial",
            "row": None,
            "col": None,
            "braille": header_br + " || " + row1_br,
            "ref_zh": header_zh + " || " + row1_zh,
            "tone": "mixed",
        }
    )
    return samples


def build_samples_all(tables: list[dict]) -> list[dict]:
    """Every cell in all holdout tables + one flat_partial (header+first data row) per table."""
    samples: list[dict] = []
    for t in tables:
        tid = t["id"]
        cells = t["cells"]
        for row_i, row in enumerate(cells):
            for col, cell in enumerate(row):
                samples.append(
                    {
                        "sample_id": f"{tid}-r{row_i}-c{col}",
                        "table_id": tid,
                        "kind": "cell",
                        "row": row_i,
                        "col": col,
                        "braille": cell["braille"],
                        "ref_zh": cell["zh"],
                        "tone": cell["tone"],
                    }
                )
        if len(cells) >= 2:
            header_br = " | ".join(c["braille"] for c in cells[0])
            header_zh = " | ".join(c["zh"] for c in cells[0])
            row1_br = " | ".join(c["braille"] for c in cells[1])
            row1_zh = " | ".join(c["zh"] for c in cells[1])
            samples.append(
                {
                    "sample_id": f"{tid}-flat-header-row1",
                    "table_id": tid,
                    "kind": "flat_partial",
                    "row": None,
                    "col": None,
                    "braille": header_br + " || " + row1_br,
                    "ref_zh": header_zh + " || " + row1_zh,
                    "tone": "mixed",
                }
            )
    return samples


def build_samples(tables: list[dict], subset: str) -> list[dict]:
    if subset == "t01":
        return build_samples_t01(tables)
    if subset == "all":
        return build_samples_all(tables)
    raise ValueError(f"Unknown subset: {subset}")


def cer(ref: str, hyp: str) -> float | None:
    if not ref:
        return None
    n, m = len(ref), len(hyp)
    dp = list(range(m + 1))
    for i in range(1, n + 1):
        prev, dp = dp, [i] + [0] * m
        for j in range(1, m + 1):
            cost = 0 if ref[i - 1] == hyp[j - 1] else 1
            dp[j] = min(dp[j - 1] + 1, prev[j] + 1, prev[j - 1] + cost)
    return dp[m] / n


def normalize_zh(s: str) -> str:
    return "".join(s.split())


def strip_assistant_prefix(text: str) -> str:
    """Recover translation: strip reply prefix and any echoed chat fluff."""
    t = text.strip()
    # Prefer the dedicated reply marker from the model card
    marker = "对应的中文内容是："
    if marker in t:
        t = t.split(marker, 1)[1]
        if t.startswith("\n"):
            t = t[1:]
        return t.strip()
    # Fallback: last assistant-looking chunk
    for alt in ("对应的中文内容是:", "中文内容是：", "中文内容是:"):
        if alt in t:
            t = t.split(alt, 1)[1].lstrip("\n").strip()
            return t
    return t


def write_fail_report(
    report_path: Path, title: str, detail: str, meta: dict | None = None, adapter: str = ""
) -> None:
    heading = (
        "# Qwen3-8B + LoRA adapter holdout eval (synthetic tables)"
        if adapter
        else "# Qwen3-8B real translation eval (synthetic tables)"
    )
    lines = [
        heading,
        "",
        f"**Failed:** {title}",
        "",
        f"```\n{detail}\n```",
        "",
    ]
    if meta:
        lines.append("## Attempt meta")
        lines.append("")
        for k, v in meta.items():
            lines.append(f"- {k}: `{v}`")
        lines.append("")
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text("\n".join(lines), encoding="utf-8")


def load_model(quant: str, device: str, model_id: str = MODEL_ID):
    """Return (tokenizer, model, load_info). quant: 4bit|8bit|bf16|fp16|auto"""
    import torch
    from transformers import AutoModelForCausalLM, AutoTokenizer

    info: dict = {"quant_requested": quant, "device_arg": device}
    tok = AutoTokenizer.from_pretrained(model_id, trust_remote_code=True)

    kwargs: dict = {
        "trust_remote_code": True,
        "device_map": {"": 0} if quant in ("4bit", "8bit", "auto") else "auto",
    }
    # 8GB cards: device_map="auto" sometimes offloads a few modules to CPU and bnb then errors;
    # pinning all layers to cuda:0 works for Qwen3-8B 4-bit (~5.7GB).

    if quant == "4bit":
        from transformers import BitsAndBytesConfig

        kwargs["quantization_config"] = BitsAndBytesConfig(
            load_in_4bit=True,
            bnb_4bit_compute_dtype=torch.float16,
            bnb_4bit_use_double_quant=True,
            bnb_4bit_quant_type="nf4",
        )
        info["quant_applied"] = "4bit-nf4"
    elif quant == "8bit":
        from transformers import BitsAndBytesConfig

        kwargs["quantization_config"] = BitsAndBytesConfig(load_in_8bit=True)
        info["quant_applied"] = "8bit"
    elif quant == "bf16":
        kwargs["torch_dtype"] = torch.bfloat16
        info["quant_applied"] = "bf16"
    elif quant == "fp16":
        kwargs["torch_dtype"] = torch.float16
        info["quant_applied"] = "fp16"
    else:
        # auto: try 4bit if cuda else fp16/cpu
        if torch.cuda.is_available():
            from transformers import BitsAndBytesConfig

            kwargs["quantization_config"] = BitsAndBytesConfig(
                load_in_4bit=True,
                bnb_4bit_compute_dtype=torch.float16,
                bnb_4bit_use_double_quant=True,
                bnb_4bit_quant_type="nf4",
            )
            info["quant_applied"] = "4bit-nf4 (auto)"
        else:
            kwargs["torch_dtype"] = torch.float32
            kwargs["device_map"] = "cpu"
            info["quant_applied"] = "fp32-cpu (auto, no cuda)"

    model = AutoModelForCausalLM.from_pretrained(model_id, **kwargs)
    model.eval()
    info["cuda"] = bool(torch.cuda.is_available())
    if torch.cuda.is_available():
        info["gpu_name"] = torch.cuda.get_device_name(0)
        info["vram_total_gb"] = round(
            torch.cuda.get_device_properties(0).total_memory / 1024**3, 2
        )
        info["vram_alloc_gb"] = round(torch.cuda.memory_allocated(0) / 1024**3, 3)
    return tok, model, info


def attach_adapter(model, adapter_path: str):
    """Load PEFT LoRA adapter on top of base model; return (model, info)."""
    from peft import PeftModel

    info = {"adapter_path": adapter_path}
    model = PeftModel.from_pretrained(model, adapter_path)
    model.eval()
    info["adapter_loaded"] = True
    try:
        cfg = getattr(model, "peft_config", None)
        if cfg:
            # peft_config is usually a dict keyed by adapter name
            first = next(iter(cfg.values())) if isinstance(cfg, dict) else cfg
            info["peft_type"] = str(getattr(first, "peft_type", type(first).__name__))
            info["r"] = getattr(first, "r", None)
            info["lora_alpha"] = getattr(first, "lora_alpha", None)
    except Exception as exc:  # noqa: BLE001
        info["peft_meta_error"] = f"{type(exc).__name__}: {exc}"
    return model, info


def translate_one(tok, model, braille: str, max_new_tokens: int, repetition_penalty: float) -> str:
    import torch

    messages = [
        {"role": "system", "content": SYSTEM},
        {"role": "user", "content": USER_TMPL.format(braille=braille)},
    ]
    prompt = tok.apply_chat_template(
        messages, tokenize=False, add_generation_prompt=True
    )
    inputs = tok(prompt, return_tensors="pt")
    # Move to model device
    try:
        dev = next(model.parameters()).device
    except StopIteration:
        dev = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    inputs = {k: v.to(dev) for k, v in inputs.items()}
    input_len = inputs["input_ids"].shape[1]

    with torch.no_grad():
        out = model.generate(
            **inputs,
            max_new_tokens=max_new_tokens,
            do_sample=False,  # greedy — more stable for short cells
            repetition_penalty=repetition_penalty,
            pad_token_id=tok.eos_token_id,
        )
    gen_ids = out[0][input_len:]
    raw = tok.decode(gen_ids, skip_special_tokens=True)
    return strip_assistant_prefix(raw), raw


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--quant",
        default="4bit",
        choices=["4bit", "8bit", "bf16", "fp16", "auto"],
        help="Load precision (default 4bit for 8GB VRAM)",
    )
    parser.add_argument("--cell-max-new", type=int, default=32)
    parser.add_argument("--flat-max-new", type=int, default=64)
    parser.add_argument("--repetition-penalty", type=float, default=1.15)
    parser.add_argument("--host-label", default="", help="Hostname note for report")
    parser.add_argument("--model-path", default="", help="Local model dir override")
    parser.add_argument(
        "--adapter",
        default="",
        help="Optional PEFT LoRA adapter path (e.g. outputs/lora_tables_win_v2/checkpoint-80)",
    )
    parser.add_argument(
        "--subset",
        default="all",
        choices=["t01", "all"],
        help="t01 = 9 samples (legacy); all = every holdout cell + flat per table (default)",
    )
    parser.add_argument(
        "--report",
        default="",
        help="Override report markdown path (relative to project root or absolute)",
    )
    parser.add_argument(
        "--preds",
        default="",
        help="Override predictions JSONL path (relative to project root or absolute)",
    )
    args = parser.parse_args()

    report_path = Path(args.report) if args.report else REPORT_DEFAULT
    preds_path = Path(args.preds) if args.preds else PREDS_DEFAULT
    if not report_path.is_absolute():
        report_path = ROOT / report_path
    if not preds_path.is_absolute():
        preds_path = ROOT / preds_path

    if not JSONL.is_file():
        print(f"Missing {JSONL}", file=sys.stderr)
        return 1

    tables = load_tables()
    samples = build_samples(tables, args.subset)
    print(f"Samples to translate: {len(samples)} (subset={args.subset})")

    host = args.host_label or os.environ.get("COMPUTERNAME") or os.uname().nodename
    if args.model_path:
        model_id = args.model_path
    elif DEFAULT_LOCAL.is_dir() and (DEFAULT_LOCAL / "config.json").is_file():
        model_id = str(DEFAULT_LOCAL)
    else:
        model_id = MODEL_ID
    print(f"Using model path/id: {model_id}")
    adapter_path = args.adapter.strip()
    if adapter_path:
        print(f"Using adapter: {adapter_path}")
    t0 = time.time()
    meta = {
        "host": host,
        "model": model_id,
        "adapter": adapter_path or "(none — base only)",
        "subset": args.subset,
        "quant": args.quant,
        "cell_max_new": args.cell_max_new,
        "flat_max_new": args.flat_max_new,
        "repetition_penalty": args.repetition_penalty,
        "report": str(report_path),
        "preds": str(preds_path),
    }

    try:
        import torch

        print(
            f"torch={torch.__version__} cuda={torch.cuda.is_available()} "
            f"device={torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'cpu'}"
        )
    except Exception as exc:
        write_fail_report(
            report_path, "import torch failed", f"{type(exc).__name__}: {exc}", meta, adapter_path
        )
        print(f"Import failed: {exc}", file=sys.stderr)
        return 2

    try:
        print(f"Loading {model_id} quant={args.quant} …")
        tok, model, load_info = load_model(args.quant, "auto", model_id=model_id)
        meta.update(load_info)
        print(f"Loaded base in {time.time() - t0:.1f}s: {load_info}")
        if adapter_path:
            print(f"Attaching adapter from {adapter_path} …")
            model, adapter_info = attach_adapter(model, adapter_path)
            meta.update(adapter_info)
            if torch.cuda.is_available():
                meta["vram_alloc_gb_after_adapter"] = round(
                    torch.cuda.memory_allocated(0) / 1024**3, 3
                )
            print(f"Adapter attached: {adapter_info}")
    except Exception as exc:
        tb = traceback.format_exc(limit=20)
        oom = "out of memory" in str(exc).lower() or "oom" in str(exc).lower()
        title = "OOM while loading model/adapter" if oom else "Failed to load model/adapter"
        write_fail_report(
            report_path, title, f"{type(exc).__name__}: {exc}\n\n{tb}", meta, adapter_path
        )
        print(f"Load failed: {exc}", file=sys.stderr)
        return 3

    results: list[dict] = []
    try:
        for i, s in enumerate(samples, 1):
            is_flat = s["kind"] == "flat_partial"
            max_new = args.flat_max_new if is_flat else args.cell_max_new
            pred, raw = translate_one(
                tok, model, s["braille"], max_new, args.repetition_penalty
            )
            ref = s["ref_zh"]
            c_raw = cer(ref, pred)
            c_ns = cer(normalize_zh(ref), normalize_zh(pred))
            row = {
                **s,
                "pred": pred,
                "pred_raw": raw,
                "exact_match": pred == ref,
                "exact_match_nospace": normalize_zh(pred) == normalize_zh(ref),
                "cer": None if c_raw is None else round(c_raw, 4),
                "cer_nospace": None if c_ns is None else round(c_ns, 4),
                "max_new_tokens": max_new,
            }
            results.append(row)
            print(
                f"  [{i}/{len(samples)}] {s['sample_id']}: ref={ref!r} pred={pred!r} "
                f"CER={row['cer']} CER_ns={row['cer_nospace']}"
            )
            if torch.cuda.is_available() and (i == 1 or i % 20 == 0 or i == len(samples)):
                print(
                    f"    vram_alloc={torch.cuda.memory_allocated(0)/1024**3:.2f}GB "
                    f"peak={torch.cuda.max_memory_allocated(0)/1024**3:.2f}GB"
                )
    except Exception as exc:
        tb = traceback.format_exc(limit=20)
        oom = ("CUDA out of memory" in str(exc)) or (
            type(exc).__name__ == "OutOfMemoryError"
        ) or ("out of memory" in str(exc).lower())
        if results:
            preds_path.parent.mkdir(parents=True, exist_ok=True)
            preds_path.write_text(
                "\n".join(json.dumps(r, ensure_ascii=False) for r in results) + "\n",
                encoding="utf-8",
            )
        title = (
            f"OOM mid-inference after {len(results)} samples"
            if oom
            else f"Failed mid-inference after {len(results)} samples"
        )
        write_fail_report(
            report_path, title, f"{type(exc).__name__}: {exc}\n\n{tb}", meta, adapter_path
        )
        print(f"Infer failed: {exc}", file=sys.stderr)
        return 4

    elapsed = round(time.time() - t0, 1)
    if torch.cuda.is_available():
        meta["vram_peak_gb"] = round(torch.cuda.max_memory_allocated(0) / 1024**3, 3)

    preds_path.parent.mkdir(parents=True, exist_ok=True)
    preds_path.write_text(
        "\n".join(json.dumps(r, ensure_ascii=False) for r in results) + "\n",
        encoding="utf-8",
    )

    cell_results = [r for r in results if r["kind"] == "cell"]
    flat_results = [r for r in results if r["kind"] == "flat_partial"]
    n = len(cell_results)
    exact_rate = sum(1 for r in cell_results if r["exact_match"]) / n if n else 0.0
    exact_ns_rate = (
        sum(1 for r in cell_results if r["exact_match_nospace"]) / n if n else 0.0
    )
    mean_cer = (
        sum(r["cer"] for r in cell_results if r["cer"] is not None) / n if n else None
    )
    mean_cer_ns = (
        sum(r["cer_nospace"] for r in cell_results if r["cer_nospace"] is not None) / n
        if n
        else None
    )

    heading = (
        "# Qwen3-8B + LoRA adapter holdout eval (synthetic tables)"
        if adapter_path
        else "# Qwen3-8B real translation eval (synthetic tables)"
    )
    subset_desc = (
        "t01 header + first data row (8 cells) + 1 partial flat"
        if args.subset == "t01"
        else f"all holdout tables ({len(tables)} tables): every cell + 1 flat_partial per table"
    )
    try:
        preds_rel = str(preds_path.relative_to(ROOT))
    except ValueError:
        preds_rel = str(preds_path)

    lines = [
        heading,
        "",
        f"- Model: `{model_id}`",
        f"- Adapter: `{adapter_path or '(none — base only)'}`",
        f"- Host: **{host}**",
        f"- Quantization: **{meta.get('quant_applied', args.quant)}**",
        f"- CUDA: `{meta.get('cuda')}` gpu=`{meta.get('gpu_name', 'n/a')}` "
        f"VRAM={meta.get('vram_total_gb', 'n/a')}GB peak_alloc={meta.get('vram_peak_gb', 'n/a')}GB",
        f"- Chat template: model-card system + user (`盲文内容是:` ASCII colon); strip `对应的中文内容是：`",
        f"- Generate: greedy (`do_sample=False`), "
        f"`max_new_tokens` cell={args.cell_max_new} / flat={args.flat_max_new}, "
        f"`repetition_penalty={args.repetition_penalty}`",
        f"- License note: CC BY-NC-SA 4.0 — research eval only",
        f"- Elapsed: **{elapsed}s** (load + {len(results)} inferences)",
        f"- Subset: {subset_desc}",
        f"- Predictions JSONL: `{preds_rel}`",
        "",
        "## Status",
        "",
        f"**Success:** {len(results)}/{len(samples)} samples produced predictions. No OOM.",
        "",
        "## Aggregate (cells only)",
        "",
        f"- N cells: **{n}**",
        f"- N flats: **{len(flat_results)}**",
        f"- Exact-match rate: **{exact_rate:.1%}**",
        f"- Exact-match (ignore spaces): **{exact_ns_rate:.1%}**",
        f"- Mean CER (raw): **{mean_cer:.4f}**" if mean_cer is not None else "- Mean CER: n/a",
        f"- Mean CER (no spaces): **{mean_cer_ns:.4f}**"
        if mean_cer_ns is not None
        else "- Mean CER (no spaces): n/a",
        "",
        "## Per-sample",
        "",
        "| id | kind | braille | ref_zh | pred | exact | CER | CER_ns |",
        "|----|------|---------|--------|------|-------|-----|--------|",
    ]
    for r in results:
        br = r["braille"].replace("|", "\\|")
        if len(br) > 48:
            br = br[:45] + "…"
        pred = str(r["pred"]).replace("|", "\\|").replace("\n", " ")
        if len(pred) > 40:
            pred = pred[:37] + "…"
        ref = str(r["ref_zh"]).replace("|", "\\|")
        lines.append(
            f"| `{r['sample_id']}` | {r['kind']} | `{br}` | {ref} | {pred} | "
            f"{r['exact_match']} | {r['cer']} | {r['cer_nospace']} |"
        )

    lines += [
        "",
        "## Notes",
        "",
        "- Same synthetic Braille holdout set (pypinyin ~10% tone); OOD vs model's passage training.",
        "- Short table cells + `|` separators are out-of-domain; compare primarily vs base on this set.",
        "- Generation capped to avoid the repetition loops seen in mT5 with max_new_tokens=300.",
        "- Chart OCR out of scope; translation step 2 only.",
        "",
        "## Inputs / outputs detail",
        "",
    ]
    for r in results:
        lines += [
            f"### `{r['sample_id']}`",
            "",
            f"- braille: `{r['braille']}`",
            f"- ref_zh: `{r['ref_zh']}`",
            f"- pred: `{r['pred']}`",
            f"- tone: {r['tone']}; exact={r['exact_match']}; "
            f"CER={r['cer']}; CER_ns={r['cer_nospace']}",
            "",
        ]

    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text("\n".join(lines), encoding="utf-8")
    print(f"Wrote {report_path}")
    print(f"Wrote {preds_path}")
    print(
        f"DONE exact={exact_rate:.1%} exact_ns={exact_ns_rate:.1%} "
        f"mean_cer={mean_cer} mean_cer_ns={mean_cer_ns} "
        f"n_cells={n} n_flats={len(flat_results)} elapsed={elapsed}s "
        f"adapter={adapter_path or 'none'}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
