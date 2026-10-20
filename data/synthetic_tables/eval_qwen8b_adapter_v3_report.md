# Qwen3-8B + LoRA adapter holdout eval (synthetic tables)

- Model: `models\Vision-Braille-Qwen3-8B`
- Adapter: `outputs\lora_tables_win_v3`
- Host: **Windows-RTX5060-8GB**
- Quantization: **4bit-nf4**
- CUDA: `True` gpu=`NVIDIA GeForce RTX 5060 Laptop GPU` VRAM=7.96GB peak_alloc=5.91GB
- Chat template: model-card system + user (`盲文内容是:` ASCII colon); strip `对应的中文内容是：`
- Generate: greedy (`do_sample=False`), `max_new_tokens` cell=32 / flat=64, `repetition_penalty=1.15`
- License note: CC BY-NC-SA 4.0 — research eval only
- Elapsed: **153.3s** (load + 128 inferences)
- Subset: all holdout tables (8 tables): every cell + 1 flat_partial per table
- Predictions JSONL: `data\synthetic_tables\eval_qwen8b_adapter_v3_predictions.jsonl`

## Status

**Success:** 128/128 samples produced predictions. No OOM.

## Aggregate (cells only)

- N cells: **120**
- N flats: **8**
- Exact-match rate: **93.3%**
- Exact-match (ignore spaces): **93.3%**
- Mean CER (raw): **0.2069**
- Mean CER (no spaces): **0.1861**

## Per-sample

