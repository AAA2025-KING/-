# Training data (synthetic Braille tables)

## Counts

- **Tables:** 30
- **Instruction examples:** 500

### By kind

- `cell`: 367
- `flat`: 30
- `row`: 103

## Files

| Path | Role |
|------|------|
| `data/synthetic_tables_train/tables.jsonl` | Expanded synthetic table grids (train set) |
| `data/train_tables.jsonl` | ShareGPT JSONL for LoRA (`cell` / `row` / `flat`) |
| `data/train_tables_placeholder.jsonl` | **Superseded** smoke set (~43 lines). Kept for reference; prefer `train_tables.jsonl` |

Eval holdout remains `data/synthetic_tables/tables.jsonl` (original 8 tables).

## Format

Each JSONL line:

```json
{
  "id": "tr01-cell-r0-c0",
  "kind": "cell|row|flat",
  "table_id": "tr01",
  "conversations": [
    {"from": "system", "value": "..."},
    {"from": "human", "value": "请把以下通用盲文转换成为汉字：\n盲文内容是:\n..."},
    {"from": "gpt", "value": "对应的中文内容是：\n..."}
  ],
  "braille": "...",
  "zh": "...",
  "note": "..."
}
```

Separators match eval tables: cell ` | `, row ` || ` in flat fields.

## Regenerate

```bash
python scripts/build_train_tables_jsonl.py
```

## Limitations

Same as `data/synthetic_tables/README.md`: pypinyin approximation, no layout OCR,
synthetic only — expand with real photographed tables before production claims.

## Cap note

Full expansion (all cells + rows + flats) yields **656** examples. Default build
caps at **500** (keeps all 30 `flat` rows, then samples `cell`/`row`) so the set
stays in the 200–500 target band. Use `--max-examples 0` for the uncapped file.
