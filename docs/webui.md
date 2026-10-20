# Web UI（Gradio 演示）

中文界面：粘贴盲文 → 调用 `translate(..., backend="qwen8b")`（默认 `models/lora_tables/` LoRA）→ 显示汉字与耗时。

OCR / 图片检测仍为脚手架，界面标注「即将支持」。

## 依赖

```bash
pip install -e ".[demo]"
# 真机 GPU 翻译还需：
pip install -e ".[qwen]"
```

可选：`[demo]` 只装 Gradio；没有 GPU / `[qwen]` 时界面仍可打开，翻译会返回脚手架字符串。

## Windows 启动（推荐）

一键启动（推荐发给别人用的方式）：

```bat
scripts\windows\Start-BrailleDemo.bat
```

首次使用请先：

```powershell
powershell -ExecutionPolicy Bypass -File scripts\windows\setup_demo_env.ps1
powershell -ExecutionPolicy Bypass -File scripts\windows\Download-BaseModel.ps1
```

打包分发说明见 [desktop_packaging.md](desktop_packaging.md)。

也可直接：

在项目根目录 `C:\Users\LENOVO\Desktop\chinese-braille-toolkit`：

```bat
.venv-qwen\Scripts\python.exe apps\gradio_demo.py
```

浏览器打开：**http://127.0.0.1:7860**

| 环境变量 | 作用 |
|----------|------|
| `CBT_WEBUI_PORT` | 端口，默认 `7860` |
| `CBT_WEBUI_HOST` | 监听地址，默认 `127.0.0.1` |
| `CBT_WEBUI_SHARE` | 设为 `1` 时开启 Gradio share 链接 |
| `CBT_QWEN_STUB` | 设为 `1` 强制脚手架（不加载 8B） |
| `CBT_QWEN_ADAPTER` | 覆盖默认 LoRA 路径；空字符串禁用适配器 |

## 功能摘要

- 盲文输入 + 可选上下文
- 后端：`qwen8b`（默认）/ `mt5`
- 「翻译」按钮 → 汉字输出 + 耗时（秒）
- Holdout 样例下拉 / 快捷按钮（来自合成表单元格）
- 状态栏：CUDA、默认适配器是否就绪、是否已加载到显存
- 许可提示：基座 CC BY-NC-SA；表格域 LoRA 为实验适配器

## 从源码布局说明

脚本路径：`apps/gradio_demo.py`。运行时会把 `src/` 加入 `sys.path`，并 `chdir` 到仓库根，以便解析 `models/` 与 `data/`。