| id | kind | braille | ref_zh | pred | exact | CER | CER_ns |
|----|------|---------|--------|------|-------|-----|--------|
| `t01-r0-c0` | cell | `⠓⠊⠼ ⠍⠊⠼⠂` | 姓名 | 姓名 | True | 0.0 | 0.0 |
| `t01-r0-c1` | cell | `⠬ ⠒` | 语文 | 语文 | True | 0.0 | 0.0 |
| `t01-r0-c2` | cell | `⠱⠥ ⠓⠾` | 数学 | 数学 | True | 0.0 | 0.0 |
| `t01-r0-c3` | cell | `⠊⠼ ⠬⠄` | 英语 | 英语 | True | 0.0 | 0.0 |
| `t01-r1-c0` | cell | `⠌⠦ ⠎⠧⠁` | 张三 | 张三 | True | 0.0 | 0.0 |
| `t01-r1-c1` | cell | `⠼⠊⠃` | 92 | 92 | True | 0.0 | 0.0 |
| `t01-r1-c2` | cell | `⠼⠓⠓` | 88 | 88 | True | 0.0 | 0.0 |
| `t01-r1-c3` | cell | `⠼⠓⠑` | 85 | 85 | True | 0.0 | 0.0 |
| `t01-r2-c0` | cell | `⠇⠊ ⠎` | 李四 | 李四 | True | 0.0 | 0.0 |
| `t01-r2-c1` | cell | `⠼⠛⠓` | 78 | 78 | True | 0.0 | 0.0 |
| `t01-r2-c2` | cell | `⠼⠊⠑` | 95 | 95 | True | 0.0 | 0.0 |
| `t01-r2-c3` | cell | `⠼⠓⠚` | 80 | 80 | True | 0.0 | 0.0 |
| `t01-r3-c0` | cell | `⠶⠂ ⠥` | 王五 | 王五 | True | 0.0 | 0.0 |
| `t01-r3-c1` | cell | `⠼⠓⠑` | 85 | 85 | True | 0.0 | 0.0 |
| `t01-r3-c2` | cell | `⠼⠓⠃` | 82 | 82 | True | 0.0 | 0.0 |
| `t01-r3-c3` | cell | `⠼⠊⠚` | 90 | 90 | True | 0.0 | 0.0 |
| `t01-flat-header-row1` | flat_partial | `⠓⠊⠼ ⠍⠊⠼⠂ \| ⠬ ⠒ \| ⠱⠥ ⠓⠾ \| ⠊⠼ ⠬⠄ \|\| ⠌⠦ ⠎⠧⠁…` | 姓名 \| 语文 \| 数学 \| 英语 \|\| 张三 \| 92 \| 88 \| 85 | 姓名 \| 语文 \| 数学 \| 英语 \|\| 张三 \| 92 \|… | True | 0.0 | 0.0 |
| `t02-r0-c0` | cell | `⠱⠦ ⠏⠊⠴` | 商品 | 商品 | True | 0.0 | 0.0 |
| `t02-r0-c1` | cell | `⠱⠥ ⠇⠭` | 数量 | 数量 | True | 0.0 | 0.0 |
| `t02-r0-c2` | cell | `⠙⠧ ⠛⠫⠆` | 单价 | 单位 | False | 0.5 | 0.5 |
| `t02-r0-c3` | cell | `⠛⠊⠴ ⠢` | 金额 | 金额 | True | 0.0 | 0.0 |
| `t02-r1-c0` | cell | `⠅⠩ ⠃⠊` | 铅笔 | 铅笔 | True | 0.0 | 0.0 |
| `t02-r1-c1` | cell | `⠼⠁⠃⠚` | 120 | 120 | True | 0.0 | 0.0 |
| `t02-r1-c2` | cell | `⠼⠃` | 2 | 2 | True | 0.0 | 0.0 |
| `t02-r1-c3` | cell | `⠼⠃⠙⠚` | 240 | 240 | True | 0.0 | 0.0 |
| `t02-r2-c0` | cell | `⠃⠊ ⠛⠊ ⠃⠴⠄` | 笔记本 | 笔记本 | True | 0.0 | 0.0 |
| `t02-r2-c1` | cell | `⠼⠓⠚` | 80 | 80 | True | 0.0 | 0.0 |
| `t02-r2-c2` | cell | `⠼⠑` | 5 | 5 | True | 0.0 | 0.0 |
| `t02-r2-c3` | cell | `⠼⠙⠚⠚` | 400 | 400 | True | 0.0 | 0.0 |
| `t02-r3-c0` | cell | `⠓⠭⠆ ⠏⠊` | 橡皮 | 橡皮 | True | 0.0 | 0.0 |
| `t02-r3-c1` | cell | `⠼⠑⠚` | 50 | 50 | True | 0.0 | 0.0 |
| `t02-r3-c2` | cell | `⠼⠁` | 1 | 1 | True | 0.0 | 0.0 |
| `t02-r3-c3` | cell | `⠼⠑⠚` | 50 | 50 | True | 0.0 | 0.0 |
| `t02-flat-header-row1` | flat_partial | `⠱⠦ ⠏⠊⠴ \| ⠱⠥ ⠇⠭ \| ⠙⠧ ⠛⠫⠆ \| ⠛⠊⠴ ⠢ \|\| ⠅⠩ ⠃⠊…` | 商品 \| 数量 \| 单价 \| 金额 \|\| 铅笔 \| 120 \| 2 \| 240 | 商品 \| 数量 \| 单价 \| 金额 \|\| 铅笔 \| 120 \… | True | 0.0 | 0.0 |
| `t03-r0-c0` | cell | `⠛⠑ ⠉` | 节次 | 解此 | False | 1.0 | 1.0 |
| `t03-r0-c1` | cell | `⠱ ⠛⠩` | 时间 | 时间 | True | 0.0 | 0.0 |
| `t03-r0-c2` | cell | `⠅⠢ ⠟⠼` | 课程 | 课程 | True | 0.0 | 0.0 |
| `t03-r0-c3` | cell | `⠛⠜ ⠱` | 教室 | 教师 | False | 0.5 | 0.5 |
| `t03-r1-c0` | cell | `⠙⠊ ⠊ ⠛⠑` | 第一节 | 第一节 | True | 0.0 | 0.0 |
| `t03-r1-c1` | cell | `⠼⠓ ⠱` | 8时 | 8时 | True | 0.0 | 0.0 |
| `t03-r1-c2` | cell | `⠬⠄ ⠒` | 语文 | 语文 | True | 0.0 | 0.0 |
| `t03-r1-c3` | cell | `⠼⠁⠚⠁` | 101 | 101 | True | 0.0 | 0.0 |
| `t03-r2-c0` | cell | `⠙⠊ ⠗⠆ ⠛⠑` | 第二节 | 第二节 | True | 0.0 | 0.0 |
| `t03-r2-c1` | cell | `⠼⠊ ⠱` | 9时 | 9时 | True | 0.0 | 0.0 |
| `t03-r2-c2` | cell | `⠱⠥ ⠓⠾` | 数学 | 数学 | True | 0.0 | 0.0 |
| `t03-r2-c3` | cell | `⠼⠁⠚⠁` | 101 | 101 | True | 0.0 | 0.0 |
| `t03-r3-c0` | cell | `⠙⠊ ⠎⠧ ⠛⠑` | 第三节 | 第三节 | True | 0.0 | 0.0 |
| `t03-r3-c1` | cell | `⠼⠁⠚ ⠱` | 10时 | 10时 | True | 0.0 | 0.0 |
| `t03-r3-c2` | cell | `⠊⠼ ⠬` | 英语 | 英语 | True | 0.0 | 0.0 |
| `t03-r3-c3` | cell | `⠼⠃⠚⠉` | 203 | 203 | True | 0.0 | 0.0 |
| `t03-flat-header-row1` | flat_partial | `⠛⠑ ⠉ \| ⠱ ⠛⠩ \| ⠅⠢ ⠟⠼ \| ⠛⠜ ⠱ \|\| ⠙⠊ ⠊ ⠛⠑ \|…` | 节次 \| 时间 \| 课程 \| 教室 \|\| 第一节 \| 8时 \| 语文 \| 101 | 节次 \| 时间 \| 课程 \| 教室 \|\| 第一节 \| 8时 \… | False | 0.025 | 0.0385 |
| `t04-r0-c0` | cell | `⠅⠢ ⠍⠥` | 科目 | 科目 | True | 0.0 | 0.0 |
| `t04-r0-c1` | cell | `⠏⠊⠼ ⠛⠬⠴` | 平均 | 平均 | True | 0.0 | 0.0 |
| `t04-r0-c2` | cell | `⠵⠥⠮ ⠛⠖` | 最高 | 最高 | True | 0.0 | 0.0 |
| `t04-r0-c3` | cell | `⠵⠥⠮ ⠙⠊` | 最低 | 组别 \| fragistics \| </tool_response> 格會員 | False | 19.0 | 16.5 |
| `t04-r0-c4` | cell | `⠛⠊ ⠛⠢ ⠇⠬` | 及格率 | 几个绿 | False | 1.0 | 1.0 |
| `t04-r1-c0` | cell | `⠬ ⠒⠂` | 语文 | 语文 | True | 0.0 | 0.0 |
| `t04-r1-c1` | cell | `⠼⠓⠃` | 82 | 82 | True | 0.0 | 0.0 |
| `t04-r1-c2` | cell | `⠼⠊⠓` | 98 | 98 | True | 0.0 | 0.0 |
| `t04-r1-c3` | cell | `⠼⠋⠁` | 61 | 61 | True | 0.0 | 0.0 |
| `t04-r1-c4` | cell | `⠼⠊⠃` | 92 | 92 | True | 0.0 | 0.0 |
| `t04-r2-c0` | cell | `⠱⠥ ⠓⠾` | 数学 | 数学 | True | 0.0 | 0.0 |
| `t04-r2-c1` | cell | `⠼⠛⠊` | 79 | 79 | True | 0.0 | 0.0 |
| `t04-r2-c2` | cell | `⠼⠁⠚⠚` | 100 | 100 | True | 0.0 | 0.0 |
| `t04-r2-c3` | cell | `⠼⠑⠑` | 55 | 55 | True | 0.0 | 0.0 |
| `t04-r2-c4` | cell | `⠼⠓⠓` | 88 | 88 | True | 0.0 | 0.0 |
| `t04-r3-c0` | cell | `⠊⠼ ⠬` | 英语 | 英语 | True | 0.0 | 0.0 |
| `t04-r3-c1` | cell | `⠼⠓⠙` | 84 | 84 | True | 0.0 | 0.0 |
| `t04-r3-c2` | cell | `⠼⠊⠛` | 97 | 97 | True | 0.0 | 0.0 |
| `t04-r3-c3` | cell | `⠼⠋⠋` | 66 | 66 | True | 0.0 | 0.0 |
| `t04-r3-c4` | cell | `⠼⠊⠙` | 94 | 94 | True | 0.0 | 0.0 |
| `t04-flat-header-row1` | flat_partial | `⠅⠢ ⠍⠥ \| ⠏⠊⠼ ⠛⠬⠴ \| ⠵⠥⠮ ⠛⠖ \| ⠵⠥⠮ ⠙⠊ \| ⠛⠊ ⠛⠢…` | 科目 \| 平均 \| 最高 \| 最低 \| 及格率 \|\| 语文 \| 82 \| 98 \| 61 \| 92 | 科目 \| 平均 \| 最高 \| 最低 \| 及格率 \|\| 语文 \… | True | 0.0 | 0.0 |
| `t05-r0-c0` | cell | `⠓⠊⠼ ⠍⠊⠼` | 姓名 | 姓名 | True | 0.0 | 0.0 |
| `t05-r0-c1` | cell | `⠅⠊ ⠉⠪` | 器材 | 器材 | True | 0.0 | 0.0 |
| `t05-r0-c2` | cell | `⠱⠥ ⠇⠭` | 数量 | 数量 | True | 0.0 | 0.0 |
| `t05-r0-c3` | cell | `⠚ ⠅⠊` | 日期 | 日期 | True | 0.0 | 0.0 |
| `t05-r1-c0` | cell | `⠌⠖ ⠇⠳` | 赵六 | 兆六 | False | 0.5 | 0.5 |
| `t05-r1-c1` | cell | `⠓⠩ ⠥⠮ ⠛⠊⠼` | 显微镜 | 线位机1 | False | 1.3333 | 1.3333 |
| `t05-r1-c2` | cell | `⠼⠃` | 2 | 2 | True | 0.0 | 0.0 |
| `t05-r1-c3` | cell | `⠼⠉ ⠾ ⠼⠑ ⠚` | 3月5日 | 3月5日 | True | 0.0 | 0.0 |
| `t05-r2-c0` | cell | `⠅⠩ ⠅⠊⠁` | 钱七 | 钱七 | True | 0.0 | 0.0 |
| `t05-r2-c1` | cell | `⠞⠩⠁ ⠏⠊⠼` | 天平 | 天平 | True | 0.0 | 0.0 |
| `t05-r2-c2` | cell | `⠼⠁` | 1 | 1 | True | 0.0 | 0.0 |
| `t05-r2-c3` | cell | `⠼⠉ ⠾ ⠼⠋ ⠚` | 3月6日 | 3月6日 | True | 0.0 | 0.0 |
| `t05-r3-c0` | cell | `⠎⠒ ⠃⠔⠁` | 孙八 | 孙八 | True | 0.0 | 0.0 |
| `t05-r3-c1` | cell | `⠱ ⠛⠻` | 试管 | 试管 | True | 0.0 | 0.0 |
| `t05-r3-c2` | cell | `⠼⠁⠚` | 10 | 10 | True | 0.0 | 0.0 |
| `t05-r3-c3` | cell | `⠼⠉ ⠾ ⠼⠛ ⠚` | 3月7日 | 3月7日 | True | 0.0 | 0.0 |
| `t05-flat-header-row1` | flat_partial | `⠓⠊⠼ ⠍⠊⠼ \| ⠅⠊ ⠉⠪ \| ⠱⠥ ⠇⠭ \| ⠚ ⠅⠊ \|\| ⠌⠖ ⠇⠳ …` | 姓名 \| 器材 \| 数量 \| 日期 \|\| 赵六 \| 显微镜 \| 2 \| 3月5日 | 姓名 \| 器材 \| 数量 \| 日期 \|\| 赵六 \| 显微镜 \… | True | 0.0 | 0.0 |
| `t06-r0-c0` | cell | `⠓⠊⠼ ⠅⠊⠁` | 星期 | 星期 | True | 0.0 | 0.0 |
| `t06-r0-c1` | cell | `⠥ ⠉⠧` | 午餐 | 午餐 | True | 0.0 | 0.0 |
| `t06-r0-c2` | cell | `⠚⠴ ⠱⠥` | 人数 | 人数 | True | 0.0 | 0.0 |
| `t06-r1-c0` | cell | `⠊` | 一 | 一 | True | 0.0 | 0.0 |
| `t06-r1-c1` | cell | `⠍⠊ ⠋⠧ ⠟⠖ ⠉⠪` | 米饭炒菜 | 米饭炒菜 | True | 0.0 | 0.0 |
| `t06-r1-c2` | cell | `⠼⠉⠃⠚` | 320 | 320 | True | 0.0 | 0.0 |
| `t06-r2-c0` | cell | `⠎⠧` | 三 | 三 | True | 0.0 | 0.0 |
| `t06-r2-c1` | cell | `⠍⠩ ⠞⠜ ⠞⠦` | 面条汤 | 面条汤 | True | 0.0 | 0.0 |
| `t06-r2-c2` | cell | `⠼⠃⠓⠚` | 280 | 280 | True | 0.0 | 0.0 |
| `t06-r3-c0` | cell | `⠥` | 五 | 吴 | False | 1.0 | 1.0 |
| `t06-r3-c1` | cell | `⠛⠜ ⠵` | 饺子 | 饺子 | True | 0.0 | 0.0 |
| `t06-r3-c2` | cell | `⠼⠉⠑⠚` | 350 | 350 | True | 0.0 | 0.0 |
| `t06-flat-header-row1` | flat_partial | `⠓⠊⠼ ⠅⠊⠁ \| ⠥ ⠉⠧ \| ⠚⠴ ⠱⠥ \|\| ⠊ \| ⠍⠊ ⠋⠧ ⠟⠖ ⠉…` | 星期 \| 午餐 \| 人数 \|\| 一 \| 米饭炒菜 \| 320 | 星期 \| 午餐 \| 人数 \|\| 一 \| 米饭炒菜 \| 320 | True | 0.0 | 0.0 |
| `t07-r0-c0` | cell | `⠓⠊⠼ ⠍⠊⠼` | 姓名 | 姓名 | True | 0.0 | 0.0 |
| `t07-r0-c1` | cell | `⠵⠕ ⠩` | 左眼 | 左眼 | True | 0.0 | 0.0 |
| `t07-r0-c2` | cell | `⠳ ⠩` | 右眼 | 右眼 | True | 0.0 | 0.0 |
| `t07-r0-c3` | cell | `⠛⠩ ⠊⠆` | 建议 | 建议 | True | 0.0 | 0.0 |
| `t07-r1-c0` | cell | `⠌⠷ ⠛⠳⠄` | 周九 | 周九 | True | 0.0 | 0.0 |
| `t07-r1-c1` | cell | `⠼⠑ . ⠼⠚` | 5.0 | 5.0 | True | 0.0 | 0.0 |
| `t07-r1-c2` | cell | `⠼⠙ . ⠼⠓` | 4.8 | 4.8 | True | 0.0 | 0.0 |
| `t07-r1-c3` | cell | `⠋⠥ ⠟⠔` | 复查 | 复查 | True | 0.0 | 0.0 |
| `t07-r2-c0` | cell | `⠥ ⠱` | 吴十 | 吴十 | True | 0.0 | 0.0 |
| `t07-r2-c1` | cell | `⠼⠙ . ⠼⠋` | 4.6 | 4.6 | True | 0.0 | 0.0 |
| `t07-r2-c2` | cell | `⠼⠙ . ⠼⠛` | 4.7 | 4.7 | True | 0.0 | 0.0 |
| `t07-r2-c3` | cell | `⠏⠮⠆ ⠛⠊⠼` | 配镜 | 配镜 | True | 0.0 | 0.0 |
| `t07-flat-header-row1` | flat_partial | `⠓⠊⠼ ⠍⠊⠼ \| ⠵⠕ ⠩ \| ⠳ ⠩ \| ⠛⠩ ⠊⠆ \|\| ⠌⠷ ⠛⠳⠄ \…` | 姓名 \| 左眼 \| 右眼 \| 建议 \|\| 周九 \| 5.0 \| 4.8 \| 复查 | 姓名 \| 左眼 \| 右眼 \| 建议 \|\| 周九 \| 5.0 \… | True | 0.0 | 0.0 |
| `t08-r0-c0` | cell | `⠵⠥ ⠃⠑⠂` | 组别 | 组别 | True | 0.0 | 0.0 |
| `t08-r0-c1` | cell | `⠙⠢ ⠋⠴⠁` | 得分 | 得分 | True | 0.0 | 0.0 |
| `t08-r0-c2` | cell | `⠍⠊⠼ ⠉` | 名次 | 名次 | True | 0.0 | 0.0 |
| `t08-r1-c0` | cell | `⠓⠲ ⠵⠥` | 红组 | 红组 | True | 0.0 | 0.0 |
| `t08-r1-c1` | cell | `⠼⠙⠑` | 45 | 45 | True | 0.0 | 0.0 |
| `t08-r1-c2` | cell | `⠼⠁` | 1 | 1 | True | 0.0 | 0.0 |
| `t08-r2-c0` | cell | `⠇⠧ ⠵⠥` | 蓝组 | 蓝组 | True | 0.0 | 0.0 |
| `t08-r2-c1` | cell | `⠼⠙⠃` | 42 | 42 | True | 0.0 | 0.0 |
| `t08-r2-c2` | cell | `⠼⠃` | 2 | 2 | True | 0.0 | 0.0 |
| `t08-r3-c0` | cell | `⠇⠬ ⠵⠥` | 绿组 | 绿组 | True | 0.0 | 0.0 |
| `t08-r3-c1` | cell | `⠼⠉⠓` | 38 | 38 | True | 0.0 | 0.0 |
| `t08-r3-c2` | cell | `⠼⠉` | 3 | 3 | True | 0.0 | 0.0 |
| `t08-flat-header-row1` | flat_partial | `⠵⠥ ⠃⠑⠂ \| ⠙⠢ ⠋⠴⠁ \| ⠍⠊⠼ ⠉ \|\| ⠓⠲ ⠵⠥ \| ⠼⠙⠑ \…` | 组别 \| 得分 \| 名次 \|\| 红组 \| 45 \| 1 | 组别 \| 得分 \| 名次 \|\| 红组 \| 45 \| 1 | True | 0.0 | 0.0 |

