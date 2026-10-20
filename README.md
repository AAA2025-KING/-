# Chinese Braille Toolkit

中文盲文图表识别、表格还原与语义翻译的 Python 工具包（**v0.1.0a1**）。

仓库：<https://github.com/AAA2025-KING/->

> 本仓库只含**代码与文档**。Vision-Braille-Qwen3-8B（约 16GB）与 LoRA 权重**不在仓库中**，需自行下载到本地 `models/`。

## 功能概览

| 能力 | 说明 |
|------|------|
| **FastAPI + 网页** | pps/api_server.py，默认 http://127.0.0.1:8000/；支持盲文翻译、图片 OCR、表格还原 |
| **点阵 OCR** | OpenCV 实心点检测（可选依赖 .[ocr]），输出 Unicode 盲文 |
| **数字盲文截图 OCR** | 识别屏幕上的 Unicode 盲文表格截图（非凸起点阵），自动还原行列 |
| **表格形状锁定** | 网页输入预览表与还原表严格同形（行列对齐）；样例按精确格子加载，避免 | 误拆 |
| **批量 GPU 翻译** | 表格按格批量推理（非逐格串行），模型预热后显著加速；单格输出消毒，抑制胡编超长/| 多列 |
| **表格还原** | 扁平 | / \|\| 分隔与 OCR 行结构 → markdown / csv / html；网页可点击单元格定位（行列跳转） |
| **中文 TTS** | 网页端用系统中文语音朗读单元格 / 本行 / 整表 |
| **语义翻译** | 	ranslate / pipeline；后端 qwen8b（本地 CUDA + 权重）或 mt5 / uto |
| **Qwen3-8B + LoRA** | 默认尝试加载 models/Vision-Braille-Qwen3-8B 与 models/lora_tables/（若存在）；无 GPU 时走脚手架，便于联调 |

## 环境要求

| 用途 | 要求 |
|------|------|
| 仅 API / 前端联调 | Python 3.10+，`pip install -e ".[api]"`；可设 `CBT_QWEN_STUB=1` |
| 图片 OCR | 另装 `.[ocr]`（OpenCV / numpy / Pillow） |
| 真机 Qwen 翻译 | NVIDIA GPU（建议 ≥8GB 用 4-bit，≥16GB 用 bf16）+ `.[qwen]` + 本地模型目录 |
| 轻量 mT5 | `.[mt5]`，约 2–4GB 内存/显存 |

## 安装

```bash
git clone https://github.com/AAA2025-KING/-.git chinese-braille-toolkit
cd chinese-braille-toolkit
python -m venv .venv
# Windows: .venv\Scripts\activate
source .venv/bin/activate
pip install -U pip
pip install -e ".[api,ocr]"          # Web + OCR
# 真机 GPU 翻译再装：
pip install -e ".[qwen]"
# 可选：轻量翻译 / 开发测试 / Gradio / 桌面 / 训练
# pip install -e ".[mt5,dev,demo,desktop,train]"
```

可选 extra 一览：`api` · `ocr` · `qwen` · `mt5` · `demo` · `desktop` · `train` · `synth` · `dev`。

## 他人如何获取模型

本仓库**不包含**任何模型权重（`.gitignore` 已忽略 `models/`、`outputs/`、`*.safetensors`、`*.bin` 等）。克隆代码后，请自行下载基座模型；LoRA 适配器需自备或跳过。

### 1. 克隆本仓库

```bash
git clone https://github.com/AAA2025-KING/-.git chinese-braille-toolkit
cd chinese-braille-toolkit
```

### 2. 一键下载基座模型 Vision-Braille-Qwen3-8B

目标目录：`models/Vision-Braille-Qwen3-8B/`（约 16GB 磁盘空间）。

模型页：<https://huggingface.co/Violet-yo/Vision-Braille-Qwen3-8B>

许可：**CC BY-NC-SA 4.0**（研究 / 非商用演示可用；商用前请自行核授权）。

先安装 Hugging Face CLI（任选其一）：

```bash
pip install -U "huggingface_hub[cli]"
# 或
pip install -U huggingface_hub
```

**Linux / macOS**（在项目根目录执行）：

```bash
mkdir -p models
huggingface-cli download Violet-yo/Vision-Braille-Qwen3-8B \
  --local-dir models/Vision-Braille-Qwen3-8B
```

**Windows**（PowerShell 或 cmd，在项目根目录）：

```bat
mkdir models 2>nul
huggingface-cli download Violet-yo/Vision-Braille-Qwen3-8B --local-dir models/Vision-Braille-Qwen3-8B
```

也可用 Python API：

```bash
python -c "from huggingface_hub import snapshot_download; snapshot_download('Violet-yo/Vision-Braille-Qwen3-8B', local_dir='models/Vision-Braille-Qwen3-8B')"
```

Windows 另可参考脚本：`scripts/windows/Download-BaseModel.ps1`。

下载完成后目录中应有 `config.json`、分片 `model-*-of-*.safetensors`、tokenizer 等文件。

### 3. LoRA 适配器（可选，GitHub 上没有）

