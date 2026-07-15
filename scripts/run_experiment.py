"""User experiment runner for A/B/C comparison of three interaction modes.

Mode A: 纯文本聊天 (text only)
Mode B: 语音聊天 (voice only, uses TTS output)
Mode C: 语音 + 虚拟角色表情/动作 (full avatar pipeline)

Usage:
    python scripts/run_experiment.py          # random mode assignment
    python scripts/run_experiment.py --mode A # force a specific mode
"""

import argparse
import asyncio
import csv
import json
import random
import sys
from datetime import datetime, timezone
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from hai_avatar.app import build_mock_pipeline
from hai_avatar.logging_config import configure_logging

RESULTS_CSV = PROJECT_ROOT / "data" / "experiment_results.csv"

SURVEY_QUESTIONS = [
    {
        "id": "naturalness",
        "text": "这个交互方式有多自然？（1=非常生硬, 5=非常自然）",
        "min": 1,
        "max": 5,
    },
    {
        "id": "engagement",
        "text": "你有多大程度的参与感？（1=毫无参与, 5=全身心投入）",
        "min": 1,
        "max": 5,
    },
    {
        "id": "human_like",
        "text": "这个 AI 有多像一个真实的人？（1=完全不像, 5=非常像真人）",
        "min": 1,
        "max": 5,
    },
    {
        "id": "gesture_match",
        "text": "动作和表情是否匹配回复内容？（1=完全不匹配, 5=非常匹配）",
        "min": 1,
        "max": 5,
    },
    {
        "id": "latency_ok",
        "text": "系统响应延迟是否可以接受？（1=完全不能, 5=完全可以）",
        "min": 1,
        "max": 5,
    },
    {
        "id": "overall",
        "text": "总体评分（1=非常差, 5=非常好）",
        "min": 1,
        "max": 5,
    },
]

MODE_LABELS = {"A": "纯文本聊天", "B": "语音聊天", "C": "语音 + 虚拟角色表情/动作"}


def assign_mode(forced: str | None = None) -> str:
    if forced and forced.upper() in ("A", "B", "C"):
        return forced.upper()
    return random.choice(["A", "B", "C"])


def collect_survey(mode: str) -> dict[str, int]:
    print(f"\n{'=' * 40}")
    print(f"你体验的是 模式 {mode}: {MODE_LABELS.get(mode, mode)}")
    print("请根据刚才的体验回答以下问题：")
    results: dict[str, int] = {}
    for q in SURVEY_QUESTIONS:
        while True:
            try:
                value = int(input(f"\n{q['text']} [{q['min']}-{q['max']}]: "))
                if q["min"] <= value <= q["max"]:
                    results[q["id"]] = value
                    break
                print(f"请输入 {q['min']} 到 {q['max']} 之间的数字。")
            except ValueError:
                print("请输入数字。")
    return results


def save_result(mode: str, scores: dict[str, int], remarks: str = "") -> None:
    RESULTS_CSV.parent.mkdir(parents=True, exist_ok=True)
    is_new = not RESULTS_CSV.exists()
    with open(RESULTS_CSV, "a", newline="") as f:
        writer = csv.writer(f)
        if is_new:
            writer.writerow(["timestamp", "mode"] + [q["id"] for q in SURVEY_QUESTIONS] + ["remarks"])
        row = [datetime.now(timezone.utc).isoformat(), mode]
        row.extend(scores.get(q["id"], "") for q in SURVEY_QUESTIONS)
        row.append(remarks)
        writer.writerow(row)
    print(f"\n结果已保存到 {RESULTS_CSV}")


def print_stats() -> None:
    if not RESULTS_CSV.exists():
        print("暂无实验数据。")
        return
    rows: list[dict] = []
    with open(RESULTS_CSV, newline="") as f:
        for row in csv.DictReader(f):
            rows.append(row)
    if not rows:
        print("暂无实验数据。")
        return
    print(f"\n总计 {len(rows)} 条实验记录")

    by_mode: dict[str, list[dict]] = {}
    for r in rows:
        by_mode.setdefault(r["mode"], []).append(r)

    for mode in ["A", "B", "C"]:
        entries = by_mode.get(mode, [])
        if not entries:
            continue
        print(f"\n模式 {mode} ({MODE_LABELS.get(mode, mode)}) — {len(entries)} 人:")
        for q in SURVEY_QUESTIONS:
            vals = [int(e[q["id"]]) for e in entries if e.get(q["id"])]
            if vals:
                avg = sum(vals) / len(vals)
                print(f"  {q['id']}: avg={avg:.2f}")


async def run_pipeline_session(texts: list[str]) -> None:
    pipeline = build_mock_pipeline()
    for i, text in enumerate(texts):
        result = await pipeline.process(text)
        print(f"\n[{i + 1}] 你说: {text}")
        print(f"    AI回复: {result.reply_text}")
        print(f"    情绪: {result.avatar_command.emotion.value}  "
              f"表情: {result.avatar_command.expression.value}  "
              f"动作: {[g.value for g in result.avatar_command.gestures]}")
        if result.audio_path:
            print(f"    语音: {result.audio_path}")


def main() -> None:
    configure_logging()
    parser = argparse.ArgumentParser(description="用户实验工具")
    parser.add_argument("--mode", choices=["A", "B", "C"], help="强制指定实验模式")
    parser.add_argument("--stats", action="store_true", help="仅查看统计数据")
    args = parser.parse_args()

    if args.stats:
        print_stats()
        return

    mode = assign_mode(args.mode)
    print(f"分配模式: {mode} — {MODE_LABELS.get(mode, mode)}")
    print("请依次输入以下测试语句，体验 AI 的回应：")


    demo_texts = [
        "你好！很高兴认识你。",
        "我最近项目压力很大，不知道怎么开始。",
        "你能解释一下为什么分解任务会有效吗？",
        "谢谢你的建议，感觉好多了。再见！",
    ]

    if mode == "A":
        print("(纯文本模式 — 仅显示文字回复)")
    elif mode == "B":
        print("(语音模式 — 会播放 TTS 语音)")
    elif mode == "C":
        print("(完整模式 — 语音 + Avatar 表情和动作)")

    print("---")

    asyncio.run(run_pipeline_session(demo_texts))

    print("\n--- 体验结束 ---")

    scores = collect_survey(mode)
    remarks = input("\n有什么其他想说的？（直接回车跳过）: ").strip()
    save_result(mode, scores, remarks)

    total = len([r for r in csv.reader(open(RESULTS_CSV))]) - 1 if RESULTS_CSV.exists() else 0
    print(f"\n当前已有 {total} 条实验记录。")


if __name__ == "__main__":
    main()
