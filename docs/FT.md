# 表格域盲文→汉字微调计划 / Table-domain Braille→Chinese FT plan

## 目标 / Goal

公开句级模型（mT5、Vision-Braille-Qwen3-8B）在**短表头/单元格**上效果差。本计划用 **LoRA / QLoRA** 把翻译模型适配到表格域，再接入 `chinese-braille-toolkit.translate`。

Public sentence-level models underperform on short table headers/cells. Adapt with **LoRA/QLoRA**, then plug into `translate`.

## 基座 / Base model

1. 优先：[Violet-yo/Vision-Braille-Qwen3-8B](https://huggingface.co/Violet-yo/Vision-Braille-Qwen3-8B)（已有盲文对话模板）  
2. 备选：`Qwen/Qwen3-8B` 再训盲文指令  

许可注意：Vision-Braille-Qwen3-8B 为 **CC BY-NC-SA 4.0**（偏非商用）。

## 数据 / Data

| 来源 | 用途 |
|------|------|
| `data/synthetic_tables_train/` + `data/train_tables.jsonl` | 表格单元格 / 行 / 整表（约 500 条；placeholder 已作废） |
| [Chinese-Braille-Dataset-10per-Tone](https://huggingface.co/datasets/Violet-yo/Chinese-Braille-Dataset-10per-Tone) | 混入句级少标调，防遗忘通用翻译 |
| 真实拍照表（自建，少量） | 最终人工验收 |

格式：ShareGPT 风格 `conversations`（system / human / gpt），与评测脚本中的 Qwen chat 模板一致。

## 训练 / Training

- **8GB 显存**：QLoRA `bits=4`，`r=16`，`alpha=32`，batch=1 + grad_accum=8（见 `configs/lora_tables.yaml`）  
- **16GB+**：可改 `bits=16` 全精度 LoRA  
- 脚本骨架：`scripts/train_lora_tables.py`（未装 peft/transformers 时会清晰退出）  
- **本仓库不默认跑完整训练、不强制下载大权重**；先装依赖、再指向本地模型目录。

```bash
pip install -e ".[train]"
# 仅检查参数 / 缺依赖提示：
python scripts/train_lora_tables.py --help
# 真跑（需 GPU + 已下载模型 + 扩大后的 jsonl）：
python scripts/train_lora_tables.py \
  --config configs/lora_tables.yaml \
  --model-path /path/to/Vision-Braille-Qwen3-8B \
  --data-path data/train_tables.jsonl \
  --output-dir outputs/lora_tables \
  --bits 4 --lora-r 16 --lora-alpha 32 --max-steps 200
```

## 评测 / Eval

仍用合成表套件回归：

- `data/synthetic_tables/tables.jsonl`
- `scripts/eval_qwen8b_tables.py`（可改为加载 LoRA adapter）
- 指标：单元格 exact-match、CER；再抽几张真实表做人工可读性

## 接入包 / Integrate

训练出的 adapter 放到 `models/lora_tables/`（当前默认：`outputs/lora_tables_win_v3` 已复制至此），`backends/qwen8b.py` 在 CUDA 上加载 4-bit 基座后用 `PeftModel.from_pretrained` 挂 adapter；`translate(..., backend="qwen8b")` 默认走适配后权重。也可用环境变量 `CBT_QWEN_ADAPTER` / 关键字参数 `adapter_path` 覆盖。详见 [`integrate_v3_backend.md`](integrate_v3_backend.md)。

## 路线 / Roadmap

1. ✅ 骨架：config + script + placeholder jsonl（本目录）  
2. ✅ 扩大合成表 → `data/train_tables.jsonl`（下一步：抽样混入 10per-Tone）  
3. 本机 QLoRA 短跑（max_steps 验证 pipeline）  
4. 正式训练 → 评测 → 写入后端  
5. 若仍不够：加真实表 OCR 噪声增强 / 更大 r
