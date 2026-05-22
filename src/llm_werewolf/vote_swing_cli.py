"""CLI: analyze vote intention swings from a game directory or JSONL file."""

from pathlib import Path

import fire

from llm_werewolf.evaluation.vote_swing_analysis import (
    analyze_path,
    format_markdown_report,
    write_persuasion_artifacts,
)


def main(
    source: str,
    output_dir: str = "",
    print_report: bool = True,
) -> str:
    """Analyze vote_intentions.jsonl (or events.jsonl) and write persuasion reports.

    Args:
        source: Game directory, vote_intentions.jsonl, or events.jsonl path.
        output_dir: Where to write vote_swing_report.md (default: same as source dir).
        print_report: Print markdown to stdout.

    Returns:
        str: Output directory path.
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