## Notes

- Same synthetic Braille holdout set (pypinyin ~10% tone); OOD vs model's passage training.
- Short table cells + `|` separators are out-of-domain; compare primarily vs base on this set.
- Generation capped to avoid the repetition loops seen in mT5 with max_new_tokens=300.
- Chart OCR out of scope; translation step 2 only.

## Inputs / outputs detail

### `t01-r0-c0`

- braille: `⠓⠊⠼ ⠍⠊⠼⠂`
- ref_zh: `姓名`
- pred: `姓名`
- tone: partial; exact=True; CER=0.0; CER_ns=0.0

### `t01-r0-c1`

- braille: `⠬ ⠒`
- ref_zh: `语文`
- pred: `语文`
- tone: none; exact=True; CER=0.0; CER_ns=0.0

### `t01-r0-c2`

- braille: `⠱⠥ ⠓⠾`
- ref_zh: `数学`
- pred: `数学`
- tone: none; exact=True; CER=0.0; CER_ns=0.0

### `t01-r0-c3`

- braille: `⠊⠼ ⠬⠄`
- ref_zh: `英语`
- pred: `英语`
- tone: partial; exact=True; CER=0.0; CER_ns=0.0

### `t01-r1-c0`

- braille: `⠌⠦ ⠎⠧⠁`
- ref_zh: `张三`
- pred: `张三`
- tone: partial; exact=True; CER=0.0; CER_ns=0.0

