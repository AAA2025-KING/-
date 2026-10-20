#!/usr/bin/env python3
"""Expand synthetic Braille tables → ShareGPT instruction JSONL for LoRA.

Reuses braille conversion from build_synthetic_tables.py.
Writes:
  data/synthetic_tables_train/tables.jsonl   (table grids)
  data/train_tables.jsonl                   (cell / row / flat examples)
  data/README_train.md                      (counts + notes)

Keeps data/train_tables_placeholder.jsonl as the superseded smoke set.
"""

from __future__ import annotations

import argparse
import json
import random
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(Path(__file__).resolve().parent))

from build_synthetic_tables import (  # noqa: E402
    CELL_SEP,
    ROW_SEP,
    default_tables,
    make_table,
    write_outputs,
)

SYSTEM = "你是一个中国盲文翻译助手，请把通用盲文转换成为汉字。"
NOTE = (
    "synthetic table train set for LoRA; "
    "pypinyin BRAILLE_MAINLAND (~10% tone); supersedes train_tables_placeholder.jsonl"
)


def train_table_specs() -> list[tuple[str, str, list[list[str]], str]]:
    """Hand-authored diverse grids (≥28). Includes the original 8 eval themes."""
    return [
        # --- original-style (eval overlap OK for train; holdout still eval suite) ---
        (
            "tr01",
            "三年级期中成绩表",
            [
                ["姓名", "语文", "数学", "英语"],
                ["张三", "92", "88", "85"],
                ["李四", "78", "95", "80"],
                ["王五", "85", "82", "90"],
                ["赵敏", "91", "87", "93"],
            ],
            "grades",
        ),
        (
            "tr02",
            "十月份商品销售表",
            [
                ["商品", "数量", "单价", "金额"],
                ["铅笔", "120", "2", "240"],
                ["笔记本", "80", "5", "400"],
                ["橡皮", "50", "1", "50"],
                ["尺子", "40", "3", "120"],
            ],
            "sales",
        ),
        (
            "tr03",
            "周一课程表",
            [
                ["节次", "时间", "课程", "教室"],
                ["第一节", "8时", "语文", "101"],
                ["第二节", "9时", "数学", "101"],
                ["第三节", "10时", "英语", "203"],
                ["第四节", "11时", "体育", "操场"],
            ],
            "schedule",
        ),
        (
            "tr04",
            "班级考试统计",
            [
                ["科目", "平均", "最高", "最低", "及格率"],
                ["语文", "82", "98", "61", "92"],
                ["数学", "79", "100", "55", "88"],
                ["英语", "84", "97", "66", "94"],
                ["科学", "81", "99", "58", "90"],
            ],
            "stats",
        ),
        (
            "tr05",
            "实验室器材借用登记",
            [
                ["姓名", "器材", "数量", "日期"],
                ["赵六", "显微镜", "2", "3月5日"],
                ["钱七", "天平", "1", "3月6日"],
                ["孙八", "试管", "10", "3月7日"],
                ["周青", "烧杯", "5", "3月8日"],
            ],
            "lab",
        ),
        (
            "tr06",
            "食堂一周菜单摘要",
            [
                ["星期", "午餐", "人数"],
                ["一", "米饭炒菜", "320"],
                ["三", "面条汤", "280"],
                ["五", "饺子", "350"],
                ["日", "包子粥", "260"],
            ],
            "canteen",
        ),
        (
            "tr07",
            "视力检查结果简表",
            [
                ["姓名", "左眼", "右眼", "建议"],
                ["周九", "5.0", "4.8", "复查"],
                ["吴十", "4.6", "4.7", "配镜"],
                ["郑十一", "5.1", "5.0", "正常"],
            ],
            "vision",
        ),
        (
            "tr08",
            "小组积分榜",
            [
                ["组别", "得分", "名次"],
                ["红组", "45", "1"],
                ["蓝组", "42", "2"],
                ["绿组", "38", "3"],
                ["黄组", "36", "4"],
            ],
            "scoreboard",
        ),
        # --- new domains ---
        (
            "tr09",
            "图书借阅登记",
            [
                ["读者", "书名", "册数", "归还日"],
                ["陈亮", "西游记", "1", "4月12日"],
                ["林芳", "红楼梦", "2", "4月15日"],
                ["黄伟", "三国演义", "1", "4月18日"],
            ],
            "library",
        ),
        (
            "tr10",
            "天气观测记录",
            [
                ["日期", "天气", "气温", "风力"],
                ["5月1日", "晴", "26", "2级"],
                ["5月2日", "多云", "24", "3级"],
                ["5月3日", "小雨", "19", "4级"],
            ],
            "weather",
        ),
        (
            "tr11",
            "运动会成绩榜",
            [
                ["项目", "第一名", "成绩", "班级"],
                ["百米", "刘洋", "12秒", "三班"],
                ["跳远", "高飞", "5米", "二班"],
                ["铅球", "马强", "9米", "一班"],
            ],
            "sports",
        ),
        (
            "tr12",
            "医院门诊挂号统计",
            [
                ["科室", "上午", "下午", "合计"],
                ["内科", "45", "38", "83"],
                ["外科", "32", "29", "61"],
                ["儿科", "50", "41", "91"],
            ],
            "hospital",
        ),
        (
            "tr13",
            "超市进货清单",
            [
                ["品名", "规格", "件数", "进价"],
                ["大米", "25公斤", "20", "120"],
                ["食用油", "5升", "30", "65"],
                ["鸡蛋", "30枚", "15", "28"],
            ],
            "grocery",
        ),
        (
            "tr14",
            "员工考勤月表",
            [
                ["姓名", "出勤", "请假", "迟到"],
                ["王磊", "22", "1", "0"],
                ["李娜", "20", "2", "1"],
                ["张鹏", "21", "0", "2"],
            ],
            "attendance",
        ),
        (
            "tr15",
            "社区垃圾分类回收",
            [
                ["类别", "重量", "单位", "备注"],
                ["可回收", "120", "公斤", "纸塑"],
                ["厨余", "80", "公斤", "湿垃圾"],
                ["有害", "3", "公斤", "电池"],
            ],
            "recycling",
        ),
        (
            "tr16",
            "公交车班次表",
            [
                ["线路", "起点", "终点", "首班"],
                ["1路", "火车站", "公园", "6时"],
                ["3路", "学校", "商场", "6时"],
                ["5路", "医院", "机场", "5时"],
            ],
            "bus",
        ),
        (
            "tr17",
            "农业测产抽样",
            [
                ["地块", "作物", "亩产", "等级"],
                ["东地", "小麦", "450", "优"],
                ["西地", "玉米", "520", "良"],
                ["南地", "水稻", "480", "优"],
            ],
            "agriculture",
        ),
        (
            "tr18",
            "水电抄表记录",
            [
                ["户号", "用电", "用水", "月份"],
                ["101", "180", "12", "3月"],
                ["102", "210", "15", "3月"],
                ["201", "165", "10", "3月"],
            ],
            "utilities",
        ),
        (
            "tr19",
            "博物馆参观预约",
            [
                ["日期", "场次", "名额", "已约"],
                ["6月8日", "上午", "100", "86"],
                ["6月8日", "下午", "100", "92"],
                ["6月9日", "上午", "80", "80"],
            ],
            "museum",
        ),
        (
            "tr20",
            "药店库存盘点",
            [
                ["药品", "批号", "库存", "有效期"],
                ["感冒灵", "A12", "200", "2027年"],
                ["维生素", "B08", "150", "2026年"],
                ["绷带", "C03", "80", "2028年"],
            ],
            "pharmacy",
        ),
        (
            "tr21",
            "幼儿园食谱周表",
            [
                ["星期", "早餐", "午餐"],
                ["一", "牛奶面包", "米饭青菜"],
                ["二", "粥鸡蛋", "面条肉丝"],
                ["三", "豆浆馒头", "饺子汤"],
            ],
            "kindergarten",
        ),
        (
            "tr22",
            "消防器材巡检",
            [
                ["位置", "器材", "状态", "检查人"],
                ["一楼", "灭火器", "正常", "小刘"],
                ["二楼", "消防栓", "正常", "小陈"],
                ["三楼", "烟感", "待修", "小周"],
            ],
            "fire_safety",
        ),
        (
            "tr23",
            "快递站点收发量",
            [
                ["站点", "收件", "发件", "滞留"],
                ["东站", "320", "280", "12"],
                ["西站", "410", "390", "8"],
                ["南站", "265", "250", "15"],
            ],
            "parcel",
        ),
        (
            "tr24",
            "会议室预订表",
            [
                ["房间", "日期", "时段", "用途"],
                ["A厅", "7月1日", "上午", "培训"],
                ["B厅", "7月1日", "下午", "面试"],
                ["C厅", "7月2日", "全天", "研讨"],
            ],
            "meeting",
        ),
        (
            "tr25",
            "水质检测简报",
            [
                ["采样点", "酸碱度", "浊度", "结论"],
                ["水源", "7.2", "0.5", "合格"],
                ["出水", "7.0", "0.3", "合格"],
                ["管网", "6.8", "0.8", "关注"],
            ],
            "water_quality",
        ),
        (
            "tr26",
            "义工服务时长",
            [
                ["姓名", "次数", "时长", "积分"],
                ["何敏", "6", "18", "36"],
                ["罗涛", "4", "12", "24"],
                ["徐静", "8", "24", "48"],
            ],
            "volunteer",
        ),
        (
            "tr27",
            "停车场车位统计",
            [
                ["区域", "总位", "占用", "空闲"],
                ["地下", "200", "178", "22"],
                ["地面", "80", "65", "15"],
                ["临停", "40", "40", "0"],
            ],
            "parking",
        ),
        (
            "tr28",
            "语文阅读打卡",
            [
                ["学生", "篇数", "字数", "星级"],
                ["丁一", "5", "8000", "三星"],
                ["钱二", "7", "12000", "四星"],
                ["孙三", "4", "6000", "二星"],
            ],
            "reading",
        ),
        (
            "tr29",
            "工厂产量日报",
            [
                ["车间", "计划", "实际", "合格率"],
                ["一车间", "500", "512", "98"],
                ["二车间", "450", "440", "97"],
                ["三车间", "600", "605", "99"],
            ],
            "factory",
        ),
        (
            "tr30",
            "旅游团行程要点",
            [
                ["日序", "景点", "用餐", "住宿"],
                ["第一天", "故宫", "团餐", "北京"],
                ["第二天", "长城", "自理", "北京"],
                ["第三天", "颐和园", "团餐", "返程"],
            ],
            "tour",
        ),
    ]


