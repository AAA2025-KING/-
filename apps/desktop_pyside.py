#!/usr/bin/env python3
"""中文盲文翻译 — PySide6 桌面窗口（非 Gradio）。

从项目根目录启动（Windows，推荐 GPU 虚拟环境）::

    .venv-qwen\\Scripts\\python.exe apps\\desktop_pyside.py

翻译在后台 QThread 中执行，首次加载模型时界面不卡死。
"""

from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path

_REPO = Path(__file__).resolve().parents[1]
_SRC = _REPO / "src"
if _SRC.is_dir() and str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

os.chdir(_REPO)

try:
    from PySide6.QtCore import Qt, QThread, Signal, Slot
    from PySide6.QtGui import QFont
    from PySide6.QtWidgets import (
        QApplication,
        QComboBox,
        QGroupBox,
        QHBoxLayout,
        QLabel,
        QLineEdit,
        QMainWindow,
        QMessageBox,
        QPlainTextEdit,
        QPushButton,
        QSpinBox,
        QStatusBar,
        QVBoxLayout,
        QWidget,
    )
except ImportError as exc:  # pragma: no cover
    raise SystemExit(
        "未安装 PySide6。请执行: pip install -e \".[desktop]\"  或  pip install PySide6"
    ) from exc

from chinese_braille_toolkit import translate  # noqa: E402
from chinese_braille_toolkit.backends import qwen8b as qwen_backend  # noqa: E402

TABLES_PATH = _REPO / "data" / "synthetic_tables" / "tables.jsonl"

# Curated holdout cells: (braille, expected_zh, label)
SAMPLE_CELLS: list[tuple[str, str, str]] = [
    ("⠓⠊⠼ ⠍⠊⠼⠂", "姓名", "成绩表·表头「姓名」"),
    ("⠬ ⠒", "语文", "成绩表·表头「语文」"),
    ("⠌⠦ ⠎⠧⠁", "张三", "成绩表·姓名「张三」"),
    ("⠱⠦ ⠏⠊⠴", "商品", "销售表·表头「商品」"),
    ("⠙⠧ ⠛⠫⠆", "单价", "销售表·表头「单价」"),
]


def _load_extra_samples_from_jsonl(limit: int = 5) -> list[tuple[str, str, str]]:
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
    return SAMPLE_CELLS if SAMPLE_CELLS else _load_extra_samples_from_jsonl(5)


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
    lines.append("OCR / 图片检测: 即将支持（当前窗口仅翻译）")
    lines.append("权重许可: Vision-Braille-Qwen3-8B 为 CC BY-NC-SA；表格域 LoRA 为实验适配器")
    return "\n".join(lines)


