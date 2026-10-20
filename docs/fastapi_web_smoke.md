# FastAPI 网页冒烟（Windows）

日期：2026-10-20（Asia/Shanghai）

## 步骤

1. 同步 `apps/api_server.py`、`apps/web/*`、`pyproject.toml`、`Start-BrailleApi.bat`、`docs/fastapi_web.md`
2. `.venv-qwen\Scripts\python.exe -m pip install -e ".[api]"` → fastapi 0.151 / uvicorn 0.54
3. `CBT_QWEN_STUB=1` 启动：`python -m uvicorn apps.api_server:app --host 127.0.0.1 --port 8000`
4. `GET /health` → `ok=true`，`cuda=true`（RTX 5060），`adapter_ready=true`，`stub=true`，`adapter_loaded=false`
5. `POST /v1/translate`（盲文「⠓⠊⠼ ⠍⠊⠼⠂」）→ 脚手架字符串含盲文，`backend=qwen8b`，`elapsed_s≈0`
6. `GET /` → 200，标题「中文盲文翻译」；`GET /static/style.css` → 200
7. 结束 uvicorn；端口 8000 释放

真模型推理未在本次冒烟中强制加载（使用 stub）；去掉 `CBT_QWEN_STUB` 后首次翻译会加载 LoRA。
