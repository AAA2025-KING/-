#!/usr/bin/env python3
"""中文盲文翻译 — FastAPI HTTP API + 静态网页前端.

从项目根目录启动（Windows，推荐 GPU 虚拟环境）::

    .venv-qwen\\Scripts\\python.exe -m uvicorn apps.api_server:app --host 127.0.0.1 --port 8000

浏览器打开 http://127.0.0.1:8000/
"""

from __future__ import annotations

import os
import sys
import tempfile
import time
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

# Ensure editable package is importable when run as a script / uvicorn from repo root.
_REPO = Path(__file__).resolve().parents[1]
_SRC = _REPO / "src"
_WEB = Path(__file__).resolve().parent / "web"
if _SRC.is_dir() and str(_SRC) not in sys.path:
    sys.path.insert(0, str(_SRC))

os.chdir(_REPO)

try:
    from fastapi import FastAPI, File, Form, HTTPException, UploadFile
    from fastapi.middleware.cors import CORSMiddleware
    from fastapi.responses import FileResponse
    from fastapi.staticfiles import StaticFiles
except ImportError as exc:  # pragma: no cover
    raise SystemExit(
        '未安装 FastAPI/uvicorn。请执行: pip install -e ".[api]"  '
        '或  pip install "fastapi" "uvicorn[standard]"'
    ) from exc

from chinese_braille_toolkit import (  # noqa: E402
    detect_detailed,
    pipeline,
    translate,
    translate_table,
)
from chinese_braille_toolkit import tables as tables_mod  # noqa: E402
from chinese_braille_toolkit.backends import qwen8b as qwen_backend  # noqa: E402

DEFAULT_HOST = os.environ.get("CBT_API_HOST", "127.0.0.1")
DEFAULT_PORT = int(os.environ.get("CBT_API_PORT", "8000"))
PRELOAD = (os.environ.get("CBT_API_PRELOAD") or "").strip().lower() in {
    "1",
    "true",
    "yes",
    "on",
}


class TranslateRequest(BaseModel):
    braille: str = Field(..., min_length=1, description="Unicode 盲文或 ASCII 盲文")
    context: str | None = Field(None, description="可选上下文，帮助消歧")
    backend: str | None = Field("qwen8b", description="auto | mt5 | qwen8b")
    as_table: bool | None = Field(
        None,
        description="若为 true（或输入像扁平表格）则按单元格翻译并还原表格",
    )


class TablePayload(BaseModel):
    cells: list[list[str]] = []
    markdown: str = ""
    csv: str = ""
    html: str = ""
    flat_zh: str = ""


class TranslateResponse(BaseModel):
    text: str
    elapsed_s: float
    backend: str
    table: TablePayload | None = None


class DetectResponse(BaseModel):
    braille: str
    method: str | None = None
    confidence: float | None = None
    rows: list[list[str]] | None = None
    elapsed_s: float = 0.0


class PipelineResponse(BaseModel):
    braille: str
    text: str
    backend: str
    confidence: float | None = None
    ocr_method: str | None = None
    table: TablePayload | None = None
    elapsed_s: float = 0.0


class HealthResponse(BaseModel):
    ok: bool
    cuda: bool
    gpu_name: str | None = None
    adapter_path: str | None = None
    adapter_ready: bool = False
    adapter_loaded: bool = False
    stub: bool = False
    ocr_ready: bool = False
    model_meta: dict[str, Any] | None = None


app = FastAPI(
    title="中文盲文翻译 API",
    description=(
        "HTTP 接口 + 静态前端。支持盲文翻译、图片 OCR、表格还原。"
        " 调用 chinese_braille_toolkit。"
    ),
    version="0.1.0a1",
)

