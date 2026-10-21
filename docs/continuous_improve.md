# 持续优化：纠错 → 一键重训 → 换适配器

网页上发现表格还原错字（如「兆六」应为「赵六」）时，把正确汉字存成训练样本，再点 **一键重训** 即可在本机 CUDA 上短训表格 LoRA 并写回适配器。

## 推荐流程（网页一键）

```
选中错误单元格 → 改正汉字 →「保存纠错」
        ↓
     「一键重训」
        ↓
 合并 → 后台 QLoRA 短训 → 复制到 models/lora_tables
        ↓
 热卸载旧模型（下次翻译自动加载；也可重启 API）
```

1. 翻译并还原表格后，点击错误单元格，在「纠错入库」改正汉字，点 **保存纠错**。
2. 点 **一键重训**（主按钮）。服务会：
   - 合并 `user_corrections` + holdout 纠错进 `data/train_tables_with_errors.jsonl`
   - 后台启动短训（默认约 80 steps）
   - 在面板内轮询 `GET /v1/retrain/status` 显示进度
   - 成功后复制适配器到 `models/lora_tables`，并卸载显存中的旧模型
3. 用原错例再译一次验证。

### 启用条件

- 用 `scripts\windows\Start-BrailleApi.bat` 启动时默认 `CBT_ALLOW_RETRAIN=1`（**仅建议本机 Windows CUDA**）。
- 无 CUDA、已有任务在跑、尚无纠错时会返回明确中文错误。
- 默认需至少 **1 条网页纠错**；若只有已有合并集/holdout，网页会弹出确认后再训（`allow_without_user_corrections=true`）。

### API

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/v1/corrections` | 保存一条纠错 |
| GET | `/v1/corrections/stats` | 条数统计 |
| POST | `/v1/retrain` | **一键重训**（合并+后台训+复制） |
| GET | `/v1/retrain/status` | 进度 / 结果 |
| POST | `/v1/retrain/prepare` | 仅合并 + 写出手动命令（高级） |

## 高级：仅准备 / 手动脚本

折叠面板里的 **准备再训**，或：

```powershell
powershell -ExecutionPolicy Bypass -File scripts\windows\retrain_from_corrections.ps1 -CopyToModels
```

参数：`-MaxSteps 80`、`-DryRun`、`-CopyToModels`、`-ModelPath <基座>`。

## 注意

- 不下载、不提交 8B 基座；新适配器默认在 `outputs/`（已 gitignore）。
- 仓库内跟踪的 `models/lora_tables` 仅在你确认效果后手动提交。
- `data/user_corrections.jsonl` 为本地纠错库，默认不入库。
- 一键重训会占用本机 GPU，训练期间翻译可能变慢或显存紧张。
