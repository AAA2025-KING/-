"""Vision-Braille-Qwen3-8B translation backend with optional LoRA adapter.

Base weights: https://huggingface.co/Violet-yo/Vision-Braille-Qwen3-8B
License of weights: CC BY-NC-SA 4.0 (non-commercial oriented).

Loading policy
--------------
* Real inference when CUDA is available (or ``CBT_QWEN_ALLOW_CPU=1``), local /
  resolved base weights exist, and optional deps (transformers / peft / bnb)
  are installed.
* Otherwise returns a scaffold string so ``pip install`` / pytest stay offline.
* Force scaffold with ``CBT_QWEN_STUB=1`` (used by unit tests).

Adapter resolution (first hit wins)
-----------------------------------
1. Explicit ``adapter_path`` kwarg (empty string disables adapter)
2. Env ``CBT_QWEN_ADAPTER``
3. ``<repo>/models/lora_tables`` when ``adapter_config.json`` is present
4. No adapter (base model only)

Base model resolution
---------------------
1. Explicit ``model_path`` kwarg
2. Env ``CBT_QWEN_MODEL``
3. ``<repo>/models/Vision-Braille-Qwen3-8B`` when ``config.json`` is present
4. Hugging Face id ``Violet-yo/Vision-Braille-Qwen3-8B``
"""

from __future__ import annotations

import os
import threading
from pathlib import Path
from typing import Any

HF_MODEL_ID = "Violet-yo/Vision-Braille-Qwen3-8B"
SYSTEM = (
    "你是一个中国盲文翻译助手，请把通用盲文转换成为汉字。"
    "只输出汉字译文本身，不要输出 XML/HTML 标签、tool 标记、解释或其它语言。"
)
# Stricter prompt for table cells / short headers (防止一格生成多列管道串).
SYSTEM_CELL = (
    "你是一个中国盲文翻译助手。输入是表格中的【单个单元格】（多为短表头或数字）。"
    "只输出该单元格对应的简短汉字，通常 1～6 个字。"
    "严禁输出竖线|、多列、列表、换行、解释、XML/HTML 或 tool 标记。"
    "不要把一个单元格扩写成整行表头或多项内容。"
)
USER_TMPL = "请把以下通用盲文转换成为汉字：\n盲文内容:\n{braille}"
USER_CELL_TMPL = (
    "请把下列【单个表格单元格】盲文译成简短汉字（只译这一格）：\n"
    "{context_line}"
    "盲文内容:\n{braille}"
)
ASSIST_MARKER = "对应的中文内容是："

_REPO_ROOT = Path(__file__).resolve().parents[3]
_DEFAULT_MODEL_DIR = _REPO_ROOT / "models" / "Vision-Braille-Qwen3-8B"
_DEFAULT_ADAPTER_DIR = _REPO_ROOT / "models" / "lora_tables"

_lock = threading.Lock()
_cache: dict[str, Any] = {
    "key": None,
    "tok": None,
    "model": None,
    "meta": None,
}


def _truthy(val: str | None) -> bool:
    return (val or "").strip().lower() in {"1", "true", "yes", "on"}


def _want_stub() -> bool:
    if _truthy(os.environ.get("CBT_QWEN_STUB")):
        return True
    # Keep unit tests offline even when a local model tree exists.
    if "PYTEST_CURRENT_TEST" in os.environ:
        return True
    return False


def _cuda_ok() -> bool:
    try:
        import torch

        return bool(torch.cuda.is_available())
    except Exception:
        return False


def _allow_cpu() -> bool:
    return _truthy(os.environ.get("CBT_QWEN_ALLOW_CPU"))


def resolve_model_path(model_path: str | Path | None = None) -> str:
    """Return local dir or HF id for the base causal LM."""
    if model_path is not None and str(model_path).strip():
        return str(Path(model_path).expanduser())
    env = (os.environ.get("CBT_QWEN_MODEL") or "").strip()
    if env:
        return env
    if (_DEFAULT_MODEL_DIR / "config.json").is_file():
        return str(_DEFAULT_MODEL_DIR)
    return HF_MODEL_ID