def build_train_tables(*, tone_prob: float, rng: random.Random) -> list[dict]:
    tables = []
    for tid, title, grid, extra in train_table_specs():
        tables.append(
            make_table(tid, title, grid, tone_prob=tone_prob, rng=rng, notes_extra=extra)
        )
    return tables


def make_example(
    *,
    ex_id: str,
    kind: str,
    table_id: str,
    braille: str,
    zh: str,
) -> dict:
    return {
        "id": ex_id,
        "kind": kind,
        "table_id": table_id,
        "conversations": [
            {"from": "system", "value": SYSTEM},
            {
                "from": "human",
                "value": f"请把以下通用盲文转换成为汉字：\n盲文内容是:\n{braille}",
            },
            {"from": "gpt", "value": f"对应的中文内容是：\n{zh}"},
        ],
        "braille": braille,
        "zh": zh,
        "note": NOTE,
    }


def tables_to_examples(
    tables: list[dict],
    *,
    include_cells: bool = True,
    include_rows: bool = True,
    include_flat: bool = True,
    max_examples: int | None = None,
    rng: random.Random | None = None,
) -> list[dict]:
    examples: list[dict] = []
    for table in tables:
        tid = table["id"]
        cells = table["cells"]
        if include_cells:
            for ri, row in enumerate(cells):
                for ci, cell in enumerate(row):
                    examples.append(
                        make_example(
                            ex_id=f"{tid}-cell-r{ri}-c{ci}",
                            kind="cell",
                            table_id=tid,
                            braille=cell["braille"],
                            zh=cell["zh"],
                        )
                    )
        if include_rows:
            for ri, row in enumerate(cells):
                br = CELL_SEP.join(c["braille"] for c in row)
                zh = CELL_SEP.join(c["zh"] for c in row)
                examples.append(
                    make_example(
                        ex_id=f"{tid}-row-{ri}",
                        kind="row",
                        table_id=tid,
                        braille=br,
                        zh=zh,
                    )
                )
        if include_flat:
            examples.append(
                make_example(
                    ex_id=f"{tid}-flat",
                    kind="flat",
                    table_id=tid,
                    braille=table["flat_braille"],
                    zh=table["flat_zh"],
                )
            )

    if max_examples is not None and len(examples) > max_examples:
        rng = rng or random.Random(42)
        # Prefer keeping diversity: shuffle then take, but always keep all flats if possible.
        flats = [e for e in examples if e["kind"] == "flat"]
        others = [e for e in examples if e["kind"] != "flat"]
        rng.shuffle(others)
        keep_n = max(0, max_examples - len(flats))
        examples = flats + others[:keep_n]
        rng.shuffle(examples)

    return examples


