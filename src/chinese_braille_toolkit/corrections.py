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
            "已合并纠错样本到训练集。"
            "推荐在网页点「一键重训」（需 CBT_ALLOW_RETRAIN=1 + CUDA）；"
            "或运行 scripts\\windows\\retrain_from_corrections.ps1。"
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


# ---------------------------------------------------------------------------
# One-click retrain job (background subprocess + status file)
# ---------------------------------------------------------------------------

ADAPTER_DEST = ROOT / "models" / "lora_tables"
_job_lock = threading.Lock()
_job_proc: Any = None  # subprocess.Popen | None
_job_meta: dict[str, Any] = {}


def _pid_alive(pid: int) -> bool:
    if pid <= 0:
        return False
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    except OSError:
        # Windows may raise OSError for nonexistent pid
        try:
            import ctypes

            kernel32 = ctypes.windll.kernel32  # type: ignore[attr-defined]
            handle = kernel32.OpenProcess(0x1000, False, int(pid))  # PROCESS_QUERY_LIMITED_INFORMATION
            if handle:
                kernel32.CloseHandle(handle)
                return True
            return False
        except Exception:  # noqa: BLE001
            return False
    return True


def retrain_gate(*, allow_without_user_corrections: bool = False) -> dict[str, Any]:
    """Decide whether one-click retrain may start.

    Default: need ≥1 user correction. With confirmation flag, allow existing
    merged train file or holdout error corrections (after merge).
    Raises ValueError with a Chinese message when blocked.
    """
    stats = correction_stats()
    user_n = int(stats["user_corrections"])
    err_n = int(stats["error_corrections"])
    merged_n = int(stats["train_tables_with_errors"])
    if user_n >= 1:
        return {**stats, "ok": True, "gate": "user_corrections"}
    has_fallback = merged_n >= 1 or err_n >= 1 or int(stats["train_tables"]) >= 1
    if has_fallback and allow_without_user_corrections:
        return {**stats, "ok": True, "gate": "merged_or_holdout"}
    if has_fallback:
        raise ValueError(
            "尚无网页纠错样本。若确认仅用已有训练集/holdout 再训，"
            "请传 allow_without_user_corrections=true。"
        )
    raise ValueError("请先在网页保存至少 1 条纠错，再点「一键重训」。")


def is_retrain_running() -> bool:
    """True if a background retrain process is still alive."""
    with _job_lock:
        proc = _job_proc
        if proc is not None and proc.poll() is None:
            return True
    st = read_retrain_status()
    if st.get("state") == "running":
        pid = st.get("pid")
        if isinstance(pid, int) and _pid_alive(pid):
            return True
    return False


def copy_adapter_to_models(
    src: Path | None = None,
    dest: Path | None = None,
) -> dict[str, Any]:
    """Copy PEFT adapter files into models/lora_tables (or configured dest)."""
    import shutil

    source = Path(src) if src else (ROOT / "outputs" / "lora_tables_from_corrections")
    target = Path(dest) if dest else ADAPTER_DEST
    if not source.is_dir():
        raise FileNotFoundError(f"训练输出目录不存在: {source}")
    cfg = source / "adapter_config.json"
    if not cfg.is_file():
        raise FileNotFoundError(f"未找到 adapter_config.json: {cfg}")
    weight = source / "adapter_model.safetensors"
    weight_bin = source / "adapter_model.bin"
    if not weight.is_file() and not weight_bin.is_file():
        raise FileNotFoundError(
            f"未找到 adapter_model.safetensors / .bin: {source}"
        )
    target.mkdir(parents=True, exist_ok=True)
    copied: list[str] = []
    for name in (
        "adapter_config.json",
        "adapter_model.safetensors",
        "adapter_model.bin",
        "README.md",
        "training_args.bin",
    ):
        p = source / name
        if p.is_file():
            shutil.copy2(p, target / name)
            copied.append(name)
    # Also copy any adapter_* extras
    for p in source.glob("adapter_*"):
        if p.is_file() and p.name not in copied:
            shutil.copy2(p, target / p.name)
            copied.append(p.name)
    return {
        "ok": True,
        "src": _rel(source),
        "dest": _rel(target),
        "copied": copied,
    }


def _tail_log(path: Path, max_chars: int = 2400) -> str:
    if not path.is_file():
        return ""
    try:
        data = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""
    return data[-max_chars:] if len(data) > max_chars else data