app.add_middleware(
    CORSMiddleware,
    allow_origin_regex=r"https?://(localhost|127\.0\.0\.1)(:\d+)?|null",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def _cuda_info() -> tuple[bool, str | None]:
    try:
        import torch

        if torch.cuda.is_available():
            return True, torch.cuda.get_device_name(0)
    except Exception:  # noqa: BLE001
        pass
    return False, None


def _adapter_loaded_hint() -> bool:
    meta = qwen_backend.get_model_meta()
    if not meta:
        return False
    return bool(meta.get("adapter_loaded") or meta.get("adapter_path"))


def _ocr_ready() -> bool:
    try:
        import cv2  # noqa: F401
        import numpy  # noqa: F401
        from PIL import Image  # noqa: F401

        return True
    except ImportError:
        return False


def _table_payload(table: dict[str, Any] | None) -> TablePayload | None:
    if not table:
        return None
    return TablePayload(
        cells=table.get("cells") or [],
        markdown=table.get("markdown") or "",
        csv=table.get("csv") or "",
        html=table.get("html") or "",
        flat_zh=table.get("flat_zh") or "",
    )


def _save_upload(upload: UploadFile) -> Path:
    suffix = Path(upload.filename or "upload.png").suffix or ".png"
    fd, name = tempfile.mkstemp(prefix="cbt_ocr_", suffix=suffix)
    os.close(fd)
    path = Path(name)
    data = upload.file.read()
    path.write_bytes(data)
    return path


@app.on_event("startup")
def _startup() -> None:
    if not PRELOAD:
        return
    try:
        translate("⠓⠊⠼", backend="qwen8b", max_new_tokens=8)
    except Exception as exc:  # noqa: BLE001
        print(f"[api_server] preload failed (non-fatal): {type(exc).__name__}: {exc}")


@app.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    cuda, gpu_name = _cuda_info()
    adap = qwen_backend.resolve_adapter_path(None)
    ready = False
    if adap:
        p = Path(adap)
        ready = (p / "adapter_config.json").is_file() and (
            (p / "adapter_model.safetensors").is_file()
            or (p / "adapter_model.bin").is_file()
        )
    stub = (os.environ.get("CBT_QWEN_STUB") or "").strip().lower() in {
        "1",
        "true",
        "yes",
        "on",
    }
    return HealthResponse(
        ok=True,
        cuda=cuda,
        gpu_name=gpu_name,
        adapter_path=adap,
        adapter_ready=ready,
        adapter_loaded=_adapter_loaded_hint(),
        stub=stub,
        ocr_ready=_ocr_ready(),
        model_meta=qwen_backend.get_model_meta(),
    )


@app.post("/v1/translate", response_model=TranslateResponse)
def v1_translate(body: TranslateRequest) -> TranslateResponse:
    backend = (body.backend or "qwen8b").strip() or "qwen8b"
    braille = (body.braille or "").strip()
    if not braille:
        raise HTTPException(status_code=400, detail="braille 不能为空")

    want_table = body.as_table
    if want_table is None:
        want_table = tables_mod.is_flat_table(braille)

    t0 = time.perf_counter()
    try:
        table_out: dict[str, Any] | None = None
        if want_table:
            table_out = translate_table(braille, context=body.context, backend=backend)
            text = table_out.get("flat_zh") or ""
        else:
            text = translate(braille, context=body.context, backend=backend)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(
            status_code=500,
            detail=f"{type(exc).__name__}: {exc}",
        ) from exc
    elapsed = round(time.perf_counter() - t0, 3)
    return TranslateResponse(
        text=text,
        elapsed_s=elapsed,
        backend=backend,
        table=_table_payload(table_out),
    )


@app.post("/v1/detect", response_model=DetectResponse)
async def v1_detect(file: UploadFile = File(...)) -> DetectResponse:
    if not file.filename:
        raise HTTPException(status_code=400, detail="需要上传图片文件")
    path = _save_upload(file)
    t0 = time.perf_counter()
    try:
        detail = detect_detailed(path)
    except ImportError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(
            status_code=500,
            detail=f"{type(exc).__name__}: {exc}",
        ) from exc
    finally:
        try:
            path.unlink(missing_ok=True)
        except Exception:  # noqa: BLE001
            pass
    elapsed = round(time.perf_counter() - t0, 3)
    return DetectResponse(
        braille=str(detail.get("braille") or ""),
        method=detail.get("method"),
        confidence=detail.get("confidence"),
        rows=detail.get("rows"),
        elapsed_s=elapsed,
    )


@app.post("/v1/pipeline", response_model=PipelineResponse)
async def v1_pipeline(
    file: UploadFile = File(...),
    backend: str = Form("qwen8b"),
    as_table: bool = Form(True),
    context: str | None = Form(None),
) -> PipelineResponse:
    if not file.filename:
        raise HTTPException(status_code=400, detail="需要上传图片文件")
    path = _save_upload(file)
    t0 = time.perf_counter()
    try:
        result = pipeline(
            path,
            backend=(backend or "qwen8b").strip() or "qwen8b",
            as_table=as_table,
            context=context,
        )
    except ImportError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(
            status_code=500,
            detail=f"{type(exc).__name__}: {exc}",
        ) from exc
    finally:
        try:
            path.unlink(missing_ok=True)
        except Exception:  # noqa: BLE001
            pass
    elapsed = round(time.perf_counter() - t0, 3)
    return PipelineResponse(
        braille=str(result.get("braille") or ""),
        text=str(result.get("text") or ""),
        backend=str(result.get("backend") or backend),
        confidence=result.get("confidence"),
        ocr_method=result.get("ocr_method"),
        table=_table_payload(result.get("table")),
        elapsed_s=elapsed,
    )


@app.get("/")
def index() -> FileResponse:
    index_path = _WEB / "index.html"
    if not index_path.is_file():
        raise HTTPException(status_code=404, detail="缺少 apps/web/index.html")
    return FileResponse(index_path, media_type="text/html; charset=utf-8")


if _WEB.is_dir():
    app.mount("/static", StaticFiles(directory=str(_WEB)), name="static")


def main() -> None:
    """``python apps/api_server.py`` 便捷入口。"""
    try:
        import uvicorn
    except ImportError as exc:  # pragma: no cover
        raise SystemExit(
            '未安装 uvicorn。请执行: pip install -e ".[api]"'
        ) from exc
    uvicorn.run(
        "apps.api_server:app",
        host=DEFAULT_HOST,
        port=DEFAULT_PORT,
        reload=False,
    )


if __name__ == "__main__":
    main()
