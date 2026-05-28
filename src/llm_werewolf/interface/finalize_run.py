"""对局结束后的薄封装：写产物并触发 evaluation PostGame（尽量不影响其他模块）。"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

from llm_werewolf.evaluation.post_game import PostGameResult, run_post_game_pipeline

logger = logging.getLogger(__name__)


def _event_to_dict(event: Any) -> dict:
    return {
        "event_type": event.event_type.value,
        "timestamp": event.timestamp.isoformat(),
        "round_number": event.round_number,
        "phase": event.phase.value if hasattr(event.phase, "value") else str(event.phase),
        "message": event.message,
        "data": event.data,
        "visible_to": event.visible_to,
    }


def persist_run_artifacts(engine: Any, run_dir: Path) -> None:
    """将事件流与投票意向写入 run_dir（若尚未写入）。"""
    run_dir.mkdir(parents=True, exist_ok=True)

    events_path = run_dir / "events.jsonl"
    if not events_path.is_file() and hasattr(engine, "event_logger"):
        with events_path.open("w", encoding="utf-8") as fh:
            for event in engine.event_logger.events:
                fh.write(json.dumps(_event_to_dict(event), ensure_ascii=False) + "\n")

    state = getattr(engine, "game_state", None)
    if state is not None and state.vote_intention_tracker is not None:
        intentions_path = run_dir / "vote_intentions.jsonl"
        if not intentions_path.is_file():
            state.vote_intention_tracker.save_jsonl(intentions_path)


async def finalize_run(
    engine: Any,
    run_dir: str | Path,
    *,
    game_result_text: str | None = None,
    config_path: str | Path | None = None,
    prompt_version: str = "v2",
) -> PostGameResult:
    """每局结束后自动调用：持久化产物 + PostGame 流水线。"""
    path = Path(run_dir)
    persist_run_artifacts(engine, path)
    result = await run_post_game_pipeline(
        path,
        engine=engine,
        game_result_text=game_result_text,
        config_path=config_path,
        prompt_version=prompt_version,
    )
    if result.error:
        logger.error("PostGame pipeline failed for %s: %s", path, result.error)
    elif result.stage_errors:
        logger.warning("PostGame completed with stage errors for %s: %s", path, result.stage_errors)
    return result