def write_jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")


def write_readme_train(
    path: Path,
    *,
    n_tables: int,
    n_examples: int,
    by_kind: dict[str, int],
    tables_path: Path,
    train_path: Path,
    placeholder_path: Path,
) -> None:
    kind_lines = "\n".join(f"- `{k}`: {v}" for k, v in sorted(by_kind.items()))
    text = f"""# Training data (synthetic Braille tables)

## Counts

- **Tables:** {n_tables}
- **Instruction examples:** {n_examples}

### By kind

{kind_lines}

## Files

| Path | Role |
|------|------|
| `{tables_path.as_posix()}` | Expanded synthetic table grids (train set) |
| `{train_path.as_posix()}` | ShareGPT JSONL for LoRA (`cell` / `row` / `flat`) |
| `{placeholder_path.as_posix()}` | **Superseded** smoke set (~43 lines). Kept for reference; prefer `{train_path.name}` |

Eval holdout remains `data/synthetic_tables/tables.jsonl` (original 8 tables).

## Format

Each JSONL line:

```json
{{
  "id": "tr01-cell-r0-c0",
  "kind": "cell|row|flat",
  "table_id": "tr01",
  "conversations": [
    {{"from": "system", "value": "..."}},
    {{"from": "human", "value": "请把以下通用盲文转换成为汉字：\\n盲文内容是:\\n..."}},
    {{"from": "gpt", "value": "对应的中文内容是：\\n..."}}
  ],
  "braille": "...",
  "zh": "...",
  "note": "..."
}}
```

Separators match eval tables: cell ` | `, row ` || ` in flat fields.

## Regenerate

```bash
python scripts/build_train_tables_jsonl.py
```

## Limitations

Same as `data/synthetic_tables/README.md`: pypinyin approximation, no layout OCR,
synthetic only — expand with real photographed tables before production claims.
"""
    path.write_text(text, encoding="utf-8")