### `t01-r1-c1`

- braille: `⠼⠊⠃`
- ref_zh: `92`
- pred: `92`
- tone: none; exact=True; CER=0.0; CER_ns=0.0

### `t01-r1-c2`

- braille: `⠼⠓⠓`
- ref_zh: `88`
- pred: `88`
- tone: none; exact=True; CER=0.0; CER_ns=0.0

### `t01-r1-c3`

- braille: `⠼⠓⠑`
- ref_zh: `85`
- pred: `85`
- tone: none; exact=True; CER=0.0; CER_ns=0.0

### `t01-r2-c0`

- braille: `⠇⠊ ⠎`
- ref_zh: `李四`
- pred: `李四`
- tone: none; exact=True; CER=0.0; CER_ns=0.0

### `t01-r2-c1`

- braille: `⠼⠛⠓`
- ref_zh: `78`
- pred: `78`
- tone: none; exact=True; CER=0.0; CER_ns=0.0

### `t01-r2-c2`

- braille: `⠼⠊⠑`
- ref_zh: `95`
- pred: `95`
- tone: none; exact=True; CER=0.0; CER_ns=0.0

### `t01-r2-c3`

- braille: `⠼⠓⠚`
- ref_zh: `80`
- pred: `80`
- tone: none; exact=True; CER=0.0; CER_ns=0.0

### `t01-r3-c0`

- braille: `⠶⠂ ⠥`
- ref_zh: `王五`
- pred: `王五`
- tone: partial; exact=True; CER=0.0; CER_ns=0.0

### `t01-r3-c1`

- braille: `⠼⠓⠑`
- ref_zh: `85`
- pred: `85`
- tone: none; exact=True; CER=0.0; CER_ns=0.0

### `t01-r3-c2`

- braille: `⠼⠓⠃`
- ref_zh: `82`
- pred: `82`
- tone: none; exact=True; CER=0.0; CER_ns=0.0

### `t01-r3-c3`

- braille: `⠼⠊⠚`
- ref_zh: `90`
- pred: `90`
- tone: none; exact=True; CER=0.0; CER_ns=0.0

### `t01-flat-header-row1`

