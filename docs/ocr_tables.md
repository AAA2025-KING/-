# 图片识别盲文 & 表格还原

## 依赖

```bash
pip install -e ".[ocr]"
# 或
pip install "opencv-python-headless>=4.8" numpy Pillow
```

HTTP API 额外：`pip install -e ".[api]"`（不强制安装 OCR）。

脚手架（无 OpenCV 时跳过真实检测）：

```bash
export CBT_OCR_STUB=1
```

## 扁平表格格式

与 `data/synthetic_tables/tables.jsonl` 一致：

- 单元格分隔：` | `（空格-竖线-空格）
- 行分隔：` || `

例（成绩表 t01）：

```
⠓⠊⠼ ⠍⠊⠼⠂ | ⠬ ⠒ | ⠱⠥ ⠓⠾ | ⠊⠼ ⠬⠄ || ⠌⠦ ⠎⠧⠁ | ⠼⠊⠃ | ⠼⠓⠓ | ⠼⠓⠑
```

## Python API

```python
from chinese_braille_toolkit import detect, translate_table, pipeline, translate

braille = detect("page.png")          # OpenCV 点阵检测 → Unicode 盲文
table = translate_table(braille, context="成绩表", backend="qwen8b")
# table["cells"] / ["markdown"] / ["csv"] / ["html"] / ["flat_zh"]

result = pipeline("page.png", backend="qwen8b", as_table=True)
# result["braille"], result["text"], result["table"], result["ocr_method"]
```

单元格翻译会把**表头列名**作为后续行的 `context`，便于 LoRA 消歧。

## HTTP

| 接口 | 说明 |
|------|------|
| `POST /v1/translate` | JSON：`braille`, `as_table`（默认：输入像表格则为 true）→ 可含 `table` |
| `POST /v1/detect` | multipart `file` → `braille`, `method`, `confidence` |
| `POST /v1/pipeline` | multipart `file` + `backend` / `as_table` → 识别+翻译+表格 |

## 合成样例图

```bash
python scripts/render_braille_sample.py
# → data/samples/t01_row_braille.png
```

用该图可冒烟 OCR（无需相机）。

## 实心点 vs 空心圈（未凸起）

部分教材 / 电子图用**实心黑点**表示凸起、用**空心圆环**表示未凸起位置。`opencv_dots` 只保留：

1. 轮廓相对外接圆填充率较高的 blob（空心圈填充率通常很低）；
2. 圆心附近灰度偏暗的区域（空心圈内部偏亮）。

并在二值图上做轻微腐蚀，削弱细线空心圈。纯实心样例（如 `data/samples/t01_row_braille.png`）行为不变。混合样例：`data/samples/user_upload_debug.png`。


## 空心圈 / 虚线点实心化

部分教材把**凸起点**画成空心圆或虚线圆（不是「空心=未凸起」那种对照表）。对此：

1. 先做轻微闭运算，把虚线弧连成环；
2. 用轮廓层次找到环内孔洞（以及中心偏亮的近圆轮廓）；
3. 在对应位置涂实心黑点，再走原有 `opencv_dots` 检测。

`detect(..., mode="auto")` / 网页 `/v1/detect`、`/v1/pipeline` 默认**自动**：仅当实心点很少，或空心环远多于实心点时才启用（避免把「实心=凸起、空心=未凸起」混合图误填实）。强制启用：`mode="solidify"`。

方法名：`opencv_dots_solidified`。数字 Unicode 表格截图仍走 `digital_table_unicode`，不经实心化。

局限：严重透视的立体/斜拍图仍不在范围内；极断的虚线、与表格线粘连的环可能漏检。

## 局限

- 经典 OpenCV 点检测适合**清晰、对比高、近似规整网格**的点阵图 / 渲染样例。
- 复杂照片（倾斜、阴影、反光、透视）、低分辨率截图、与背景粘连的点，准确率会下降。
- 实心/空心启发式依赖对比度；半透明点、极粗描边空心圈、或实心点中间有反光时可能误判。
- 「凸起点画成空心/虚线」可用自动实心化；「空心=未凸起」的混合图不会自动填实。
- 全空心单元格若未触发实心化，OCR 不会输出空白格，列对齐可能少一格。
- 立体/大幅透视斜拍仍不支持。
- Unicode 盲文字体截图依赖可选 `pytesseract`；未安装时主要走点阵路径。
- 表格还原假设扁平 ` | ` / ` || ` 或 OCR 输出的多单元格行；自由排版表格需后处理。


## 网页：定位与朗读

还原表格后，每个单元格带 `data-r` / `data-c`（0-based）与 `tabindex`，可点击或用方向键移动；`#cellPos` 显示「第 R 行，第 C 列 · 内容：…」。

朗读使用浏览器 **SpeechSynthesis**（优先 `zh-CN` / 中文音色，语速约 0.95），无需服务端 TTS：

- **朗读单元格**：报位置 + 内容（如「第2行第3列，88」）
- **朗读本行** / **朗读整表**：按单元格串联，单元格间短暂停顿
- **停止**：`speechSynthesis.cancel()`

Windows 一般用系统自带中文语音。不支持 SpeechSynthesis 时按钮禁用并提示。
