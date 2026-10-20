#!/usr/bin/env python3
"""中文盲文翻译演示 — Gradio Web UI.

从项目根目录启动（Windows，推荐 GPU 虚拟环境）::

    .venv-qwen\\Scripts\\python.exe apps\\gradio_demo.py

浏览器打开 http://127.0.0.1:7860
"""

from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path

# Ensure editable package is importable when run as a script from repo root.
_REPO = Path(__file__).resolve().parents[1]
_SRC = _REPO / "src"
if _SRC.is_dir() and str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

os.chdir(_REPO)

try:
    import gradio as gr
except ImportError as exc:  # pragma: no cover
    raise SystemExit(
        "未安装 Gradio。请执行: pip install -e \".[demo]\"  或  pip install \"gradio>=4.0\""
    ) from exc

from chinese_braille_toolkit import translate  # noqa: E402
from chinese_braille_toolkit.backends import qwen8b as qwen_backend  # noqa: E402

TABLES_PATH = _REPO / "data" / "synthetic_tables" / "tables.jsonl"
DEFAULT_PORT = int(os.environ.get("CBT_WEBUI_PORT", "7860"))

APP_CSS = """
.gradio-container { max-width: 920px !important; }
#status-box textarea { font-family: ui-monospace, Consolas, monospace; font-size: 13px; }
"""

# Curated holdout cells for one-click fill (braille, expected zh, label).
SAMPLE_CELLS: list[tuple[str, str, str]] = [
    ("⠓⠊⠼ ⠍⠊⠼⠂", "姓名", "成绩表·表头「姓名」"),
    ("⠬ ⠒", "语文", "成绩表·表头「语文」"),
    ("⠌⠦ ⠎⠧⠁", "张三", "成绩表·姓名「张三」"),
    ("⠱⠦ ⠏⠊⠴", "商品", "销售表·表头「商品」"),
    ("⠙⠧ ⠛⠫⠆", "单价", "销售表·表头「单价」"),
]


def _load_extra_samples_from_jsonl(limit: int = 5) -> list[tuple[str, str, str]]:
    """Fallback / supplement from tables.jsonl if curated list is short."""
    out: list[tuple[str, str, str]] = []
    if not TABLES_PATH.is_file():
        return out
    try:
        for line in TABLES_PATH.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            obj = json.loads(line)
            title = obj.get("title_zh") or obj.get("id") or "样例"
            for row in obj.get("cells") or []:
                for cell in row:
                    zh = (cell.get("zh") or "").strip()
                    br = (cell.get("braille") or "").strip()
                    if zh and br:
                        out.append((br, zh, f"{title}·{zh}"))
                        if len(out) >= limit:
                            return out
    except Exception:  # noqa: BLE001
        pass
    return out


def _samples() -> list[tuple[str, str, str]]:
    if SAMPLE_CELLS:
        return SAMPLE_CELLS
    return _load_extra_samples_from_jsonl(5)


