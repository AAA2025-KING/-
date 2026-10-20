# FastAPI + 网页前端

本机 HTTP API：`POST /v1/translate` 调用 `chinese_braille_toolkit.translate`；浏览器打开 `/` 使用简易中文页面。Gradio / PySide 仍保留，本方案适合嵌入自有网页或给别人用 HTTP 调用。

## 依赖

```bash
pip install -e ".[api]"
# 真机 GPU 翻译还需：
pip install -e ".[qwen]"
```

没有 GPU / `[qwen]` 时服务仍可启动：设 `CBT_QWEN_STUB=1` 走脚手架字符串，便于联调前端。

## Windows 一键启动

```bat
scripts\windows\Start-BrailleApi.bat
```

浏览器打开：**http://127.0.0.1:8000/**

交互式 API 文档：**http://127.0.0.1:8000/docs**

## 手动启动

在项目根目录：

```bat
cd C:\Users\LENOVO\Desktop\chinese-braille-toolkit
.venv-qwen\Scripts\python.exe -m pip install -e ".[api]"
.venv-qwen\Scripts\python.exe -m uvicorn apps.api_server:app --host 127.0.0.1 --port 8000
```

或：

```bat
.venv-qwen\Scripts\python.exe apps\api_server.py
```

## 接口

### `GET /health`

返回示例字段：

| 字段 | 含义 |
|------|------|
| `ok` | 服务存活 |
| `cuda` | 是否检测到 CUDA |
| `adapter_ready` | 默认 LoRA 目录是否完整 |
| `adapter_loaded` | 模型是否已加载到显存 |
| `stub` | 是否强制脚手架模式 |

### `POST /v1/translate`

请求 JSON：

```json
{
  "braille": "⠓⠊⠼ ⠍⠊⠼⠂",
  "context": "成绩表表头",
  "backend": "qwen8b"
}
```

响应：

```json
{
  "text": "姓名",
  "elapsed_s": 1.23,
  "backend": "qwen8b"
}
```

`backend` 默认为 `qwen8b`；也可 `mt5` / `auto`。

### 静态页

- `/` → `apps/web/index.html`
- `/static/*` → `apps/web/` 下 CSS/JS

## 环境变量

| 变量 | 作用 |
|------|------|
| `CBT_API_HOST` | 监听地址，默认 `127.0.0.1` |
| `CBT_API_PORT` | 端口，默认 `8000` |
| `CBT_API_PRELOAD` | 设为 `1` 时启动即预热一次翻译（加载模型） |
| `CBT_QWEN_STUB` | 设为 `1` 强制脚手架 |
| `CBT_QWEN_ADAPTER` | 覆盖默认 LoRA；空字符串禁用适配器 |
| `CBT_QWEN_MODEL` | 覆盖基座路径 / HF id |

## curl 冒烟

```bat
curl http://127.0.0.1:8000/health
curl -X POST http://127.0.0.1:8000/v1/translate -H "Content-Type: application/json" -d "{\"braille\":\"⠓⠊⠼ ⠍⠊⠼⠂\",\"backend\":\"qwen8b\"}"
```

PowerShell：

```powershell
Invoke-RestMethod http://127.0.0.1:8000/health
Invoke-RestMethod http://127.0.0.1:8000/v1/translate -Method Post -ContentType "application/json" -Body '{"braille":"⠓⠊⠼ ⠍⠊⠼⠂","backend":"qwen8b"}'
```

## CORS

默认允许本机常见来源（`127.0.0.1` / `localhost` 及常用端口）。静态页与 API 同源时无需额外配置；若用 Live Server 等单独起前端，可按需改 `apps/api_server.py` 中的 `CORSMiddleware`。

## 许可提示

基座 Vision-Braille-Qwen3-8B 多为 **CC BY-NC-SA**（非商用）；表格域 LoRA 为实验适配器。分发权重前请自查合规。

## 表格定位与朗读

网页「还原表格」区域支持单元格定位（点击 / 方向键 / 行·列跳转）与浏览器语音朗读（SpeechSynthesis，优先中文音色）。详见 `docs/ocr_tables.md`「网页：定位与朗读」。
