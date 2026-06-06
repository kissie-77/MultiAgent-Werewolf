"""CLI for leaderboard entry build, aggregation, and A/B compare."""

from __future__ import annotations

import argparse

from llm_werewolf.evaluation.leaderboard.ab_compare import write_ab_report
from llm_werewolf.evaluation.leaderboard.aggregator import write_leaderboard
from llm_werewolf.evaluation.leaderboard.entry_builder import build_entry, write_entry_bundle


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="werewolf-leaderboard")
    sub = parser.add_subparsers(dest="command", required=True)

    entry_parser = sub.add_parser("entry")
    entry_parser.add_argument("run_dir")
    entry_parser.add_argument("--version-id", default=None)
    entry_parser.add_argument("--model", default="unknown")
    entry_parser.add_argument("--prompt-version", default="unknown")
    entry_parser.add_argument("--skill-version", default="baseline")
    entry_parser.add_argument("--scenario", default="unknown")
    entry_parser.add_argument("--notes", nargs="*", default=None)
    entry_parser.add_argument("--previous-run-dir", default=None)
    entry_parser.add_argument("--previous-skill-snapshot-path", default=None)

    build_parser = sub.add_parser("build")
    build_parser.add_argument("root_dir")
    build_parser.add_argument("--output-dir", default=None)

    compare_parser = sub.add_parser("compare")
    compare_parser.add_argument("entry_a")
    compare_parser.add_argument("entry_b")
    compare_parser.add_argument("--output-dir", default=None)

    args = parser.parse_args(argv)

    if args.command == "entry":
        entry = build_entry(
            args.run_dir,
            version_id=args.version_id,
            model=args.model,
            prompt_version=args.prompt_version,
            skill_version=args.skill_version,
            scenario=args.scenario,
            notes=args.notes,
        )
        write_entry_bundle(
            args.run_dir,
            entry,
            previous_run_dir=args.previous_run_dir,
            previous_skill_snapshot_path=args.previous_skill_snapshot_path,
        )
        return 0

    if args.command == "build":
        write_leaderboard(args.root_dir, output_dir=args.output_dir)
        return 0

    if args.command == "compare":
        write_ab_report(args.entry_a, args.entry_b, output_dir=args.output_dir)
        return 0

    return 1


if __name__ == "__main__":
    raise SystemExit(main())