def _parse_progress(log_tail: str, max_steps: int | None) -> dict[str, Any]:
    """Best-effort step progress from Trainer log lines."""
    import re

    step = None
    # Common patterns: "Step 40/80", "'loss': 0.12, 'epoch':", "global_step=40"
    for pat in (
        r"[Ss]tep\s+(\d+)\s*/\s*(\d+)",
        r"global_step[=:\s]+(\d+)",
        r"'\s*loss\s*'[^\}]*?(\d+)\s*/\s*(\d+)",
        r"(\d+)\s*/\s*(\d+)\s*\[",
    ):
        matches = list(re.finditer(pat, log_tail))
        if matches:
            m = matches[-1]
            try:
                step = int(m.group(1))
                if m.lastindex and m.lastindex >= 2:
                    max_steps = int(m.group(2))
            except (ValueError, IndexError):
                pass
            break
    out: dict[str, Any] = {}
    if step is not None:
        out["step"] = step
        if max_steps:
            out["max_steps"] = max_steps
            out["progress_pct"] = round(100.0 * min(step, max_steps) / max_steps, 1)
    return out


def refresh_retrain_status() -> dict[str, Any]:
    """Refresh running/finished state from process + log; return status dict."""
    st = read_retrain_status()
    state = st.get("state") or "idle"
    log_path = Path(st["log_path"]) if st.get("log_path") else (OUTPUTS_DIR / "retrain_api.log")
    if not log_path.is_absolute():
        log_path = ROOT / log_path
    tail = _tail_log(log_path)
    if state == "running":
        pid = st.get("pid")
        alive = isinstance(pid, int) and _pid_alive(pid)
        with _job_lock:
            proc = _job_proc
        if proc is not None:
            code = proc.poll()
            if code is not None:
                alive = False
                st["returncode"] = code
            else:
                alive = True
        prog = _parse_progress(tail, st.get("max_steps"))
        st.update(prog)
        st["log_tail"] = tail[-1200:] if tail else ""
        if not alive and "returncode" not in st:
            # Process gone but watcher may not have finished — mark unknown
            st["state"] = "running"
            st["message"] = st.get("message") or "训练进程已结束，正在结算…"
        elif alive:
            pct = st.get("progress_pct")
            step = st.get("step")
            ms = st.get("max_steps")
            if step is not None and ms:
                st["message"] = f"训练中… 第 {step}/{ms} 步" + (
                    f"（{pct}%）" if pct is not None else ""
                )
            else:
                st["message"] = st.get("message") or "训练进行中…"
        write_retrain_status(st)
        return st
    if state in {"succeeded", "failed", "dry_run_done", "idle", "unknown"}:
        if tail and "log_tail" not in st:
            st["log_tail"] = tail[-1200:]
        return st
    return st


def _finish_retrain_job(
    *,
    returncode: int,
    hp: dict[str, Any],
    copy_to_models: bool,
    hot_reload: bool,
    log_path: Path,
) -> None:
    tail = _tail_log(log_path)
    out_dir = ROOT / str(hp.get("output_dir") or "outputs/lora_tables_from_corrections")
    status: dict[str, Any] = {
        "state": "succeeded" if returncode == 0 else "failed",
        "returncode": returncode,
        "log_path": str(log_path),
        "output_dir": _rel(out_dir),
        "max_steps": hp.get("max_steps"),
        "log_tail": tail[-2000:] if tail else "",
        "copy_to_models": copy_to_models,
        "hot_reload": hot_reload,
    }
    if returncode != 0:
        status["message"] = f"再训失败（退出码 {returncode}）。请查看 outputs/retrain_api.log。"
        write_retrain_status(status)
        return

    status["message"] = "再训完成。"
    if copy_to_models:
        try:
            copied = copy_adapter_to_models(out_dir, ADAPTER_DEST)
            status["adapter_copy"] = copied
            status["message"] = (
                "再训完成，已复制适配器到 models/lora_tables。"
            )
        except Exception as exc:  # noqa: BLE001
            status["adapter_copy_error"] = f"{type(exc).__name__}: {exc}"
            status["message"] = (
                f"再训完成，但复制适配器失败：{exc}。"
                "请手动复制 outputs/lora_tables_from_corrections → models/lora_tables。"
            )

    if hot_reload:
        try:
            from chinese_braille_toolkit.backends import qwen8b as qwen_backend

            qwen_backend.unload()
            status["hot_reload_done"] = True
            status["message"] += " 已卸载旧模型，下次翻译将加载新适配器（无需重启 API）。"
        except Exception as exc:  # noqa: BLE001
            status["hot_reload_error"] = f"{type(exc).__name__}: {exc}"
            status["message"] += " 热加载失败，请重启 API。"
    else:
        status["message"] += " 请重启 API 以加载新适配器。"

    write_retrain_status(status)