def resolve_adapter_path(adapter_path: str | Path | None = None) -> str | None:
    """Return adapter dir, or None to run base-only.

    Pass ``adapter_path=""`` to explicitly disable the default adapter.
    """
    if adapter_path is not None:
        s = str(adapter_path).strip()
        if s == "":
            return None
        return str(Path(s).expanduser())
    env = os.environ.get("CBT_QWEN_ADAPTER")
    if env is not None:
        s = env.strip()
        if s == "":
            return None
        return s
    cfg = _DEFAULT_ADAPTER_DIR / "adapter_config.json"
    if cfg.is_file():
        return str(_DEFAULT_ADAPTER_DIR)
    return None


def _adapter_ready(path: str | None) -> bool:
    if not path:
        return False
    p = Path(path)
    if not (p / "adapter_config.json").is_file():
        return False
    return (p / "adapter_model.safetensors").is_file() or (
        p / "adapter_model.bin"
    ).is_file()


def _strip_assistant_prefix(text: str) -> str:
    t = text.strip()
    if ASSIST_MARKER in t:
        t = t.split(ASSIST_MARKER, 1)[1]
        if t.startswith("\n"):
            t = t[1:]
        t = t.strip()
    else:
        for alt in ("对应的中文内容是:", "中文内容是：", "中文内容是:"):
            if alt in t:
                t = t.split(alt, 1)[1].lstrip("\n").strip()
                break
    # Drop leaked tool / chat-template markers from cell generations.
    import re

    t = re.sub(
        r"</?\s*tool_?response\s*>|</?\s*tool_?calls?\s*>|</?\s*quote\s*>|<\|/?[^|>]+\|>",
        "",
        t,
        flags=re.IGNORECASE,
    )
    t = re.sub(r"[ \t]{2,}", " ", t)
    return t.strip()


def _braille_compact_len(braille: str) -> int:
    return len((braille or "").replace(" ", "").replace("\u2800", ""))


def _is_short_cell(braille: str) -> bool:
    """Heuristic: table headers / numeric cells are short braille strings."""
    return _braille_compact_len(braille) <= 12


def _build_messages(braille: str, context: str | None, *, cell_mode: bool) -> list[dict[str, str]]:
    if cell_mode or _is_short_cell(braille):
        ctx = (context or "").strip()
        context_line = f"表格上下文: {ctx}\n" if ctx else ""
        return [
            {"role": "system", "content": SYSTEM_CELL},
            {
                "role": "user",
                "content": USER_CELL_TMPL.format(
                    braille=braille, context_line=context_line
                ),
            },
        ]
    return [
        {"role": "system", "content": SYSTEM},
        {"role": "user", "content": USER_TMPL.format(braille=braille)},
    ]


def _finalize_cell_output(text: str) -> str:
    """Post-process a single-cell translation: first line only, no pipes."""
    t = _strip_assistant_prefix(text)
    if not t:
        return ""
    # Stop at first newline (model sometimes dumps a fake multi-row table).
    if "\n" in t:
        t = t.split("\n", 1)[0].strip()
    # Single cell must never contain column separators.
    if "|" in t:
        # Keep the first segment only — rest is usually hallucinated columns.
        t = t.split("|", 1)[0].strip()
    t = t.strip(" |\t")
    return t