def annotate_placeholder(placeholder: Path) -> None:
    if not placeholder.is_file():
        return
    banner = placeholder.with_name("train_tables_placeholder.NOTE.txt")
    banner.write_text(
        "SUPERSEDED by data/train_tables.jsonl (expanded synthetic table ShareGPT set).\n"
        "This placeholder (~43 examples) remains only for historical smoke runs.\n"
        "Point configs/lora_tables.yaml data.path at data/train_tables.jsonl for real FT.\n",
        encoding="utf-8",
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--tables-out",
        type=Path,
        default=ROOT / "data" / "synthetic_tables_train",
    )
    parser.add_argument(
        "--train-out",
        type=Path,
        default=ROOT / "data" / "train_tables.jsonl",
    )
    parser.add_argument(
        "--readme-out",
        type=Path,
        default=ROOT / "data" / "README_train.md",
    )
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--tone-prob", type=float, default=0.10)
    parser.add_argument(
        "--max-examples",
        type=int,
        default=500,
        help="Cap total ShareGPT examples (default 500). Use 0 for no cap.",
    )
    parser.add_argument(
        "--min-examples",
        type=int,
        default=200,
        help="Warn if fewer than this many examples are produced.",
    )
    args = parser.parse_args()

    rng = random.Random(args.seed)
    tables = build_train_tables(tone_prob=args.tone_prob, rng=rng)
    write_outputs(args.tables_out, tables)

    max_ex = None if args.max_examples == 0 else args.max_examples
    examples = tables_to_examples(
        tables,
        include_cells=True,
        include_rows=True,
        include_flat=True,
        max_examples=max_ex,
        rng=random.Random(args.seed + 1),
    )
    write_jsonl(args.train_out, examples)

    by_kind: dict[str, int] = {}
    for ex in examples:
        by_kind[ex["kind"]] = by_kind.get(ex["kind"], 0) + 1

    placeholder = ROOT / "data" / "train_tables_placeholder.jsonl"
    write_readme_train(
        args.readme_out,
        n_tables=len(tables),
        n_examples=len(examples),
        by_kind=by_kind,
        tables_path=args.tables_out.relative_to(ROOT) / "tables.jsonl",
        train_path=args.train_out.relative_to(ROOT),
        placeholder_path=placeholder.relative_to(ROOT),
    )
    annotate_placeholder(placeholder)

    # Point config at the expanded set (keep placeholder note in comment).
    cfg = ROOT / "configs" / "lora_tables.yaml"
    if cfg.is_file():
        text = cfg.read_text(encoding="utf-8")
        if "train_tables_placeholder.jsonl" in text:
            text = text.replace(
                "path: data/train_tables_placeholder.jsonl",
                "path: data/train_tables.jsonl  # was train_tables_placeholder.jsonl",
            )
            cfg.write_text(text, encoding="utf-8")

    print(f"tables:   {len(tables)} → {args.tables_out / 'tables.jsonl'}")
    print(f"examples: {len(examples)} → {args.train_out}")
    print(f"by_kind:  {by_kind}")
    print(f"readme:   {args.readme_out}")
    if len(examples) < args.min_examples:
        print(
            f"WARNING: only {len(examples)} examples (< min {args.min_examples})",
            file=sys.stderr,
        )
        raise SystemExit(1)


if __name__ == "__main__":
    main()