def start_retrain_job(
    *,
    max_steps: int | None = None,
    dry_run: bool = False,
    copy_to_models: bool = True,
    hot_reload: bool = True,
    allow_without_user_corrections: bool = False,
    include_user: bool = True,
    include_holdout_errors: bool = True,
    python_exe: str | None = None,
) -> dict[str, Any]:
    """Merge corrections and start background QLoRA train (or dry-run sync).

    Raises ValueError / PermissionError / RuntimeError with Chinese messages.
    """
    import subprocess
    import sys as _sys

    global _job_proc, _job_meta

    if not retrain_allowed():
        raise PermissionError(
            "未开启再训。请设环境变量 CBT_ALLOW_RETRAIN=1"
            "（Start-BrailleApi.bat 已默认开启），"
            "或改用「准备再训」+ 本机 PowerShell 脚本。"
        )
    if is_retrain_running():
        raise RuntimeError("已有再训任务在运行，请等待完成后再试。")
    if not dry_run and not cuda_available():
        raise RuntimeError(
            "未检测到 CUDA，拒绝启动训练。请在 Windows GPU 机器上用 "
            "Start-BrailleApi.bat 启动，或先 dry_run。"
        )

    gate = retrain_gate(allow_without_user_corrections=allow_without_user_corrections)
    mr = merge_into_train(
        include_user=include_user,
        include_holdout_errors=include_holdout_errors,
    )
    prep = write_retrain_request(mr, max_steps=max_steps)
    hp = prep["hyperparams"]

    py = python_exe or _sys.executable
    cmd = [
        py,
        str(ROOT / "scripts" / "train_lora_tables.py"),
        "--config",
        str(ROOT / hp["config"]),
        "--data-path",
        str(ROOT / hp["data_path"]),
        "--output-dir",
        str(ROOT / hp["output_dir"]),
        "--bits",
        str(hp["bits"]),
        "--max-steps",
        str(hp["max_steps"]),
        "--optim",
        str(hp["optim"]),
        "--logging-steps",
        str(hp["logging_steps"]),
    ]
    if dry_run:
        cmd.append("--dry-run")

    log_path = OUTPUTS_DIR / "retrain_api.log"
    OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)

    if dry_run:
        try:
            proc = subprocess.run(
                cmd,
                cwd=str(ROOT),
                capture_output=True,
                text=True,
                timeout=120,
                check=False,
            )
        except Exception as exc:  # noqa: BLE001
            raise RuntimeError(f"dry-run 启动失败: {exc}") from exc
        status = {
            "state": "dry_run_done",
            "returncode": proc.returncode,
            "cmd": cmd,
            "stdout_tail": (proc.stdout or "")[-2000:],
            "stderr_tail": (proc.stderr or "")[-2000:],
            "message": "dry-run 完成（未真正训练）",
            "gate": gate.get("gate"),
            "merge": mr,
        }
        write_retrain_status(status)
        return status

    with _job_lock:
        try:
            log_f = open(log_path, "a", encoding="utf-8")
            log_f.write(f"\n--- start {_shanghai_iso()} ---\n")
            log_f.write(" ".join(cmd) + "\n")
            log_f.flush()
            proc = subprocess.Popen(
                cmd,
                cwd=str(ROOT),
                stdout=log_f,
                stderr=subprocess.STDOUT,
                start_new_session=True,
            )
        except Exception as exc:  # noqa: BLE001
            raise RuntimeError(f"无法启动训练进程: {exc}") from exc
        _job_proc = proc
        _job_meta = {
            "pid": proc.pid,
            "hp": hp,
            "copy_to_models": copy_to_models,
            "hot_reload": hot_reload,
            "log_path": str(log_path),
        }

    status = {
        "state": "running",
        "pid": proc.pid,
        "cmd": cmd,
        "log_path": str(log_path),
        "output_dir": hp["output_dir"],
        "max_steps": hp["max_steps"],
        "copy_to_models": copy_to_models,
        "hot_reload": hot_reload,
        "gate": gate.get("gate"),
        "merge": mr,
        "message": (
            f"已启动一键重训 PID={proc.pid}（最多 {hp['max_steps']} 步）。"
            "请稍候，进度会自动刷新。"
        ),
    }
    write_retrain_status(status)

    def _watcher() -> None:
        code = proc.wait()
        try:
            log_f.close()
        except Exception:  # noqa: BLE001
            pass
        with _job_lock:
            global _job_proc
            if _job_proc is proc:
                _job_proc = None
        _finish_retrain_job(
            returncode=code,
            hp=hp,
            copy_to_models=copy_to_models,
            hot_reload=hot_reload,
            log_path=log_path,
        )

    threading.Thread(target=_watcher, name="cbt-retrain-watch", daemon=True).start()
    return status