- braille: `⠓⠊⠼ ⠍⠊⠼⠂ | ⠬ ⠒ | ⠱⠥ ⠓⠾ | ⠊⠼ ⠬⠄ || ⠌⠦ ⠎⠧⠁ | ⠼⠊⠃ | ⠼⠓⠓ | ⠼⠓⠑`
- ref_zh: `姓名 | 语文 | 数学 | 英语 || 张三 | 92 | 88 | 85`
- pred: `姓名 | 语文 | 数学 | 英语 || 张三 | 92 | 88 | 85`
- tone: mixed; exact=True; CER=0.0; CER_ns=0.0

### `t02-r0-c0`

- braille: `⠱⠦ ⠏⠊⠴`
- ref_zh: `商品`
- pred: `商品`
- tone: none; exact=True; CER=0.0; CER_ns=0.0

### `t02-r0-c1`

- braille: `⠱⠥ ⠇⠭`
- ref_zh: `数量`
- pred: `数量`
- tone: none; exact=True; CER=0.0; CER_ns=0.0

### `t02-r0-c2`

- braille: `⠙⠧ ⠛⠫⠆`
- ref_zh: `单价`
- pred: `单位`
- tone: partial; exact=False; CER=0.5; CER_ns=0.5

### `t02-r0-c3`

- braille: `⠛⠊⠴ ⠢`
- ref_zh: `金额`
- pred: `金额`
- tone: none; exact=True; CER=0.0; CER_ns=0.0

### `t02-r1-c0`

- braille: `⠅⠩ ⠃⠊`
- ref_zh: `铅笔`
- pred: `铅笔`
- tone: none; exact=True; CER=0.0; CER_ns=0.0

### `t02-r1-c1`

- braille: `⠼⠁⠃⠚`
- ref_zh: `120`
- pred: `120`
- tone: none; exact=True; CER=0.0; CER_ns=0.0

### `t02-r1-c2`

- braille: `⠼⠃`
- ref_zh: `2`
- pred: `2`
- tone: none; exact=True; CER=0.0; CER_ns=0.0

### `t02-r1-c3`

- braille: `⠼⠃⠙⠚`
- ref_zh: `240`
- pred: `240`
- tone: none; exact=True; CER=0.0; CER_ns=0.0

### `t02-r2-c0`

- braille: `⠃⠊ ⠛⠊ ⠃⠴⠄`
- ref_zh: `笔记本`
- pred: `笔记本`
- tone: partial; exact=True; CER=0.0; CER_ns=0.0

### `t02-r2-c1`

- braille: `⠼⠓⠚`
- ref_zh: `80`
- pred: `80`
- tone: none; exact=True; CER=0.0; CER_ns=0.0

### `t02-r2-c2`

- braille: `⠼⠑`
- ref_zh: `5`
- pred: `5`
- tone: none; exact=True; CER=0.0; CER_ns=0.0

### `t02-r2-c3`

- braille: `⠼⠙⠚⠚`
- ref_zh: `400`
- pred: `400`
- tone: none; exact=True; CER=0.0; CER_ns=0.0

### `t02-r3-c0`

- braille: `⠓⠭⠆ ⠏⠊`
- ref_zh: `橡皮`
- pred: `橡皮`
- tone: partial; exact=True; CER=0.0; CER_ns=0.0

### `t02-r3-c1`

- braille: `⠼⠑⠚`
- ref_zh: `50`
- pred: `50`
- tone: none; exact=True; CER=0.0; CER_ns=0.0

### `t02-r3-c2`

- braille: `⠼⠁`
- ref_zh: `1`
- pred: `1`
- tone: none; exact=True; CER=0.0; CER_ns=0.0

### `t02-r3-c3`

- braille: `⠼⠑⠚`
- ref_zh: `50`
- pred: `50`
- tone: none; exact=True; CER=0.0; CER_ns=0.0

### `t02-flat-header-row1`

- braille: `⠱⠦ ⠏⠊⠴ | ⠱⠥ ⠇⠭ | ⠙⠧ ⠛⠫⠆ | ⠛⠊⠴ ⠢ || ⠅⠩ ⠃⠊ | ⠼⠁⠃⠚ | ⠼⠃ | ⠼⠃⠙⠚`
- ref_zh: `商品 | 数量 | 单价 | 金额 || 铅笔 | 120 | 2 | 240`
- pred: `商品 | 数量 | 单价 | 金额 || 铅笔 | 120 | 2 | 240`
- tone: mixed; exact=True; CER=0.0; CER_ns=0.0

### `t03-r0-c0`

- braille: `⠛⠑ ⠉`
- ref_zh: `节次`
- pred: `解此`
- tone: none; exact=False; CER=1.0; CER_ns=1.0

### `t03-r0-c1`

- braille: `⠱ ⠛⠩`
- ref_zh: `时间`
- pred: `时间`
- tone: none; exact=True; CER=0.0; CER_ns=0.0

### `t03-r0-c2`

- braille: `⠅⠢ ⠟⠼`
- ref_zh: `课程`
- pred: `课程`
- tone: none; exact=True; CER=0.0; CER_ns=0.0

### `t03-r0-c3`

- braille: `⠛⠜ ⠱`
- ref_zh: `教室`
- pred: `教师`
- tone: none; exact=False; CER=0.5; CER_ns=0.5

### `t03-r1-c0`

- braille: `⠙⠊ ⠊ ⠛⠑`
- ref_zh: `第一节`
- pred: `第一节`
- tone: none; exact=True; CER=0.0; CER_ns=0.0

### `t03-r1-c1`

- braille: `⠼⠓ ⠱`
- ref_zh: `8时`
- pred: `8时`
- tone: none; exact=True; CER=0.0; CER_ns=0.0

### `t03-r1-c2`

- braille: `⠬⠄ ⠒`
- ref_zh: `语文`
- pred: `语文`
- tone: partial; exact=True; CER=0.0; CER_ns=0.0

### `t03-r1-c3`

- braille: `⠼⠁⠚⠁`
- ref_zh: `101`
- pred: `101`
- tone: none; exact=True; CER=0.0; CER_ns=0.0

### `t03-r2-c0`

- braille: `⠙⠊ ⠗⠆ ⠛⠑`
- ref_zh: `第二节`
- pred: `第二节`
- tone: partial; exact=True; CER=0.0; CER_ns=0.0

### `t03-r2-c1`

- braille: `⠼⠊ ⠱`
- ref_zh: `9时`
- pred: `9时`
- tone: none; exact=True; CER=0.0; CER_ns=0.0

### `t03-r2-c2`

- braille: `⠱⠥ ⠓⠾`
- ref_zh: `数学`
- pred: `数学`
- tone: none; exact=True; CER=0.0; CER_ns=0.0