def probe_status() -> str:
    """Human-readable runtime status (CUDA / adapter / stub)."""
    lines: list[str] = []
    stub_env = (os.environ.get("CBT_QWEN_STUB") or "").strip()
    if stub_env in {"1", "true", "yes", "on"}:
        lines.append("模式: 强制脚手架 (CBT_QWEN_STUB=1) — 不会加载真模型")
    else:
        lines.append("模式: 正常推理（有 CUDA + 权重时加载 Qwen）")

    cuda = False
    gpu_name = ""
    try:
        import torch

        cuda = bool(torch.cuda.is_available())
        if cuda:
            gpu_name = torch.cuda.get_device_name(0)
    except Exception as exc:  # noqa: BLE001
        lines.append(f"PyTorch: 不可用 ({type(exc).__name__})")
    else:
        lines.append(f"CUDA: {'可用 — ' + gpu_name if cuda else '不可用（将走脚手架或 CPU）'}")

    adap = qwen_backend.resolve_adapter_path(None)
    if adap:
        ap = Path(adap)
        ready = (ap / "adapter_config.json").is_file() and (
            (ap / "adapter_model.safetensors").is_file()
            or (ap / "adapter_model.bin").is_file()
        )
        if ready:
            lines.append(f"默认适配器: 已找到 — {adap}")
        else:
            lines.append(f"默认适配器: 路径存在但权重不完整 — {adap}")
    else:
        lines.append("默认适配器: 未配置（将用基座或脚手架）")

    model = qwen_backend.resolve_model_path(None)
    lines.append(f"基座路径/ID: {model}")

    meta = qwen_backend.get_model_meta()
    if meta:
        loaded = "是" if meta.get("adapter_loaded") else "否（基座或尚未带 LoRA）"
        lines.append(f"已加载到内存: 是 | 适配器已挂: {loaded}")
        if "vram_alloc_gb_after_adapter" in meta:
            lines.append(f"显存约: {meta['vram_alloc_gb_after_adapter']} GB")
        elif "vram_alloc_gb" in meta:
            lines.append(f"显存约: {meta['vram_alloc_gb']} GB")
    else:
        lines.append("已加载到内存: 否（首次点「翻译」时加载）")

    tables_ok = "有" if TABLES_PATH.is_file() else "无"
    lines.append(f"Holdout 表数据: {tables_ok} ({TABLES_PATH.name})")
    lines.append("OCR / 图片检测: 即将支持（当前界面仅翻译）")
    lines.append("权重许可提示: Vision-Braille-Qwen3-8B 为 CC BY-NC-SA；表格域 LoRA 为实验适配器")
    return "\n".join(lines)


def do_translate(
    braille: str,
    context: str,
    backend: str,
    max_new_tokens: int,
) -> tuple[str, str, str]:
    """Run translate; return (han_output, elapsed_line, status_refresh)."""
    text = (braille or "").strip()
    if not text:
        return "", "耗时: —（请先输入盲文）", probe_status()

    ctx = (context or "").strip() or None
    backend = (backend or "qwen8b").strip().lower()
    try:
        mt = int(max_new_tokens) if max_new_tokens else 32
    except (TypeError, ValueError):
        mt = 32
    mt = max(8, min(mt, 256))

    t0 = time.perf_counter()
    try:
        if backend == "qwen8b":
            out = translate(
                text,
                context=ctx,
                backend="qwen8b",
                max_new_tokens=mt,
            )
        elif backend == "mt5":
            out = translate(text, context=ctx, backend="mt5")
        else:
            out = f"[错误] 未知后端: {backend!r}"
    except Exception as exc:  # noqa: BLE001
        elapsed = time.perf_counter() - t0
        return (
            f"[异常] {type(exc).__name__}: {exc}",
            f"耗时: {elapsed:.2f} 秒（失败）",
            probe_status(),
        )
    elapsed = time.perf_counter() - t0
    return out, f"耗时: {elapsed:.2f} 秒", probe_status()


def fill_sample(idx: int):
    samples = _samples()
    if idx < 0 or idx >= len(samples):
        return gr.update(), gr.update(), gr.update()
    br, zh, label = samples[idx]
    note = f"已填入样例「{label}」；参考汉字: {zh}"
    return br, note, zh


