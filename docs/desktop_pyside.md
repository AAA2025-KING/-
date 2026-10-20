# 桌面窗口（PySide6）

原生桌面界面：粘贴盲文 → 调用 `translate(..., backend="qwen8b")`（默认 `models/lora_tables/` LoRA）→ 显示汉字与耗时。翻译在 **QThread** 后台执行，首次加载模型时窗口不卡死。

OCR / 图片检测仍为脚手架，界面标注「即将支持」。

与 Gradio Web 演示（`apps/gradio_demo.py`）功能对应，但**不依赖浏览器**。

## 依赖

```bash
pip install -e ".[desktop]"
# 或仅装 essentials（本窗口够用，体积更小）：
# pip install PySide6-Essentials
# 真机 GPU 翻译还需：
pip install -e ".[qwen]"
```

仅装 `[desktop]`（PySide6）即可打开窗口；没有 GPU / `[qwen]` 时翻译会返回脚手架字符串。

## Windows 启动（推荐）

在项目根目录 `C:\Users\LENOVO\Desktop\chinese-braille-toolkit`：

```bat
.venv-qwen\Scripts\python.exe apps\desktop_pyside.py
```

或双击：

```bat
scripts\windows\Start-BrailleDesktop.bat
```

首次使用请先准备虚拟环境与基座（与 Gradio 演示相同）：

```powershell
powershell -ExecutionPolicy Bypass -File scripts\windows\setup_demo_env.ps1
powershell -ExecutionPolicy Bypass -File scripts\windows\Download-BaseModel.ps1
# 若尚未安装 PySide6：
.venv-qwen\Scripts\python.exe -m pip install "PySide6"
# 或
.venv-qwen\Scripts\python.exe -m pip install -e ".[desktop]"
```

## 无界面冒烟（CI / 远程）

```bat
set CBT_DESKTOP_SMOKE=1
.venv-qwen\Scripts\python.exe apps\desktop_pyside.py
```

会构造窗口并以 offscreen 平台立即退出（不常驻 GUI）。

| 环境变量 | 作用 |
|----------|------|
| `CBT_DESKTOP_SMOKE` | 设为 `1` 时构造 UI 后立即退出 |
| `CBT_QWEN_STUB` | 设为 `1` 强制脚手架（不加载 8B） |
| `CBT_QWEN_ADAPTER` | 覆盖默认 LoRA 路径；空字符串禁用适配器 |
| `CBT_QWEN_MODEL` | 覆盖基座路径 / HF id |

## 功能摘要

- 盲文输入 + 可选上下文
- 后端：`qwen8b`（默认）/ `mt5`
- 「翻译」按钮 → 汉字输出 + 耗时（秒）；后台线程，界面可刷新状态
- Holdout 样例下拉 / 快捷按钮（合成表单元格）
- 状态区：CUDA、默认适配器是否就绪、是否已加载到显存
- 许可提示：基座 CC BY-NC-SA；表格域 LoRA 为实验适配器

## 与 Gradio 对比

| | PySide6 桌面 | Gradio Web |
|--|--------------|------------|
| 入口 | `apps/desktop_pyside.py` | `apps/gradio_demo.py` |
| 依赖 extra | `[desktop]` | `[demo]` |
| 启动脚本 | `Start-BrailleDesktop.bat` | `Start-BrailleDemo.bat` |
| 适用 | 内网、不想开端口、给同事双击 | 浏览器联调、远程演示 |