### `t03-r2-c3`

- braille: `⠼⠁⠚⠁`
- ref_zh: `101`
- pred: `101`
- tone: none; exact=True; CER=0.0; CER_ns=0.0

### `t03-r3-c0`

- braille: `⠙⠊ ⠎⠧ ⠛⠑`
- ref_zh: `第三节`
- pred: `第三节`
- tone: none; exact=True; CER=0.0; CER_ns=0.0

### `t03-r3-c1`

- braille: `⠼⠁⠚ ⠱`
- ref_zh: `10时`
- pred: `10时`
- tone: none; exact=True; CER=0.0; CER_ns=0.0

### `t03-r3-c2`

- braille: `⠊⠼ ⠬`
- ref_zh: `英语`
- pred: `英语`
- tone: none; exact=True; CER=0.0; CER_ns=0.0

### `t03-r3-c3`

- braille: `⠼⠃⠚⠉`
- ref_zh: `203`
- pred: `203`
- tone: none; exact=True; CER=0.0; CER_ns=0.0

### `t03-flat-header-row1`

- braille: `⠛⠑ ⠉ | ⠱ ⠛⠩ | ⠅⠢ ⠟⠼ | ⠛⠜ ⠱ || ⠙⠊ ⠊ ⠛⠑ | ⠼⠓ ⠱ | ⠬⠄ ⠒ | ⠼⠁⠚⠁`
- ref_zh: `节次 | 时间 | 课程 | 教室 || 第一节 | 8时 | 语文 | 101`
- pred: `节次 | 时间 | 课程 | 教室 || 第一节 | 8时 | 梯文 | 101`
- tone: mixed; exact=False; CER=0.025; CER_ns=0.0385

### `t04-r0-c0`

- braille: `⠅⠢ ⠍⠥`
- ref_zh: `科目`
- pred: `科目`
- tone: none; exact=True; CER=0.0; CER_ns=0.0

### `t04-r0-c1`

- braille: `⠏⠊⠼ ⠛⠬⠴`
- ref_zh: `平均`
- pred: `平均`
- tone: none; exact=True; CER=0.0; CER_ns=0.0

### `t04-r0-c2`

- braille: `⠵⠥⠮ ⠛⠖`
- ref_zh: `最高`
- pred: `最高`
- tone: none; exact=True; CER=0.0; CER_ns=0.0

### `t04-r0-c3`

- braille: `⠵⠥⠮ ⠙⠊`
- ref_zh: `最低`
- pred: `组别 | fragistics | </tool_response> 格會員`
- tone: none; exact=False; CER=19.0; CER_ns=16.5

### `t04-r0-c4`

- braille: `⠛⠊ ⠛⠢ ⠇⠬`
- ref_zh: `及格率`
- pred: `几个绿`
- tone: none; exact=False; CER=1.0; CER_ns=1.0

### `t04-r1-c0`

- braille: `⠬ ⠒⠂`
- ref_zh: `语文`
- pred: `语文`
- tone: partial; exact=True; CER=0.0; CER_ns=0.0

### `t04-r1-c1`

- braille: `⠼⠓⠃`
- ref_zh: `82`
- pred: `82`
- tone: none; exact=True; CER=0.0; CER_ns=0.0

### `t04-r1-c2`

- braille: `⠼⠊⠓`
- ref_zh: `98`
- pred: `98`
- tone: none; exact=True; CER=0.0; CER_ns=0.0

### `t04-r1-c3`

- braille: `⠼⠋⠁`
- ref_zh: `61`
- pred: `61`
- tone: none; exact=True; CER=0.0; CER_ns=0.0

### `t04-r1-c4`

- braille: `⠼⠊⠃`
- ref_zh: `92`
- pred: `92`
- tone: none; exact=True; CER=0.0; CER_ns=0.0

### `t04-r2-c0`

- braille: `⠱⠥ ⠓⠾`
- ref_zh: `数学`
- pred: `数学`
- tone: none; exact=True; CER=0.0; CER_ns=0.0

### `t04-r2-c1`

- braille: `⠼⠛⠊`
- ref_zh: `79`
- pred: `79`
- tone: none; exact=True; CER=0.0; CER_ns=0.0

### `t04-r2-c2`

- braille: `⠼⠁⠚⠚`
- ref_zh: `100`
- pred: `100`
- tone: none; exact=True; CER=0.0; CER_ns=0.0

### `t04-r2-c3`

- braille: `⠼⠑⠑`
- ref_zh: `55`
- pred: `55`
- tone: none; exact=True; CER=0.0; CER_ns=0.0

### `t04-r2-c4`

- braille: `⠼⠓⠓`
- ref_zh: `88`
- pred: `88`
- tone: none; exact=True; CER=0.0; CER_ns=0.0

### `t04-r3-c0`

- braille: `⠊⠼ ⠬`
- ref_zh: `英语`
- pred: `英语`
- tone: none; exact=True; CER=0.0; CER_ns=0.0

### `t04-r3-c1`

- braille: `⠼⠓⠙`
- ref_zh: `84`
- pred: `84`
- tone: none; exact=True; CER=0.0; CER_ns=0.0

### `t04-r3-c2`

- braille: `⠼⠊⠛`
- ref_zh: `97`
- pred: `97`
- tone: none; exact=True; CER=0.0; CER_ns=0.0

### `t04-r3-c3`

- braille: `⠼⠋⠋`
- ref_zh: `66`
- pred: `66`
- tone: none; exact=True; CER=0.0; CER_ns=0.0

### `t04-r3-c4`

- braille: `⠼⠊⠙`
- ref_zh: `94`
- pred: `94`
- tone: none; exact=True; CER=0.0; CER_ns=0.0

### `t04-flat-header-row1`

- braille: `⠅⠢ ⠍⠥ | ⠏⠊⠼ ⠛⠬⠴ | ⠵⠥⠮ ⠛⠖ | ⠵⠥⠮ ⠙⠊ | ⠛⠊ ⠛⠢ ⠇⠬ || ⠬ ⠒⠂ | ⠼⠓⠃ | ⠼⠊⠓ | ⠼⠋⠁ | ⠼⠊⠃`
- ref_zh: `科目 | 平均 | 最高 | 最低 | 及格率 || 语文 | 82 | 98 | 61 | 92`
- pred: `科目 | 平均 | 最高 | 最低 | 及格率 || 语文 | 82 | 98 | 61 | 92`
- tone: mixed; exact=True; CER=0.0; CER_ns=0.0

### `t05-r0-c0`