def _load_base(model_id: str, quant: str):
    import torch
    from transformers import AutoModelForCausalLM, AutoTokenizer

    info: dict[str, Any] = {"quant_requested": quant, "model_id": model_id}
    tok = AutoTokenizer.from_pretrained(model_id, trust_remote_code=True)
    kwargs: dict[str, Any] = {
        "trust_remote_code": True,
        "device_map": {"": 0} if quant in ("4bit", "8bit", "auto") else "auto",
    }
    if quant == "4bit" or (quant == "auto" and torch.cuda.is_available()):
        from transformers import BitsAndBytesConfig

        kwargs["quantization_config"] = BitsAndBytesConfig(
            load_in_4bit=True,
            bnb_4bit_compute_dtype=torch.float16,
            bnb_4bit_use_double_quant=True,
            bnb_4bit_quant_type="nf4",
        )
        info["quant_applied"] = "4bit-nf4" if quant == "4bit" else "4bit-nf4 (auto)"
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
        kwargs["torch_dtype"] = torch.float32
        kwargs["device_map"] = "cpu"
        info["quant_applied"] = "fp32-cpu"

    model = AutoModelForCausalLM.from_pretrained(model_id, **kwargs)
    model.eval()
    info["cuda"] = bool(torch.cuda.is_available())
    if torch.cuda.is_available():
        info["gpu_name"] = torch.cuda.get_device_name(0)
        info["vram_alloc_gb"] = round(torch.cuda.memory_allocated(0) / 1024**3, 3)
    return tok, model, info


def _attach_adapter(model, adapter_path: str):
    from peft import PeftModel

    model = PeftModel.from_pretrained(model, adapter_path)
    model.eval()
    info: dict[str, Any] = {"adapter_path": adapter_path, "adapter_loaded": True}
    try:
        cfg = getattr(model, "peft_config", None)
        if cfg:
            first = next(iter(cfg.values())) if isinstance(cfg, dict) else cfg
            info["peft_type"] = str(getattr(first, "peft_type", type(first).__name__))
            info["r"] = getattr(first, "r", None)
            info["lora_alpha"] = getattr(first, "lora_alpha", None)
    except Exception as exc:  # noqa: BLE001
        info["peft_meta_error"] = f"{type(exc).__name__}: {exc}"
    return model, info


def get_model_meta() -> dict[str, Any] | None:
    """Return load metadata for the cached model, if any."""
    return _cache.get("meta")


def unload() -> None:
    """Drop the cached tokenizer/model (frees GPU memory best-effort)."""
    with _lock:
        _cache["key"] = None
        _cache["tok"] = None
        _cache["model"] = None
        _cache["meta"] = None
        try:
            import torch

            if torch.cuda.is_available():
                torch.cuda.empty_cache()
        except Exception:
            pass


def _ensure_loaded(
    model_path: str | Path | None,
    adapter_path: str | Path | None,
    quant: str,
) -> tuple[Any, Any, dict[str, Any]]:
    mid = resolve_model_path(model_path)
    adap = resolve_adapter_path(adapter_path)
    if adap is not None and not _adapter_ready(adap):
        raise FileNotFoundError(
            f"Adapter path {adap!r} is missing adapter_config.json / weights. "
            "Copy outputs/lora_tables_win_v3 into models/lora_tables/ or set "
            "CBT_QWEN_ADAPTER."
        )
    key = f"{mid}|{adap or ''}|{quant}"
    with _lock:
        if _cache["key"] == key and _cache["model"] is not None:
            return _cache["tok"], _cache["model"], _cache["meta"]
        # Different key: drop old weights before loading new ones.
        _cache["tok"] = None
        _cache["model"] = None
        _cache["meta"] = None
        _cache["key"] = None

        tok, model, info = _load_base(mid, quant)
        info["adapter"] = adap or "(none — base only)"
        if adap:
            model, ainfo = _attach_adapter(model, adap)
            info.update(ainfo)
            try:
                import torch

                if torch.cuda.is_available():
                    info["vram_alloc_gb_after_adapter"] = round(
                        torch.cuda.memory_allocated(0) / 1024**3, 3
                    )
            except Exception:
                pass

        _cache["key"] = key
        _cache["tok"] = tok
        _cache["model"] = model
        _cache["meta"] = info
        return tok, model, info


