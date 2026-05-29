"""Run a werewolf game and export replay artifacts (console log + events JSONL)."""

from __future__ import annotations

import asyncio
import json
import sys
from datetime import datetime
from pathlib import Path

# Windows console: avoid GBK emoji crashes when piping output.
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

# Ensure src is on sys.path for direct script execution
_project_root = Path(__file__).resolve().parent.parent
_src_path = _project_root / "src"
if str(_src_path) not in sys.path:
    sys.path.insert(0, str(_src_path))

from llm_werewolf.game_runtime.env import load_project_dotenv

load_project_dotenv()

from llm_werewolf.evaluation.post_game.event_adapter import event_to_dict
from llm_werewolf.interface.bootstrap import prepare_game_roster, wire_agentscope_after_setup, create_information_hub
from llm_werewolf.game_runtime import GameEngine
from llm_werewolf.game_runtime.utils import load_config
from llm_werewolf.game_runtime.locale import Locale
from llm_werewolf.paths import RUNS_DIR
from llm_werewolf.ui.console_presenter import ConsolePresenter


async def run(config_path: Path, run_dir: Path) -> None:
    players_config = load_config(config_path=config_path)
    players, roles, game_config = prepare_game_roster(players_config)

    locale = Locale(players_config.language)
    engine = GameEngine(
        game_config,
        language=players_config.language,
        information_hub=create_information_hub(),
    )
    presenter = ConsolePresenter(locale)
    engine.on_event = presenter.present_event

    engine.setup_game(players=players, roles=roles)
    wire_agentscope_after_setup(engine, players_config)

    print(f"[run] config={config_path.resolve()} players={len(players)}")
    print(f"[run] log_dir={run_dir.resolve()}")

    result = await engine.play_game()
    print(result)

    events_path = run_dir / "events.jsonl"
    with events_path.open("w", encoding="utf-8") as fh:
        for event in engine.event_logger.events:
            fh.write(json.dumps(event_to_dict(event), ensure_ascii=False) + "\n")

    replay_md = run_dir / "game_replay.md"
    lines = [
        "# 对局复盘",
        "",
        f"- 配置: `{config_path}`",
        f"- 时间: {datetime.now().isoformat(timespec='seconds')}",
        f"- 结果: {result}",
        "",
        "## 事件流",
        "",
    ]
    if engine.game_state:
        lines.append("## 最终身份")
        lines.append("")
        for player in engine.game_state.players:
            status = "存活" if player.is_alive() else "死亡"
            lines.append(f"- {player.name}: {player.get_role_name()} ({status})")
        lines.append("")

    for event in engine.event_logger.events:
        lines.append(
            f"### 第{event.round_number}轮 · {event.phase.value} · {event.event_type.value}"
        )
        lines.append("")
        lines.append(event.message)
        if event.data:
            lines.append("")
            lines.append(f"```json\n{json.dumps(event.data, ensure_ascii=False, indent=2)}\n```")
        lines.append("")

    replay_md.write_text("\n".join(lines), encoding="utf-8")

    from llm_werewolf.interface.finalize_run import finalize_run

    post = await finalize_run(
        engine,
        run_dir,
        game_result_text=result,
        config_path=config_path,
        prompt_version=players_config.prompt_version,
    )
    if post.error:
        print(f"[run] post-game warning: {post.error}")

    print(f"[run] events -> {events_path}")
    print(f"[run] replay -> {replay_md}")
    print(f"[run] post-game artifacts -> {', '.join(post.artifacts)}")


def main() -> None:
    config = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("configs/llm-12p-doubao.yaml")
    label = config.stem.replace("llm-", "")
    ts = datetime.now().strftime("%Y%m%d-%H%M%S")
    run_dir = RUNS_DIR / f"{label}-{ts}"
    run_dir.mkdir(parents=True, exist_ok=True)

    log_path = run_dir / "game_log.txt"
    tee = log_path.open("w", encoding="utf-8")

    class Tee:
        def write(self, data: str) -> None:
            sys.__stdout__.write(data)
            tee.write(data)

        def flush(self) -> None:
            sys.__stdout__.flush()
            tee.flush()

    sys.stdout = Tee()  # type: ignore[assignment]
    try:
        asyncio.run(run(config, run_dir))
    finally:
        tee.close()
        sys.stdout = sys.__stdout__
        print(f"[run] console log -> {log_path.resolve()}")


if __name__ == "__main__":
    main()
