#!/usr/bin/env python3
"""LoRA / QLoRA training skeleton for table-domain Braille→Chinese.

Does NOT run a full train by default beyond a short max_steps smoke once deps
and a local model are present. Missing peft/transformers/bitsandbytes → clear exit.

Example:
  python scripts/train_lora_tables.py --config configs/lora_tables.yaml --max-steps 10
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CONFIG = ROOT / "configs" / "lora_tables.yaml"
DEFAULT_DATA = ROOT / "data" / "train_tables_placeholder.jsonl"
DEFAULT_OUT = ROOT / "outputs" / "lora_tables"
DEFAULT_MODEL = "Violet-yo/Vision-Braille-Qwen3-8B"

SYSTEM = "你是一个中国盲文翻译助手，请把通用盲文转换成为汉字。"


def _load_yaml(path: Path) -> dict[str, Any]:
    try:
        import yaml  # type: ignore
    except ImportError:
        # Minimal fallback: only support flat keys we need via CLI; empty dict OK.
        print(
            "[train_lora_tables] PyYAML not installed; using CLI defaults only "
            "(pip install pyyaml or install .[train]).",
            file=sys.stderr,
        )
        return {}
    with path.open(encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def _require_train_stack() -> None:
    missing: list[str] = []
    for mod in ("torch", "transformers", "peft", "datasets", "trl"):
        try:
            __import__(mod)
        except ImportError:
            missing.append(mod)
    if missing:
        print(
            "[train_lora_tables] Missing packages: "
            + ", ".join(missing)
            + "\nInstall with:\n  pip install -e \".[train]\"\n"
            "Then re-run with a local --model-path and --data-path.",
            file=sys.stderr,
        )
        raise SystemExit(2)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="QLoRA/LoRA skeleton: table Braille → Chinese (Qwen3-8B family)"
    )
    p.add_argument("--config", type=Path, default=DEFAULT_CONFIG, help="YAML config path")
    p.add_argument("--model-path", type=str, default=None, help="HF id or local dir")
    p.add_argument("--data-path", type=Path, default=None, help="JSONL ShareGPT/instruction")
    p.add_argument("--output-dir", type=Path, default=None, help="Adapter output directory")
    p.add_argument("--lora-r", type=int, default=None, help="LoRA rank")
    p.add_argument("--lora-alpha", type=int, default=None, help="LoRA alpha")
    p.add_argument(
        "--bits",
        type=int,
        choices=(4, 16),
        default=None,
        help="4=QLoRA (≈8GB), 16=bf16 LoRA",
    )
    p.add_argument("--max-steps", type=int, default=None, help="Trainer max_steps")
    p.add_argument(
        "--dry-run",
        action="store_true",
        help="Parse config + count samples; do not load model or train",
    )
    p.add_argument(
        "--offload-dir",
        type=Path,
        default=None,
        help="Disk offload folder when GPU RAM is tight or CUDA is absent",
    )
    p.add_argument(
        "--resume-from-checkpoint",
        type=Path,
        default=None,
        help="HF/TRL checkpoint dir to resume (adapter + optimizer); passed to trainer.train()",
    )
    p.add_argument(
        "--logging-steps",
        type=int,
        default=None,
        help="Override Trainer logging_steps (e.g. 5 for denser loss curve)",
    )
    p.add_argument(
        "--optim",
        type=str,
        default=None,
        help="Trainer optim (e.g. paged_adamw_8bit, adamw_torch)",
    )
    return p.parse_args(argv)


def merge_settings(args: argparse.Namespace) -> dict[str, Any]:
    cfg = _load_yaml(args.config) if args.config.is_file() else {}
    model = cfg.get("model") or {}
    quant = cfg.get("quantization") or {}
    lora = cfg.get("lora") or {}
    data = cfg.get("data") or {}
    train = cfg.get("train") or {}

    return {
        "model_path": args.model_path or model.get("path") or DEFAULT_MODEL,
        "data_path": Path(args.data_path or data.get("path") or DEFAULT_DATA),
        "output_dir": Path(args.output_dir or train.get("output_dir") or DEFAULT_OUT),
        "lora_r": args.lora_r if args.lora_r is not None else int(lora.get("r", 16)),
        "lora_alpha": (
            args.lora_alpha if args.lora_alpha is not None else int(lora.get("alpha", 32))
        ),
        "lora_dropout": float(lora.get("dropout", 0.05)),
        "target_modules": lora.get("target_modules")
        or ["q_proj", "k_proj", "v_proj", "o_proj", "gate_proj", "up_proj", "down_proj"],
        "bits": args.bits if args.bits is not None else int(quant.get("bits", 4)),
        "max_steps": (
            args.max_steps if args.max_steps is not None else int(train.get("max_steps", 200))
        ),
        "max_seq_length": int(data.get("max_seq_length", 512)),
        "per_device_train_batch_size": int(train.get("per_device_train_batch_size", 1)),
        "gradient_accumulation_steps": int(train.get("gradient_accumulation_steps", 8)),
        "learning_rate": float(train.get("learning_rate", 2e-4)),
        "warmup_ratio": float(train.get("warmup_ratio", 0.03)),
        "logging_steps": (
            args.logging_steps
            if args.logging_steps is not None
            else int(train.get("logging_steps", 10))
        ),
        "save_steps": int(train.get("save_steps", 100)),
        "seed": int(train.get("seed", 42)),
        "trust_remote_code": bool(model.get("trust_remote_code", True)),
        "dry_run": bool(args.dry_run),
        "offload_dir": args.offload_dir,
        "resume_from_checkpoint": args.resume_from_checkpoint,
        "optim": args.optim,
    }


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.is_file():
        print(f"[train_lora_tables] Data file not found: {path}", file=sys.stderr)
        raise SystemExit(1)
    rows: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            rows.append(json.loads(line))
    return rows


def example_to_text(ex: dict[str, Any]) -> str:
    """Flatten ShareGPT conversations or braille/zh fields into one training string."""
    if "conversations" in ex:
        parts: list[str] = []
        for turn in ex["conversations"]:
            role = turn.get("from") or turn.get("role") or ""
            val = turn.get("value") or turn.get("content") or ""
            if role in ("system",):
                parts.append(f"<|im_start|>system\n{val}<|im_end|>")
            elif role in ("human", "user"):
                parts.append(f"<|im_start|>user\n{val}<|im_end|>")
            elif role in ("gpt", "assistant"):
                parts.append(f"<|im_start|>assistant\n{val}<|im_end|>")
        return "\n".join(parts)
    braille = ex.get("braille") or ex.get("input") or ""
    zh = ex.get("zh") or ex.get("output") or ""
    user = f"请把以下通用盲文转换成为汉字：\n盲文内容是:\n{braille}"
    return (
        f"<|im_start|>system\n{SYSTEM}<|im_end|>\n"
        f"<|im_start|>user\n{user}<|im_end|>\n"
        f"<|im_start|>assistant\n对应的中文内容是：\n{zh}<|im_end|>"
    )


def run_dry(settings: dict[str, Any], rows: list[dict[str, Any]]) -> None:
    print("=== train_lora_tables dry-run ===")
    print(f"model_path:   {settings['model_path']}")
    print(f"data_path:    {settings['data_path']}  ({len(rows)} examples)")
    print(f"output_dir:   {settings['output_dir']}")
    print(f"bits:         {settings['bits']}  (4=QLoRA, 16=LoRA)")
    print(f"lora r/alpha: {settings['lora_r']} / {settings['lora_alpha']}")
    print(f"max_steps:    {settings['max_steps']}")
    if rows:
        sample = example_to_text(rows[0])
        preview = sample.replace("\n", "\\n")[:200]
        try:
            print(f"sample[0]:    {preview}...")
        except UnicodeEncodeError:
            print(f"sample[0]:    {preview.encode('unicode_escape').decode('ascii')}...")
    print("Dry-run OK. Install .[train] and drop --dry-run to train.")


def train(settings: dict[str, Any], rows: list[dict[str, Any]]) -> None:
    _require_train_stack()

    import torch
    from datasets import Dataset
    from peft import LoraConfig, get_peft_model, prepare_model_for_kbit_training
    from transformers import (
        AutoModelForCausalLM,
        AutoTokenizer,
        BitsAndBytesConfig,
        TrainingArguments,
    )
    from trl import SFTTrainer

    model_path = settings["model_path"]
    local = Path(model_path)
    if local.exists() and not any(local.iterdir()):
        print(f"[train_lora_tables] Model dir empty: {local}", file=sys.stderr)
        raise SystemExit(1)

    print(f"[train_lora_tables] Loading tokenizer/model from {model_path} ...")
    tokenizer = AutoTokenizer.from_pretrained(
        model_path, trust_remote_code=settings["trust_remote_code"],
    )
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token

    bnb_config = None
    if settings["bits"] == 4:
        try:
            import bitsandbytes  # noqa: F401
        except ImportError:
            print(
                "[train_lora_tables] bits=4 needs bitsandbytes "
                "(pip install bitsandbytes). Or pass --bits 16.",
                file=sys.stderr,
            )
            raise SystemExit(2)
        bnb_config = BitsAndBytesConfig(
            load_in_4bit=True,
            bnb_4bit_quant_type="nf4",
            bnb_4bit_use_double_quant=True,
            bnb_4bit_compute_dtype=torch.bfloat16,
        )

    has_cuda = torch.cuda.is_available()
    offload_dir = settings.get("offload_dir")
    if offload_dir is None and not has_cuda:
        offload_dir = ROOT / "outputs" / "offload_train"
    if offload_dir is not None:
        offload_dir = Path(offload_dir)
        if not offload_dir.is_absolute():
            offload_dir = ROOT / offload_dir
        offload_dir.mkdir(parents=True, exist_ok=True)

    if settings["bits"] == 4 and not has_cuda:
        print(
            "[train_lora_tables] No CUDA: keeping bits=4 on CPU (needs bitsandbytes+kernels). "
            "Disk-offload bf16 train is unsupported (meta/autocast).",
            file=sys.stderr,
        )

    # Prefer whole-model on GPU 0. "auto" on Windows WDDM can park layers on
    # CPU and trip bitsandbytes; {"": 0} is the reliable path for 8GB cards.
    model_kwargs: dict[str, Any] = {
        "trust_remote_code": settings["trust_remote_code"],
        "device_map": ({"": 0} if has_cuda else "auto"),
        "low_cpu_mem_usage": True,
    }
    if has_cuda:
        # Hint accelerate/bnb about budget (helps some stacks; harmless with {"":0}).
        model_kwargs["max_memory"] = {0: "7600MiB", "cpu": "2GiB"}
    if bnb_config is not None:
        model_kwargs["quantization_config"] = bnb_config
    else:
        # Prefer bf16 on CUDA; float16/float32 on CPU offload hosts.
        model_kwargs["torch_dtype"] = torch.bfloat16 if has_cuda else torch.float16

    if not has_cuda:
        if settings["bits"] == 4:
            # Full 4-bit weights on CPU (~5GB); known-working short-train path.
            model_kwargs["device_map"] = {"": "cpu"}
            if bnb_config is not None:
                # CPU 4bit prefers float32 compute
                import torch as _torch
                bnb_config.bnb_4bit_compute_dtype = _torch.float32
                model_kwargs["quantization_config"] = bnb_config
        elif offload_dir is not None:
            # bits=16 disk offload can *load* but Trainer autocast fails on meta devices.
            model_kwargs["offload_folder"] = str(offload_dir)
            model_kwargs["max_memory"] = {"cpu": "12GiB"}

    print(
        f"[train_lora_tables] cuda={has_cuda} bits={settings['bits']} "
        f"offload={offload_dir}",
        flush=True,
    )
    model = AutoModelForCausalLM.from_pretrained(model_path, **model_kwargs)
    if settings["bits"] == 4:
        model = prepare_model_for_kbit_training(model)

    lora_cfg = LoraConfig(
        r=settings["lora_r"],
        lora_alpha=settings["lora_alpha"],
        lora_dropout=settings["lora_dropout"],
        bias="none",
        task_type="CAUSAL_LM",
        target_modules=settings["target_modules"],
    )
    model = get_peft_model(model, lora_cfg)
    model.print_trainable_parameters()

    texts = [example_to_text(r) for r in rows]
    ds = Dataset.from_dict({"text": texts})

    out = settings["output_dir"]
    if not out.is_absolute():
        out = ROOT / out
    out.mkdir(parents=True, exist_ok=True)

    use_bf16 = bool(has_cuda and torch.cuda.is_bf16_supported())
    # Short smoke runs should log every step unless CLI/config overrides.
    log_every = settings["logging_steps"]
    if log_every is None or (settings["max_steps"] <= 20 and log_every >= 10):
        log_every = 1 if settings["max_steps"] <= 20 else int(log_every or 10)
    # transformers>=5 dropped warmup_ratio from TrainingArguments; derive steps.
    warmup_steps = max(0, int(settings["max_steps"] * float(settings["warmup_ratio"])))
    # CPU/disk-offload smoke: keep grad accum tiny to avoid hanging.
    grad_accum = settings["gradient_accumulation_steps"]
    if not has_cuda:
        grad_accum = min(grad_accum, 1)
    targs = TrainingArguments(
        output_dir=str(out),
        max_steps=settings["max_steps"],
        per_device_train_batch_size=settings["per_device_train_batch_size"],
        gradient_accumulation_steps=grad_accum,
        learning_rate=settings["learning_rate"],
        lr_scheduler_type="cosine",
        warmup_steps=warmup_steps,
        logging_steps=log_every,
        save_steps=min(settings["save_steps"], settings["max_steps"]),
        save_total_limit=2,
        bf16=use_bf16,
        fp16=bool(has_cuda and not use_bf16),
        gradient_checkpointing=True,
        optim=(
            settings["optim"]
            if settings.get("optim")
            else (
                "paged_adamw_8bit"
                if (settings["bits"] == 4 and has_cuda)
                else "adamw_torch"
            )
        ),
        report_to="none",
        seed=settings["seed"],
        dataloader_pin_memory=bool(has_cuda),
        remove_unused_columns=False,
        use_cpu=not has_cuda,
    )

    # trl API varies by version (1.x uses processing_class; older used tokenizer=)
    trainer = None
    last_err: Exception | None = None
    attempts = [
        dict(model=model, train_dataset=ds, args=targs, processing_class=tokenizer,
             formatting_func=lambda ex: ex["text"]),
        dict(model=model, train_dataset=ds, args=targs, processing_class=tokenizer,
             dataset_text_field="text"),
        dict(model=model, train_dataset=ds, args=targs, tokenizer=tokenizer,
             dataset_text_field="text", max_seq_length=settings["max_seq_length"]),
    ]
    for kwargs in attempts:
        try:
            trainer = SFTTrainer(**kwargs)
            break
        except TypeError as exc:
            last_err = exc
            continue
    if trainer is None:
        raise RuntimeError(f"SFTTrainer init failed: {last_err}")

    resume = settings.get("resume_from_checkpoint")
    resume_path = None
    if resume is not None:
        resume_path = Path(resume)
        if not resume_path.is_absolute():
            resume_path = ROOT / resume_path
        if not resume_path.is_dir():
            print(
                f"[train_lora_tables] resume checkpoint not found: {resume_path}",
                file=sys.stderr,
            )
            raise SystemExit(1)
        print(
            f"[train_lora_tables] RESUME from {resume_path} "
            f"→ max_steps={settings['max_steps']} "
            f"logging_steps={log_every}",
            flush=True,
        )
    else:
        print(
            f"[train_lora_tables] Starting train max_steps={settings['max_steps']} "
            f"logging_steps={log_every} (fresh)",
            flush=True,
        )

    if resume_path is not None:
        trainer.train(resume_from_checkpoint=str(resume_path))
    else:
        trainer.train()

    # Persist loss curve / Trainer metrics for reports (stdout can miss them).
    metrics_path = out / "train_metrics.json"
    try:
        history = list(getattr(trainer.state, "log_history", []) or [])
        metrics_path.write_text(
            json.dumps(
                {
                    "max_steps": settings["max_steps"],
                    "logging_steps": log_every,
                    "resume_from_checkpoint": str(resume_path) if resume_path else None,
                    "log_history": history,
                },
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )
        print(f"[train_lora_tables] Wrote metrics → {metrics_path} ({len(history)} entries)", flush=True)
    except Exception as exc:  # pragma: no cover
        print(f"[train_lora_tables] WARN: could not write train_metrics.json: {exc}", file=sys.stderr)

    trainer.save_model(str(out))
    tokenizer.save_pretrained(str(out))
    print(f"[train_lora_tables] Adapter saved to {out}", flush=True)


def main(argv: list[str] | None = None) -> None:
    args = parse_args(argv)
    settings = merge_settings(args)
    data_path = settings["data_path"]
    if not data_path.is_absolute():
        data_path = ROOT / data_path
        settings["data_path"] = data_path
    rows = load_jsonl(data_path)

    if settings["dry_run"] or args.dry_run:
        run_dry(settings, rows)
        return

    # Soft gate: if train stack missing, exit 2 with message (no traceback spam)
    try:
        train(settings, rows)
    except SystemExit:
        raise
    except Exception as exc:  # pragma: no cover - skeleton safety net
        print(f"[train_lora_tables] Failed: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc


if __name__ == "__main__":
    main()
