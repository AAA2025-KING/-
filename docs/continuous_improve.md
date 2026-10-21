# 持续优化：纠错 → 合并 → 再训 → 替换适配器

网页上发现表格还原错字（如「兆六」应为「赵六」）时，可把正确汉字存成训练样本，合并进表格训练集后短训 LoRA，再换上新适配器。

## 流程概览

```
选中错误单元格 → 改正汉字 →「保存纠错」
        ↓
 data/user_corrections.jsonl
        ↓
「准备再训」或 scripts/merge_user_corrections.py
        ↓
 data/train_tables_with_errors.jsonl
        ↓
 Windows CUDA：retrain_from_corrections.ps1
        ↓
 outputs/lora_tables_from_corrections
        ↓
 复制到 models/lora_tables（或设 CBT_ADAPTER_PATH）→ 重启 API
```

## 1. 网页纠错入库

1. 翻译并还原表格后，点击错误单元格。
2. 在「纠错入库」里改「正确汉字」，点 **保存纠错**（或回车）。
3. 样本追加到 `data/user_corrections.jsonl`（ShareGPT：system / human / gpt，含 `braille`、`zh`、`source_pred`）。
4. 顶栏附近显示已保存条数；可用「刷新计数」。

对应 API：

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/v1/corrections` | 保存一条纠错 |
| GET | `/v1/corrections/stats` | 条数统计 |
| POST | `/v1/corrections/merge` | 合并进训练集 |

## 2. 合并训练集

网页点 **准备再训**，或本机：

```bash
python scripts/merge_user_corrections.py --prepare-retrain --max-steps 80
```

会：

- 以 `data/train_tables.jsonl` 为底
- 并入 `data/error_corrections.jsonl`（评测 holdout）与 `data/user_corrections.jsonl`
- 按 `(braille, zh)` 去重，写出 `data/train_tables_with_errors.jsonl`
- 写出 `outputs/retrain_request.json`（含推荐超参与命令）

## 3. Windows CUDA 再训

在项目根目录（已配置 `.venv-qwen` 与基座权重）：

```powershell
powershell -ExecutionPolicy Bypass -File scripts\windows\retrain_from_corrections.ps1
```

常用参数：

- `-MaxSteps 80`（默认；可改 40–200）
- `-DryRun` 只检查数据/配置
- `-CopyToModels` 训完复制到 `models\lora_tables`
- `-ModelPath <本地基座目录>` 指定基座

等价 Python（需自备 CUDA 环境）：

```text
.venv-qwen\Scripts\python.exe scripts\train_lora_tables.py --config configs/lora_tables.yaml --data-path data/train_tables_with_errors.jsonl --output-dir outputs/lora_tables_from_corrections --bits 4 --max-steps 80 --optim adamw_torch --logging-steps 5
```

### API 本机开训（可选）

仅当 API 跑在同一台 Windows CUDA 机器上：

```text
set CBT_ALLOW_RETRAIN=1
POST /v1/retrain          # 后台短训；无 CUDA 则拒绝
GET  /v1/retrain/status
POST /v1/retrain/prepare  # 只合并 + 写命令（默认推荐）
```

未设 `CBT_ALLOW_RETRAIN` 时不会启动训练，避免误在无 GPU 的主机上跑。

## 4. 替换适配器

训完后任选其一：

1. 脚本加 `-CopyToModels`，或手动把 `adapter_config.json`、`adapter_model.safetensors` 拷到 `models/lora_tables/`
2. 设置环境变量 `CBT_ADAPTER_PATH=outputs/lora_tables_from_corrections`

然后 **重启** FastAPI / 桌面端，再用原错例回归。

## 注意

- 不下载、不提交 8B 基座；新适配器默认在 `outputs/`（已 gitignore）。
- 仓库内跟踪的 `models/lora_tables` 仅在你确认效果后手动提交。
- `data/user_corrections.jsonl` 为本地纠错库，默认不强制入库；可自行备份。