- braille: `⠓⠊⠼ ⠍⠊⠼`
- ref_zh: `姓名`
- pred: `姓名`
- tone: none; exact=True; CER=0.0; CER_ns=0.0

### `t05-r0-c1`

- braille: `⠅⠊ ⠉⠪`
- ref_zh: `器材`
- pred: `器材`
- tone: none; exact=True; CER=0.0; CER_ns=0.0

### `t05-r0-c2`

- braille: `⠱⠥ ⠇⠭`
- ref_zh: `数量`
- pred: `数量`
- tone: none; exact=True; CER=0.0; CER_ns=0.0

### `t05-r0-c3`

- braille: `⠚ ⠅⠊`
- ref_zh: `日期`
- pred: `日期`
- tone: none; exact=True; CER=0.0; CER_ns=0.0

### `t05-r1-c0`

- braille: `⠌⠖ ⠇⠳`
- ref_zh: `赵六`
- pred: `兆六`
- tone: none; exact=False; CER=0.5; CER_ns=0.5

### `t05-r1-c1`

- braille: `⠓⠩ ⠥⠮ ⠛⠊⠼`
- ref_zh: `显微镜`
- pred: `线位机1`
- tone: none; exact=False; CER=1.3333; CER_ns=1.3333

### `t05-r1-c2`

- braille: `⠼⠃`
- ref_zh: `2`
- pred: `2`
- tone: none; exact=True; CER=0.0; CER_ns=0.0

### `t05-r1-c3`

- braille: `⠼⠉ ⠾ ⠼⠑ ⠚`
- ref_zh: `3月5日`
- pred: `3月5日`
- tone: none; exact=True; CER=0.0; CER_ns=0.0

### `t05-r2-c0`

- braille: `⠅⠩ ⠅⠊⠁`
- ref_zh: `钱七`
- pred: `钱七`
- tone: partial; exact=True; CER=0.0; CER_ns=0.0

### `t05-r2-c1`

- braille: `⠞⠩⠁ ⠏⠊⠼`
- ref_zh: `天平`
- pred: `天平`
- tone: partial; exact=True; CER=0.0; CER_ns=0.0

### `t05-r2-c2`

- braille: `⠼⠁`
- ref_zh: `1`
- pred: `1`
- tone: none; exact=True; CER=0.0; CER_ns=0.0

### `t05-r2-c3`

- braille: `⠼⠉ ⠾ ⠼⠋ ⠚`
- ref_zh: `3月6日`
- pred: `3月6日`
- tone: none; exact=True; CER=0.0; CER_ns=0.0

### `t05-r3-c0`

- braille: `⠎⠒ ⠃⠔⠁`
- ref_zh: `孙八`
- pred: `孙八`
- tone: partial; exact=True; CER=0.0; CER_ns=0.0

### `t05-r3-c1`

- braille: `⠱ ⠛⠻`
- ref_zh: `试管`
- pred: `试管`
- tone: none; exact=True; CER=0.0; CER_ns=0.0

### `t05-r3-c2`

- braille: `⠼⠁⠚`
- ref_zh: `10`
- pred: `10`
- tone: none; exact=True; CER=0.0; CER_ns=0.0

### `t05-r3-c3`

- braille: `⠼⠉ ⠾ ⠼⠛ ⠚`
- ref_zh: `3月7日`
- pred: `3月7日`
- tone: none; exact=True; CER=0.0; CER_ns=0.0

### `t05-flat-header-row1`

- braille: `⠓⠊⠼ ⠍⠊⠼ | ⠅⠊ ⠉⠪ | ⠱⠥ ⠇⠭ | ⠚ ⠅⠊ || ⠌⠖ ⠇⠳ | ⠓⠩ ⠥⠮ ⠛⠊⠼ | ⠼⠃ | ⠼⠉ ⠾ ⠼⠑ ⠚`
- ref_zh: `姓名 | 器材 | 数量 | 日期 || 赵六 | 显微镜 | 2 | 3月5日`
- pred: `姓名 | 器材 | 数量 | 日期 || 赵六 | 显微镜 | 2 | 3月5日`
- tone: mixed; exact=True; CER=0.0; CER_ns=0.0

### `t06-r0-c0`

- braille: `⠓⠊⠼ ⠅⠊⠁`
- ref_zh: `星期`
- pred: `星期`
- tone: partial; exact=True; CER=0.0; CER_ns=0.0

### `t06-r0-c1`

- braille: `⠥ ⠉⠧`
- ref_zh: `午餐`
- pred: `午餐`
- tone: none; exact=True; CER=0.0; CER_ns=0.0

### `t06-r0-c2`

- braille: `⠚⠴ ⠱⠥`
- ref_zh: `人数`
- pred: `人数`
- tone: none; exact=True; CER=0.0; CER_ns=0.0

### `t06-r1-c0`

- braille: `⠊`
- ref_zh: `一`
- pred: `一`
- tone: none; exact=True; CER=0.0; CER_ns=0.0

### `t06-r1-c1`

- braille: `⠍⠊ ⠋⠧ ⠟⠖ ⠉⠪`
- ref_zh: `米饭炒菜`
- pred: `米饭炒菜`
- tone: none; exact=True; CER=0.0; CER_ns=0.0

### `t06-r1-c2`

- braille: `⠼⠉⠃⠚`
- ref_zh: `320`
- pred: `320`
- tone: none; exact=True; CER=0.0; CER_ns=0.0

### `t06-r2-c0`

- braille: `⠎⠧`
- ref_zh: `三`
- pred: `三`
- tone: none; exact=True; CER=0.0; CER_ns=0.0

### `t06-r2-c1`

- braille: `⠍⠩ ⠞⠜ ⠞⠦`
- ref_zh: `面条汤`
- pred: `面条汤`
- tone: none; exact=True; CER=0.0; CER_ns=0.0

### `t06-r2-c2`

- braille: `⠼⠃⠓⠚`
- ref_zh: `280`
- pred: `280`
- tone: none; exact=True; CER=0.0; CER_ns=0.0

### `t06-r3-c0`

- braille: `⠥`
- ref_zh: `五`
- pred: `吴`
- tone: none; exact=False; CER=1.0; CER_ns=1.0

### `t06-r3-c1`

- braille: `⠛⠜ ⠵`
- ref_zh: `饺子`
- pred: `饺子`
- tone: none; exact=True; CER=0.0; CER_ns=0.0

### `t06-r3-c2`

- braille: `⠼⠉⠑⠚`
- ref_zh: `350`
- pred: `350`
- tone: none; exact=True; CER=0.0; CER_ns=0.0

### `t06-flat-header-row1`

