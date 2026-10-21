"""User / holdout error corrections → ShareGPT JSONL for table LoRA retrain.

Persists under ``data/user_corrections.jsonl`` and can merge (dedupe by
braille+zh) into ``data/train_tables_with_errors.jsonl``.
"""

from __future__ import annotations

import json
import os
import threading
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = ROOT / "data"
USER_CORRECTIONS = DATA_DIR / "user_corrections.jsonl"
ERROR_CORRECTIONS = DATA_DIR / "error_corrections.jsonl"
TRAIN_TABLES = DATA_DIR / "train_tables.jsonl"
MERGED_TRAIN = DATA_DIR / "train_tables_with_errors.jsonl"
OUTPUTS_DIR = ROOT / "outputs"
RETRAIN_REQUEST = OUTPUTS_DIR / "retrain_request.json"
RETRAIN_STATUS = OUTPUTS_DIR / "retrain_status.json"

SYSTEM = "你是一个中国盲文翻译助手，请把通用盲文转换成为汉字。"
USER_TMPL = "请把以下通用盲文转换成为汉字：\n盲文内容是:\n{braille}"
ASSIST_TMPL = "对应的中文内容是：\n{zh}"

_lock = threading.Lock()


def _shanghai_iso() -> str:
    """Return Asia/Shanghai wall time as ISO string with +08:00."""
    try:
        from zoneinfo import ZoneInfo

        return datetime.now(ZoneInfo("Asia/Shanghai")).isoformat(timespec="seconds")
    except Exception:  # noqa: BLE001
        # Fallback: UTC+8 fixed offset
        from datetime import timedelta

        tz = timezone(timedelta(hours=8), name="Asia/Shanghai")
        return datetime.now(tz).isoformat(timespec="seconds")