def build_ui() -> gr.Blocks:
    samples = _samples()
    sample_labels = [f"{i + 1}. {s[2]}（期望: {s[1]}）" for i, s in enumerate(samples)]

    with gr.Blocks(title="中文盲文翻译演示") as demo:
        gr.Markdown(
            """
# 中文盲文翻译演示
粘贴 Unicode 盲文，调用 `translate(..., backend=\"qwen8b\")`（默认加载表格域 LoRA）。
OCR 图片识别 **即将支持**，本页只做翻译。
            """.strip()
        )

        with gr.Row():
            with gr.Column(scale=3):
                braille_in = gr.Textbox(
                    label="盲文输入",
                    placeholder="例如：⠓⠊⠼ ⠍⠊⠼⠂",
                    lines=4,
                    elem_id="braille-in",
                )
                context_in = gr.Textbox(
                    label="可选上下文（帮助消歧）",
                    placeholder="例如：三年级成绩表表头",
                    lines=2,
                )
                with gr.Row():
                    backend = gr.Radio(
                        choices=["qwen8b", "mt5"],
                        value="qwen8b",
                        label="翻译后端",
                    )
                    max_tok = gr.Slider(
                        minimum=8,
                        maximum=128,
                        value=32,
                        step=8,
                        label="max_new_tokens（qwen8b）",
                    )
                with gr.Row():
                    btn = gr.Button("翻译", variant="primary")
                    clear_btn = gr.Button("清空")
            with gr.Column(scale=2):
                han_out = gr.Textbox(label="汉字输出", lines=4)
                elapsed_out = gr.Textbox(label="耗时", lines=1, interactive=False)
                ref_out = gr.Textbox(
                    label="参考汉字（填入样例时显示，便于对比）",
                    lines=1,
                    interactive=False,
                )
                sample_note = gr.Markdown("选择下方样例可一键填入盲文。")

        with gr.Row():
            sample_dd = gr.Dropdown(
                choices=sample_labels,
                label="Holdout 样例（填入盲文）",
                value=None,
            )
            fill_btn = gr.Button("填入所选样例")

        # Quick buttons for first few samples
        with gr.Row():
            quick_btns = []
            for i, (_br, zh, lab) in enumerate(samples[:5]):
                b = gr.Button(f"样例: {zh}", size="sm")
                quick_btns.append((b, i))

        status = gr.Textbox(
            label="运行状态（适配器 / CUDA / 脚手架）",
            value=probe_status(),
            lines=10,
            interactive=False,
            elem_id="status-box",
        )
        refresh_btn = gr.Button("刷新状态", size="sm")

        gr.Markdown(
            """
---
**说明**
- 基座模型 Vision-Braille-Qwen3-8B 权重许可为 **CC BY-NC-SA**（非商业向）。
- 默认 LoRA：`models/lora_tables/`（表格域短训适配器，实验性质）。
- `detect` / 图片 OCR：**即将支持**（当前禁用）。
- 无 GPU 或未装 `[qwen]` 依赖时，`qwen8b` 会返回脚手架字符串，便于联调界面。
            """.strip()
        )

        btn.click(
            fn=do_translate,
            inputs=[braille_in, context_in, backend, max_tok],
            outputs=[han_out, elapsed_out, status],
        )
        clear_btn.click(
            fn=lambda: ("", "", "", "", "已清空。", probe_status()),
            inputs=[],
            outputs=[braille_in, context_in, han_out, elapsed_out, sample_note, status],
        )
        refresh_btn.click(fn=probe_status, inputs=[], outputs=[status])

        def _fill_from_dropdown(choice: str | None):
            if not choice:
                return gr.update(), "请先选择样例。", ""
            try:
                idx = int(choice.split(".", 1)[0]) - 1
            except ValueError:
                return gr.update(), "样例解析失败。", ""
            return fill_sample(idx)

        fill_btn.click(
            fn=_fill_from_dropdown,
            inputs=[sample_dd],
            outputs=[braille_in, sample_note, ref_out],
        )
        for b, i in quick_btns:
            b.click(
                fn=lambda i=i: fill_sample(i),
                inputs=[],
                outputs=[braille_in, sample_note, ref_out],
            )

    return demo


def main() -> None:
    demo = build_ui()
    share = (os.environ.get("CBT_WEBUI_SHARE") or "").strip() in {"1", "true", "yes"}
    launch_kw = dict(
        server_name=os.environ.get("CBT_WEBUI_HOST", "127.0.0.1"),
        server_port=DEFAULT_PORT,
        share=share,
        show_error=True,
        inbrowser=False,
        theme=gr.themes.Soft(),
        css=APP_CSS,
    )
    # Gradio <6: theme/css on Blocks; >=6: on launch. Prefer launch kwargs.
    try:
        demo.launch(**launch_kw)
    except TypeError:
        launch_kw.pop("theme", None)
        launch_kw.pop("css", None)
        demo.launch(**launch_kw)


if __name__ == "__main__":
    main()