默认若存在会加载 `models/lora_tables/`（需含 `adapter_config.json` 与 `adapter_model.safetensors`）。

- **本仓库不提供** `models/lora_tables` 权重，请勿指望从 GitHub 拉取。
- 你可以：用 `scripts/train_lora_tables.py` **自己训练**后拷到该目录；或
- **跳过 LoRA**，只使用上面的基座模型（无 adapter 时后端会按基座推理）。

请勿把 `models/` 或任何 `*.safetensors` 提交进 Git。

## 启动网页 API

在项目根目录：

```bash
# Linux / macOS
python -m uvicorn apps.api_server:app --host 127.0.0.1 --port 8000

# 或
python apps/api_server.py
```

Windows（推荐已装好 GPU 的虚拟环境）：

```bat
scripts\windows\Start-BrailleApi.bat
```

或：

```bat
.venv-qwen\Scripts\python.exe -m uvicorn apps.api_server:app --host 127.0.0.1 --port 8000
```

- 网页：<http://127.0.0.1:8000/>
- OpenAPI：<http://127.0.0.1:8000/docs>
- 健康检查：`GET /health`

无 GPU 联调前端时可设环境变量 `CBT_QWEN_STUB=1`。启动时预加载模型：`CBT_API_PRELOAD=1`。

### 网页能力提示

- 粘贴带 | 的盲文或点样例后，输入区会自动成表；翻译后还原表与输入表**同形对齐**。
- 可上传凸起点阵照片，或 **Unicode 盲文表格截图**（数字表）。
- 翻译出表格后：点击单元格或用方向键移动，状态栏显示「第 R 行，第 C 列 · 内容：…」；可用行/列数字跳转。
- 朗读使用本机中文语音：朗读单元格 / 本行 / 整表，可随时停止。
- 表格翻译默认批量 GPU 推理；启动可用 CBT_API_PRELOAD=1 预热模型。

## Python API

```python
from chinese_braille_toolkit import detect, translate, translate_table, pipeline

# 图片 → Unicode 盲文（需 .[ocr]）
braille = detect("page.png")

# 盲文 → 汉字
text = translate(braille, context="成绩表表头", backend="qwen8b")
# backend: "auto" | "mt5" | "qwen8b"

# 扁平表格盲文 → 结构化表格
table = translate_table(flat_braille, backend="qwen8b")

# 一步：识别 + 翻译；as_table=True 时结果含 table（markdown/csv/html）
result = pipeline("page.png", backend="auto", as_table=True)
print(result["text"], result.get("table"))
```

约定：`detect` 只识别；`translate` / `translate_table` 只翻译；`pipeline` = 识别 → 翻译。

更多 OCR / 表格说明见 [docs/ocr_tables.md](docs/ocr_tables.md)；FastAPI 细节见 [docs/fastapi_web.md](docs/fastapi_web.md)。

## 其它入口（可选）

| 入口 | 命令 / 路径 |
|------|-------------|
| Gradio | `python apps/gradio_demo.py`（需 `.[demo]`） |
| PySide 桌面 | `python apps/desktop_pyside.py` 或 `scripts/windows/Start-BrailleDesktop.bat` |
| LoRA 训练 | `scripts/train_lora_tables.py`（需 `.[train]`） |

## 推荐模型

| 步骤 | 模型 | 说明 |
|------|------|------|
| 翻译（语义） | [Violet-yo/Vision-Braille-Qwen3-8B](https://huggingface.co/Violet-yo/Vision-Braille-Qwen3-8B) | 长文少标调更强；许可 **CC BY-NC-SA 4.0** |
| 翻译（轻量） | [Violet-yo/mt5-small-ft-Chinese-Braille](https://huggingface.co/Violet-yo/mt5-small-ft-Chinese-Braille) | 约 0.3B |
| 识别 | 本包 OpenCV 点阵 OCR；亦可对接 AngelinaReader 等 | 与翻译模型分开 |

训练参考：[AlanYWu/ChineseBrailleTranslation](https://github.com/AlanYWu/ChineseBrailleTranslation)

## 目录结构（节选）

```
chinese-braille-toolkit/
├── apps/                 # api_server、Gradio、PySide、web 静态页
├── src/chinese_braille_toolkit/
├── scripts/              # 评测、合成表、Windows 启动脚本
├── configs/              # 训练等配置
├── data/                 # 合成样例与 jsonl（无大权重）
├── docs/                 # 使用与打包说明
├── tests/
├── models/               # 本地权重（git 忽略）
└── outputs/              # 训练输出（git 忽略）
```

## 许可

- **本仓库代码**：MIT（见 `LICENSE`）。
- **Vision-Braille-Qwen3-8B 等模型权重**：各自许可证；Qwen 微调权重为 **CC BY-NC-SA 4.0**（研究/演示可用，商用前请自行核授权）。
- 分发二进制或演示包时请在文档中写明依赖模型的许可证（参见 `scripts/windows/license_note_before_install.txt`）。

## 状态

Pre-alpha（`0.1.0a1`）。API 与网页已可用；无 GPU / 无权重时翻译返回脚手架字符串，OCR 与表格路径仍可联调。