def build_correction_record(
    *,
    braille: str,
    zh: str,
    pred: str | None = None,
    context: str | None = None,
    row: int | None = None,
    col: int | None = None,
    table_id: str | None = None,
    sample_id: str | None = None,
    kind: str = "cell",
    meta: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build one ShareGPT-compatible correction row."""
    br = (braille or "").strip()
    corrected = (zh or "").strip()
    if not br:
        raise ValueError("braille 不能为空")
    if not corrected:
        raise ValueError("纠正后的汉字不能为空")
    if pred is not None and corrected == str(pred).strip():
        raise ValueError("纠正后的汉字与原预测相同，无需保存")

    sid = sample_id or (
        f"user-{table_id or 'web'}-r{row}-c{col}"
        if row is not None and col is not None
        else f"user-{uuid.uuid4().hex[:10]}"
    )
    note_parts = ["web user correction"]
    if pred is not None:
        note_parts.append(f"was pred={pred!r}")
    if context:
        note_parts.append(f"context={context!r}")
    if row is not None and col is not None:
        note_parts.append(f"cell=r{row}-c{col}")

    record: dict[str, Any] = {
        "id": f"userfix-{sid}",
        "kind": kind or "cell",
        "table_id": table_id or "web",
        "conversations": [
            {"from": "system", "value": SYSTEM},
            {"from": "human", "value": USER_TMPL.format(braille=br)},
            {"from": "gpt", "value": ASSIST_TMPL.format(zh=corrected)},
        ],
        "braille": br,
        "zh": corrected,
        "note": "; ".join(note_parts),
        "source_pred": pred,
        "source_sample_id": sid,
        "context": context,
        "row": row,
        "col": col,
        "timestamp": _shanghai_iso(),
    }
    if meta:
        record["meta"] = meta
    return record



def _rel(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(ROOT.resolve()))
    except ValueError:
        return str(path)

def _ensure_parent(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


def append_correction(
    record: dict[str, Any],
    path: Path | None = None,
) -> dict[str, Any]:
    """Append one correction JSONL line. Returns stats after write."""
    target = path or USER_CORRECTIONS
    _ensure_parent(target)
    line = json.dumps(record, ensure_ascii=False)
    with _lock:
        with target.open("a", encoding="utf-8") as f:
            f.write(line + "\n")
        n = _count_jsonl(target)
    return {"ok": True, "path": _rel(target), "count": n, "id": record.get("id")}


def _count_jsonl(path: Path) -> int:
    if not path.is_file():
        return 0
    n = 0
    with path.open(encoding="utf-8") as f:
        for line in f:
            if line.strip():
                n += 1
    return n


def _load_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.is_file():
        return []
    rows: list[dict[str, Any]] = []
    with path.open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return rows


def correction_stats() -> dict[str, Any]:
    """Counts for user / holdout / merged train sets."""
    user_n = _count_jsonl(USER_CORRECTIONS)
    err_n = _count_jsonl(ERROR_CORRECTIONS)
    train_n = _count_jsonl(TRAIN_TABLES)
    merged_n = _count_jsonl(MERGED_TRAIN)
    return {
        "user_corrections": user_n,
        "error_corrections": err_n,
        "train_tables": train_n,
        "train_tables_with_errors": merged_n,
        "user_path": _rel(USER_CORRECTIONS),
        "merged_path": _rel(MERGED_TRAIN),
    }


def merge_into_train(
    *,
    include_user: bool = True,
    include_holdout_errors: bool = True,
    train_path: Path | None = None,
    out_path: Path | None = None,
) -> dict[str, Any]:
    """Merge base train + corrections into ``train_tables_with_errors.jsonl``.

    Dedupes by (braille, zh). Later sources win order but duplicates are skipped.
    """
    base = train_path or TRAIN_TABLES
    out = out_path or MERGED_TRAIN
    train = _load_jsonl(base)
    extras: list[dict[str, Any]] = []
    if include_holdout_errors:
        extras.extend(_load_jsonl(ERROR_CORRECTIONS))
    if include_user:
        extras.extend(_load_jsonl(USER_CORRECTIONS))

    seen: set[tuple[str, str]] = set()
    merged: list[dict[str, Any]] = []
    dupes = 0
    for row in train + extras:
        key = (str(row.get("braille") or ""), str(row.get("zh") or ""))
        if not key[0] or not key[1]:
            continue
        if key in seen:
            dupes += 1
            continue
        seen.add(key)
        merged.append(row)

    _ensure_parent(out)
    with _lock:
        out.write_text(
            "\n".join(json.dumps(r, ensure_ascii=False) for r in merged) + ("\n" if merged else ""),
            encoding="utf-8",
        )

    return {
        "ok": True,
        "train": len(train),
        "extras": len(extras),
        "merged": len(merged),
        "dupes_skipped": dupes,
        "user_corrections": _count_jsonl(USER_CORRECTIONS) if include_user else 0,
        "error_corrections": _count_jsonl(ERROR_CORRECTIONS) if include_holdout_errors else 0,
        "out_path": _rel(out),
    }


def default_retrain_hyperparams(*, max_steps: int | None = None) -> dict[str, Any]:
    """Short continue-train defaults for correction fine-tune."""
    steps = max_steps if max_steps is not None else int(os.environ.get("CBT_RETRAIN_MAX_STEPS") or "80")
    return {
        "config": "configs/lora_tables.yaml",
        "data_path": "data/train_tables_with_errors.jsonl",
        "output_dir": "outputs/lora_tables_from_corrections",
        "resume_adapter": "models/lora_tables",
        "bits": 4,
        "max_steps": max(20, min(steps, 400)),
        "learning_rate": 1.0e-4,
        "optim": "adamw_torch",
        "logging_steps": 5,
        "per_device_train_batch_size": 1,
        "gradient_accumulation_steps": 8,
    }


def write_retrain_request(
    merge_result: dict[str, Any] | None = None,
    *,
    max_steps: int | None = None,
) -> dict[str, Any]:
    """Merge (if needed) + write ``outputs/retrain_request.json`` with commands."""
    mr = merge_result or merge_into_train()
    hp = default_retrain_hyperparams(max_steps=max_steps)
    OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)

    ps1 = (
        "powershell -ExecutionPolicy Bypass -File "
        "scripts\\windows\\retrain_from_corrections.ps1"
    )
    py_cmd = (
        f'.venv-qwen\\Scripts\\python.exe scripts\\train_lora_tables.py '
        f'--config {hp["config"]} '
        f'--data-path {hp["data_path"]} '
        f'--output-dir {hp["output_dir"]} '
        f'--bits {hp["bits"]} '
        f'--max-steps {hp["max_steps"]} '
        f'--optim {hp["optim"]} '
        f'--logging-steps {hp["logging_steps"]}'
    )
    # Note: continue from current adapter is documented; train script uses
    # --resume-from-checkpoint for HF trainer ckpts. For PEFT adapter continue,
    # the Windows script copies / points CBT_ADAPTER / peft load as needed.

    payload = {
        "created_at": _shanghai_iso(),
        "timezone": "Asia/Shanghai",
        "merge": mr,
        "hyperparams": hp,
        "commands": {
            "powershell_one_liner": ps1,
            "python_train": py_cmd,
            "after_train_copy": (
                "训练结束后，将 outputs\\lora_tables_from_corrections 中的 "
                "adapter_config.json / adapter_model.safetensors 复制到 "
                "models\\lora_tables\\（或设置 CBT_ADAPTER_PATH），然后重启 API。"
            ),
        },
        "notes_zh": (
            "已合并纠错样本到训练集。请在本机 Windows CUDA 环境运行再训脚本；"
            "API 主机若无 GPU，勿依赖 POST /v1/retrain。"
        ),
    }
    RETRAIN_REQUEST.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    payload["request_path"] = _rel(RETRAIN_REQUEST)
    return payload


def read_retrain_status() -> dict[str, Any]:
    if not RETRAIN_STATUS.is_file():
        return {"state": "idle", "message": "尚无再训任务"}
    try:
        return json.loads(RETRAIN_STATUS.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {"state": "unknown", "message": "状态文件损坏"}


def write_retrain_status(data: dict[str, Any]) -> None:
    OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)
    data = {**data, "updated_at": _shanghai_iso()}
    RETRAIN_STATUS.write_text(
        json.dumps(data, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def retrain_allowed() -> bool:
    return (os.environ.get("CBT_ALLOW_RETRAIN") or "").strip().lower() in {
        "1",
        "true",
        "yes",
        "on",
    }


def cuda_available() -> bool:
    try:
        import torch

        return bool(torch.cuda.is_available())
    except Exception:  # noqa: BLE001
        return False
