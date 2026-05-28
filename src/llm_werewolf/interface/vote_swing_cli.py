"""CLI：从游戏目录或 JSONL 文件分析投票意向摇摆。"""

from pathlib import Path

import fire

from llm_werewolf.evaluation.core.vote_swing_analysis import (
    analyze_path,
    format_markdown_report,
    write_persuasion_artifacts,
)


def main(
    source: str,
    output_dir: str = "",
    print_report: bool = True,
) -> str:
    """分析 vote_intentions.jsonl（或 events.jsonl）并写入说服效果报告。

    Args:
        source: 游戏目录、vote_intentions.jsonl 或 events.jsonl 路径。
        output_dir: vote_swing_report.md 的输出目录（默认与 source 同目录）。
        print_report: 是否将 Markdown 报告打印到 stdout。

    Returns:
        str: 输出目录路径。
    """
    out = write_persuasion_artifacts(source, output_dir or None)
    if print_report:
        report = analyze_path(source)
        print(format_markdown_report(report))
    return str(out.resolve())


def entry() -> None:
    fire.Fire(main)


if __name__ == "__main__":
    entry()