def _generate(
    tok,
    model,
    braille: str,
    *,
    max_new_tokens: int,
    repetition_penalty: float,
    context: str | None = None,
    cell_mode: bool = False,
) -> str:
    import torch

    messages = _build_messages(braille, context, cell_mode=cell_mode)
    prompt = tok.apply_chat_template(
        messages, tokenize=False, add_generation_prompt=True
    )
    inputs = tok(prompt, return_tensors="pt")
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
            do_sample=False,
            repetition_penalty=repetition_penalty,
            pad_token_id=tok.eos_token_id,
        )
    raw = tok.decode(out[0][input_len:], skip_special_tokens=True)
    if cell_mode or _is_short_cell(braille):
        return _finalize_cell_output(raw)
    return _strip_assistant_prefix(raw)


def _scaffold(braille: str, context: str | None) -> str:
    ctx = f" context={context!r}" if context else ""
    preview = braille if len(braille) <= 80 else braille[:77] + "..."
    return f"[scaffold-qwen8b]{ctx} input={preview!r}"



def _cell_token_budget(braille: str, cap: int) -> int:
    """Shorter cells need fewer new tokens; EOS usually stops earlier anyway."""
    n = _braille_compact_len(braille)
    # Tight caps for headers like 单价 / 商品 — long budgets invite pipe hallucinations.
    if n <= 4:
        return min(8, cap)
    if n <= 8:
        return min(12, cap)
    if n <= 12:
        return min(16, cap)
    if n <= 20:
        return min(32, cap)
    return cap


def translate_batch(
    brailles: list[str],
    context: str | None = None,
    *,
    adapter_path: str | Path | None = None,
    model_path: str | Path | None = None,
    quant: str = "4bit",
    max_new_tokens: int = 32,
    repetition_penalty: float = 1.15,
    batch_size: int = 8,
) -> list[str]:
    """Translate many braille strings in one or more batched generate() calls.

    Empty / whitespace-only inputs become "" without calling the model.
    Falls back to sequential translate() when batching is unavailable.
    """
    if not brailles:
        return []

    out: list[str | None] = [None] * len(brailles)
    pending_idx: list[int] = []
    pending_text: list[str] = []
    for i, br in enumerate(brailles):
        s = (br or "").strip()
        if not s:
            out[i] = ""
        else:
            pending_idx.append(i)
            pending_text.append(s)

    if not pending_text:
        return [x or "" for x in out]

    if _want_stub() or not (_cuda_ok() or _allow_cpu()):
        for i, s in zip(pending_idx, pending_text):
            out[i] = _scaffold(s, context)
        return [x or "" for x in out]

    try:
        import torch
        from transformers import AutoModelForCausalLM  # noqa: F401
    except ImportError:
        for i, s in zip(pending_idx, pending_text):
            out[i] = translate(
                s,
                context=context,
                adapter_path=adapter_path,
                model_path=model_path,
                quant=quant,
                max_new_tokens=max_new_tokens,
                repetition_penalty=repetition_penalty,
            )
        return [x or "" for x in out]

    q = quant
    if not _cuda_ok() and q in ("4bit", "8bit", "auto"):
        q = "fp16" if _allow_cpu() else q

    tok, model, _meta = _ensure_loaded(model_path, adapter_path, q)

    prev_side = getattr(tok, "padding_side", "right")
    tok.padding_side = "left"
    if tok.pad_token_id is None:
        tok.pad_token = tok.eos_token

    try:
        dev = next(model.parameters()).device
    except StopIteration:
        dev = torch.device("cuda" if torch.cuda.is_available() else "cpu")

    bs = max(1, int(batch_size or 8))
    try:
        for start in range(0, len(pending_text), bs):
            chunk = pending_text[start : start + bs]
            chunk_idx = pending_idx[start : start + bs]
            prompts = []
            budgets = []
            for br in chunk:
                messages = _build_messages(br, context, cell_mode=True)
                prompts.append(
                    tok.apply_chat_template(
                        messages, tokenize=False, add_generation_prompt=True
                    )
                )
                budgets.append(_cell_token_budget(br, max_new_tokens))
            inputs = tok(prompts, return_tensors="pt", padding=True)
            inputs = {k: v.to(dev) for k, v in inputs.items()}
            input_len = inputs["input_ids"].shape[1]
            gen_tok = max(budgets) if budgets else max_new_tokens
            with torch.no_grad():
                gen = model.generate(
                    **inputs,
                    max_new_tokens=gen_tok,
                    do_sample=False,
                    repetition_penalty=repetition_penalty,
                    pad_token_id=tok.pad_token_id,
                    eos_token_id=tok.eos_token_id,
                    use_cache=True,
                )
            for row_i, orig_i in enumerate(chunk_idx):
                raw = tok.decode(gen[row_i][input_len:], skip_special_tokens=True)
                out[orig_i] = _finalize_cell_output(raw)
    except Exception:
        for i, s in zip(pending_idx, pending_text):
            if out[i] is None:
                out[i] = translate(
                    s,
                    context=context,
                    adapter_path=adapter_path,
                    model_path=model_path,
                    quant=quant,
                    max_new_tokens=_cell_token_budget(s, max_new_tokens),
                    repetition_penalty=repetition_penalty,
                )
    finally:
        tok.padding_side = prev_side

    return [x or "" for x in out]