- braille: `⠓⠊⠼ ⠅⠊⠁ | ⠥ ⠉⠧ | ⠚⠴ ⠱⠥ || ⠊ | ⠍⠊ ⠋⠧ ⠟⠖ ⠉⠪ | ⠼⠉⠃⠚`
- ref_zh: `星期 | 午餐 | 人数 || 一 | 米饭炒菜 | 320`
- pred: `星期 | 午餐 | 人数 || 一 | 米饭炒菜 | 320`
- tone: mixed; exact=True; CER=0.0; CER_ns=0.0

### `t07-r0-c0`

- braille: `⠓⠊⠼ ⠍⠊⠼`
- ref_zh: `姓名`
- pred: `姓名`
- tone: none; exact=True; CER=0.0; CER_ns=0.0

### `t07-r0-c1`

- braille: `⠵⠕ ⠩`
- ref_zh: `左眼`
- pred: `左眼`
- tone: none; exact=True; CER=0.0; CER_ns=0.0

### `t07-r0-c2`

- braille: `⠳ ⠩`
- ref_zh: `右眼`
- pred: `右眼`
- tone: none; exact=True; CER=0.0; CER_ns=0.0

### `t07-r0-c3`

- braille: `⠛⠩ ⠊⠆`
- ref_zh: `建议`
- pred: `建议`
- tone: partial; exact=True; CER=0.0; CER_ns=0.0

### `t07-r1-c0`

- braille: `⠌⠷ ⠛⠳⠄`
- ref_zh: `周九`
- pred: `周九`
- tone: partial; exact=True; CER=0.0; CER_ns=0.0

### `t07-r1-c1`

- braille: `⠼⠑ . ⠼⠚`
- ref_zh: `5.0`
- pred: `5.0`
- tone: none; exact=True; CER=0.0; CER_ns=0.0

### `t07-r1-c2`

- braille: `⠼⠙ . ⠼⠓`
- ref_zh: `4.8`
- pred: `4.8`
- tone: none; exact=True; CER=0.0; CER_ns=0.0

### `t07-r1-c3`

- braille: `⠋⠥ ⠟⠔`
- ref_zh: `复查`
- pred: `复查`
- tone: none; exact=True; CER=0.0; CER_ns=0.0

### `t07-r2-c0`

- braille: `⠥ ⠱`
- ref_zh: `吴十`
- pred: `吴十`
- tone: none; exact=True; CER=0.0; CER_ns=0.0

### `t07-r2-c1`

- braille: `⠼⠙ . ⠼⠋`
- ref_zh: `4.6`
- pred: `4.6`
- tone: none; exact=True; CER=0.0; CER_ns=0.0

### `t07-r2-c2`

- braille: `⠼⠙ . ⠼⠛`
- ref_zh: `4.7`
- pred: `4.7`
- tone: none; exact=True; CER=0.0; CER_ns=0.0

### `t07-r2-c3`

- braille: `⠏⠮⠆ ⠛⠊⠼`
- ref_zh: `配镜`
- pred: `配镜`
- tone: partial; exact=True; CER=0.0; CER_ns=0.0

### `t07-flat-header-row1`

- braille: `⠓⠊⠼ ⠍⠊⠼ | ⠵⠕ ⠩ | ⠳ ⠩ | ⠛⠩ ⠊⠆ || ⠌⠷ ⠛⠳⠄ | ⠼⠑ . ⠼⠚ | ⠼⠙ . ⠼⠓ | ⠋⠥ ⠟⠔`
- ref_zh: `姓名 | 左眼 | 右眼 | 建议 || 周九 | 5.0 | 4.8 | 复查`
- pred: `姓名 | 左眼 | 右眼 | 建议 || 周九 | 5.0 | 4.8 | 复查`
- tone: mixed; exact=True; CER=0.0; CER_ns=0.0

### `t08-r0-c0`

- braille: `⠵⠥ ⠃⠑⠂`
- ref_zh: `组别`
- pred: `组别`
- tone: partial; exact=True; CER=0.0; CER_ns=0.0

### `t08-r0-c1`

- braille: `⠙⠢ ⠋⠴⠁`
- ref_zh: `得分`
- pred: `得分`
- tone: partial; exact=True; CER=0.0; CER_ns=0.0

### `t08-r0-c2`

- braille: `⠍⠊⠼ ⠉`
- ref_zh: `名次`
- pred: `名次`
- tone: none; exact=True; CER=0.0; CER_ns=0.0

### `t08-r1-c0`

- braille: `⠓⠲ ⠵⠥`
- ref_zh: `红组`
- pred: `红组`
- tone: none; exact=True; CER=0.0; CER_ns=0.0

### `t08-r1-c1`

- braille: `⠼⠙⠑`
- ref_zh: `45`
- pred: `45`
- tone: none; exact=True; CER=0.0; CER_ns=0.0

### `t08-r1-c2`

- braille: `⠼⠁`
- ref_zh: `1`
- pred: `1`
- tone: none; exact=True; CER=0.0; CER_ns=0.0

### `t08-r2-c0`

- braille: `⠇⠧ ⠵⠥`
- ref_zh: `蓝组`
- pred: `蓝组`
- tone: none; exact=True; CER=0.0; CER_ns=0.0

### `t08-r2-c1`

- braille: `⠼⠙⠃`
- ref_zh: `42`
- pred: `42`
- tone: none; exact=True; CER=0.0; CER_ns=0.0

### `t08-r2-c2`

- braille: `⠼⠃`
- ref_zh: `2`
- pred: `2`
- tone: none; exact=True; CER=0.0; CER_ns=0.0

### `t08-r3-c0`

- braille: `⠇⠬ ⠵⠥`
- ref_zh: `绿组`
- pred: `绿组`
- tone: none; exact=True; CER=0.0; CER_ns=0.0

### `t08-r3-c1`

- braille: `⠼⠉⠓`
- ref_zh: `38`
- pred: `38`
- tone: none; exact=True; CER=0.0; CER_ns=0.0

### `t08-r3-c2`

- braille: `⠼⠉`
- ref_zh: `3`
- pred: `3`
- tone: none; exact=True; CER=0.0; CER_ns=0.0

### `t08-flat-header-row1`

- braille: `⠵⠥ ⠃⠑⠂ | ⠙⠢ ⠋⠴⠁ | ⠍⠊⠼ ⠉ || ⠓⠲ ⠵⠥ | ⠼⠙⠑ | ⠼⠁`
- ref_zh: `组别 | 得分 | 名次 || 红组 | 45 | 1`
- pred: `组别 | 得分 | 名次 || 红组 | 45 | 1`
- tone: mixed; exact=True; CER=0.0; CER_ns=0.0
