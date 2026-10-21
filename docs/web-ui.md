# 网页端使用说明（Web UI）

对应静态页：`apps/web/index.html`（主流程）与 `apps/web/help.html`（完整说明）。浏览器打开服务根路径 `/` 即可；说明页为 `/static/help.html`。

## 主页面布局

主页面按工作流分区，冗长说明收进折叠「使用说明」与独立帮助页：

1. **状态** — `/health` 结果
2. **盲文输入** — 文本框、自动输入表格、可选上下文、后端、按表格还原、样例芯片、翻译 / 清空
3. **图片识别（可选）** — 选图 +「识别并翻译」；细节见帮助页 OCR 章节
4. **汉字结果** — 译文、还原表格（定位 / TTS）、单元格纠错入库、准备再训、Markdown·CSV 导出
5. **使用说明（折叠）** — OCR 要点、表格、许可、API 摘要 + 链到完整说明

## OCR 提示

- **Unicode / 网页盲文表格截图**：切格读取 U+2800 字形。
- **凸起点阵照片**：需清晰实心圆点。
- **空心圈教材图 / 模糊照** 常失败 → 改为粘贴盲文。
- 流水线：`POST /v1/pipeline`。

## 表格

- 单元格 `|`、行 `||`；粘贴后自动成可编辑表，并勾选「按表格还原」。
- 样例芯片可带 `data-sample`、`data-cells`、`data-table` 等属性，由 `app.js` 加载精确网格。
- 结果表支持单元格跳转与浏览器 `SpeechSynthesis` 朗读。

## 许可

基座模型多为 **CC BY-NC-SA（非商用）**。详见仓库 `LICENSE` 与上游条款。

## API

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/health` | 健康与适配器状态 |
| POST | `/v1/translate` | 翻译（可 `as_table`） |
| POST | `/v1/detect` | 图片 OCR / 检测 |
| POST | `/v1/pipeline` | 识别并翻译 |
| POST | `/v1/corrections` | 保存单元格纠错 |
| GET | `/v1/corrections/stats` | 纠错条数 |
| POST | `/v1/corrections/merge` | 合并进训练集 |
| POST | `/v1/retrain/prepare` | 合并并给出再训命令 |
| GET | `/docs` | OpenAPI |

静态资源挂载于 `/static`（同目录下的 `style.css`、`app.js`、`help.html`）。

## 开发注意

- 保持 `lang="zh-CN"` 与用户可见文案为中文。
- 修改 CSS/JS 后请 bump `index.html` / `help.html` 中的 `?v=` 缓存参数。
- 勿在此文档或前端提交大型模型权重。

## 持续优化

单元格纠错与 LoRA 再训闭环见 [continuous_improve.md](./continuous_improve.md)。