def translate(
    braille: str,
    context: str | None = None,
    *,
    adapter_path: str | Path | None = None,
    model_path: str | Path | None = None,
    quant: str = "4bit",
    max_new_tokens: int = 128,
    repetition_penalty: float = 1.15,
) -> str:
    """Translate Chinese braille to Han via Vision-Braille-Qwen3-8B (+ LoRA).

    Parameters
    ----------
    braille:
        Unicode / ASCII braille string.
    context:
        Reserved for future prompt conditioning; currently unused by the
        chat template (kept for API parity with ``mt5``).
    adapter_path:
        Optional PEFT adapter directory. Default: env ``CBT_QWEN_ADAPTER``
        or ``models/lora_tables`` when present. Pass ``\"\"`` to force base-only.
    model_path:
        Optional base model directory / HF id. Default: env ``CBT_QWEN_MODEL``
        or ``models/Vision-Braille-Qwen3-8B``.
    quant:
        ``4bit`` (default, ~8GB VRAM) | ``8bit`` | ``bf16`` | ``fp16`` | ``auto``.
    max_new_tokens:
        Generation length cap (default 128; short cells usually finish earlier via EOS).
    repetition_penalty:
        Greedy decode repetition penalty (eval default 1.15).
    """
    # context is injected into short-cell / table-cell prompts
    if _want_stub():
        return _scaffold(braille, context)

    can_run = _cuda_ok() or _allow_cpu()
    if not can_run:
        return _scaffold(braille, context)

    try:
        import torch  # noqa: F401
        from transformers import AutoModelForCausalLM  # noqa: F401
    except ImportError as exc:
        raise ImportError(
            "qwen8b backend needs torch + transformers. "
            'Install with: pip install -e ".[qwen]" '
            "(and peft/bitsandbytes for LoRA + 4-bit)."
        ) from exc

    adap = resolve_adapter_path(adapter_path)
    if adap is not None:
        try:
            from peft import PeftModel  # noqa: F401
        except ImportError as exc:
            raise ImportError(
                "LoRA adapter requested but peft is not installed. "
                'pip install peft  (or pip install -e ".[train]")'
            ) from exc

    if not _cuda_ok() and quant in ("4bit", "8bit", "auto"):
        quant = "fp16" if _allow_cpu() else quant

    tok, model, _meta = _ensure_loaded(model_path, adapter_path, quant)
    cell_mode = _is_short_cell(braille)
    return _generate(
        tok,
        model,
        braille,
        max_new_tokens=_cell_token_budget(braille, max_new_tokens),
        repetition_penalty=repetition_penalty,
        context=context,
        cell_mode=cell_mode,
    )
