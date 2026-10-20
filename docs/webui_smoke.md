# Web UI 冒烟结果

**日期:** 2026-10-20（Asia/Shanghai）  
**主机:** Windows RTX 5060 Laptop（`LAPTOP-979NM299`）  
**环境:** `.venv-qwen` + Gradio **6.30.0**  
**状态:** 通过

## 启动命令

```bat
cd C:\Users\LENOVO\Desktop\chinese-braille-toolkit
.venv-qwen\Scripts\python.exe apps\gradio_demo.py
```

**URL:** http://127.0.0.1:7860/

## 检查项

| 项 | 结果 |
|----|------|
| 依赖安装 | `pip install "gradio>=4.0"` → Gradio 6.30.0 |
| `build_ui()` | Blocks 构建成功（Gradio 6：`theme`/`css` 传给 `launch()`） |
| 状态栏 | CUDA 可用（RTX 5060）；默认适配器 `models/lora_tables` 已找到 |
| HTTP 冒烟 | 后台启动约 2s 后 `GET /` → **200**，页面约 40KB，含界面内容 |
| 真实翻译 | 同进程调用 `do_translate("⠓⠊⠼ ⠍⠊⠼⠂", …, "qwen8b")` → **姓名**，耗时 **12.45 秒**（含冷启动加载） |
| 脚手架模式 | `CBT_QWEN_STUB=1` 下仅起 UI（HTTP 冒烟用），避免二次占满显存 |

## 产物路径

| 路径 | 说明 |
|------|------|
| `apps/gradio_demo.py` | Gradio 演示入口 |
| `docs/webui.md` | 启动说明 |
| `outputs/webui_translate_smoke.json` | 翻译冒烟 JSON |
| `outputs/webui_server_smoke.json` | HTTP 冒烟 JSON |

## 可选依赖

`pyproject.toml` 增加：

```toml
demo = ["gradio>=4.0"]
```

安装：`pip install -e ".[demo]"`（真机推理另需 `[qwen]`）。

## 备注

- 无长期占用端口：冒烟后已结束 Gradio 进程。
- 日常使用请去掉 `CBT_QWEN_STUB`，直接启动上述命令，浏览器打开 http://127.0.0.1:7860/ 。