class TranslateWorker(QThread):
    """Run ``translate`` off the UI thread."""

    finished_ok = Signal(str, float)  # han_text, elapsed_sec
    finished_err = Signal(str, float)  # error_message, elapsed_sec

    def __init__(
        self,
        braille: str,
        context: str | None,
        backend: str,
        max_new_tokens: int,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self._braille = braille
        self._context = context
        self._backend = backend
        self._max_new_tokens = max_new_tokens

    def run(self) -> None:
        t0 = time.perf_counter()
        try:
            backend = (self._backend or "qwen8b").strip().lower()
            if backend == "qwen8b":
                out = translate(
                    self._braille,
                    context=self._context,
                    backend="qwen8b",
                    max_new_tokens=self._max_new_tokens,
                )
            elif backend == "mt5":
                out = translate(self._braille, context=self._context, backend="mt5")
            else:
                raise ValueError(f"未知后端: {backend!r}")
            elapsed = time.perf_counter() - t0
            self.finished_ok.emit(out, elapsed)
        except Exception as exc:  # noqa: BLE001
            elapsed = time.perf_counter() - t0
            self.finished_err.emit(f"{type(exc).__name__}: {exc}", elapsed)


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("中文盲文翻译 — 桌面版")
        self.resize(780, 640)
        self._worker: TranslateWorker | None = None
        self._samples = _samples()

        central = QWidget()
        self.setCentralWidget(central)
        root = QVBoxLayout(central)

        # --- Input ---
        in_box = QGroupBox("输入")
        in_form = QVBoxLayout(in_box)
        self.braille_edit = QPlainTextEdit()
        self.braille_edit.setPlaceholderText("粘贴 Unicode 盲文，例如：⠓⠊⠼ ⠍⠊⠼⠂")
        self.braille_edit.setMinimumHeight(90)
        braille_font = QFont("Segoe UI Symbol")
        braille_font.setPointSize(14)
        self.braille_edit.setFont(braille_font)
        in_form.addWidget(QLabel("盲文："))
        in_form.addWidget(self.braille_edit)

        self.context_edit = QLineEdit()
        self.context_edit.setPlaceholderText("可选，例如：三年级成绩表表头")
        in_form.addWidget(QLabel("上下文（可选）："))
        in_form.addWidget(self.context_edit)

        opts = QHBoxLayout()
        opts.addWidget(QLabel("后端："))
        self.backend_combo = QComboBox()
        self.backend_combo.addItems(["qwen8b", "mt5"])
        self.backend_combo.setCurrentText("qwen8b")
        opts.addWidget(self.backend_combo)
        opts.addWidget(QLabel("max_new_tokens："))
        self.tokens_spin = QSpinBox()
        self.tokens_spin.setRange(8, 256)
        self.tokens_spin.setSingleStep(8)
        self.tokens_spin.setValue(32)
        opts.addWidget(self.tokens_spin)
        opts.addStretch(1)
        in_form.addLayout(opts)
        root.addWidget(in_box)

        # --- Samples ---
        sample_box = QGroupBox("Holdout 样例")
        sample_row = QHBoxLayout(sample_box)
        self.sample_combo = QComboBox()
        for i, (_br, zh, lab) in enumerate(self._samples):
            self.sample_combo.addItem(f"{i + 1}. {lab}（期望: {zh}）", i)
        sample_row.addWidget(self.sample_combo, stretch=1)
        fill_btn = QPushButton("填入样例")
        fill_btn.clicked.connect(self._on_fill_sample)
        sample_row.addWidget(fill_btn)
        for i, (_br, zh, _lab) in enumerate(self._samples[:5]):
            qb = QPushButton(zh)
            qb.setToolTip(self._samples[i][2])
            qb.clicked.connect(lambda _checked=False, idx=i: self._fill_sample_idx(idx))
            sample_row.addWidget(qb)
        root.addWidget(sample_box)

        # --- Actions ---
        act_row = QHBoxLayout()
        self.translate_btn = QPushButton("翻译")
        self.translate_btn.setDefault(True)
        self.translate_btn.clicked.connect(self._on_translate)
        act_row.addWidget(self.translate_btn)
        clear_btn = QPushButton("清空")
        clear_btn.clicked.connect(self._on_clear)
        act_row.addWidget(clear_btn)
        refresh_btn = QPushButton("刷新状态")
        refresh_btn.clicked.connect(self._refresh_status)
        act_row.addWidget(refresh_btn)
        act_row.addStretch(1)
        self.elapsed_label = QLabel("耗时: —")
        act_row.addWidget(self.elapsed_label)
        root.addLayout(act_row)

        # --- Output ---
        out_box = QGroupBox("输出")
        out_layout = QVBoxLayout(out_box)
        self.han_edit = QPlainTextEdit()
        self.han_edit.setReadOnly(True)
        self.han_edit.setMinimumHeight(70)
        out_font = QFont()
        out_font.setPointSize(16)
        self.han_edit.setFont(out_font)
        out_layout.addWidget(QLabel("汉字："))
        out_layout.addWidget(self.han_edit)
        self.ref_label = QLabel("参考汉字: —")
        out_layout.addWidget(self.ref_label)
        root.addWidget(out_box)

        # --- Status ---
        status_box = QGroupBox("运行状态（CUDA / 适配器 / 耗时）")
        status_layout = QVBoxLayout(status_box)
        self.status_edit = QPlainTextEdit()
        self.status_edit.setReadOnly(True)
        self.status_edit.setMaximumBlockCount(200)
        mono = QFont("Consolas")
        mono.setPointSize(10)
        self.status_edit.setFont(mono)
        self.status_edit.setMinimumHeight(140)
        status_layout.addWidget(self.status_edit)
        root.addWidget(status_box)

        self.setStatusBar(QStatusBar())
        self.statusBar().showMessage("就绪 — 首次翻译会加载模型，请稍候")
        self._refresh_status()

    def _fill_sample_idx(self, idx: int) -> None:
        if idx < 0 or idx >= len(self._samples):
            return
        br, zh, lab = self._samples[idx]
        self.braille_edit.setPlainText(br)
        self.ref_label.setText(f"参考汉字: {zh}（{lab}）")
        self.statusBar().showMessage(f"已填入样例「{lab}」")

    @Slot()
    def _on_fill_sample(self) -> None:
        idx = self.sample_combo.currentData()
        if idx is None:
            idx = self.sample_combo.currentIndex()
        self._fill_sample_idx(int(idx))

    @Slot()
    def _on_clear(self) -> None:
        self.braille_edit.clear()
        self.context_edit.clear()
        self.han_edit.clear()
        self.ref_label.setText("参考汉字: —")
        self.elapsed_label.setText("耗时: —")
        self.statusBar().showMessage("已清空")
        self._refresh_status()

    @Slot()
    def _refresh_status(self) -> None:
        self.status_edit.setPlainText(probe_status())

    @Slot()
    def _on_translate(self) -> None:
        text = self.braille_edit.toPlainText().strip()
        if not text:
            QMessageBox.information(self, "提示", "请先输入盲文。")
            return
        if self._worker is not None and self._worker.isRunning():
            QMessageBox.information(self, "提示", "正在翻译中，请稍候。")
            return

        ctx = self.context_edit.text().strip() or None
        backend = self.backend_combo.currentText()
        mt = int(self.tokens_spin.value())

        self.translate_btn.setEnabled(False)
        self.statusBar().showMessage("翻译中…（首次加载模型可能需数十秒）")
        self.elapsed_label.setText("耗时: 进行中…")
        self.han_edit.setPlainText("…")

        self._worker = TranslateWorker(text, ctx, backend, mt, parent=self)
        self._worker.finished_ok.connect(self._on_translate_ok)
        self._worker.finished_err.connect(self._on_translate_err)
        self._worker.finished.connect(self._on_worker_finished)
        self._worker.start()

    @Slot(str, float)
    def _on_translate_ok(self, han: str, elapsed: float) -> None:
        self.han_edit.setPlainText(han)
        self.elapsed_label.setText(f"耗时: {elapsed:.2f} 秒")
        self.statusBar().showMessage(f"完成 — {elapsed:.2f} 秒")
        self._refresh_status()

    @Slot(str, float)
    def _on_translate_err(self, err: str, elapsed: float) -> None:
        self.han_edit.setPlainText(f"[异常] {err}")
        self.elapsed_label.setText(f"耗时: {elapsed:.2f} 秒（失败）")
        self.statusBar().showMessage("翻译失败")
        self._refresh_status()

    @Slot()
    def _on_worker_finished(self) -> None:
        self.translate_btn.setEnabled(True)

    def closeEvent(self, event) -> None:  # noqa: N802
        if self._worker is not None and self._worker.isRunning():
            self._worker.wait(2000)
        super().closeEvent(event)


def main() -> int:
    # Offscreen / headless smoke: CBT_DESKTOP_SMOKE=1 builds UI then exits.
    smoke = (os.environ.get("CBT_DESKTOP_SMOKE") or "").strip() in {"1", "true", "yes"}
    if smoke and not os.environ.get("QT_QPA_PLATFORM"):
        os.environ["QT_QPA_PLATFORM"] = "offscreen"

    app = QApplication(sys.argv)
    app.setApplicationName("中文盲文翻译")
    app.setOrganizationName("chinese-braille-toolkit")
    win = MainWindow()
    if smoke:
        # Import-level + window construct check; do not exec event loop forever.
        win.show()
        app.processEvents()
        print("desktop_pyside smoke OK: window constructed")
        print(probe_status())
        win.close()
        return 0
    win.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
