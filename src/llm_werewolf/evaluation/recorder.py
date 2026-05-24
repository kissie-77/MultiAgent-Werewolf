import json
import traceback
from datetime import datetime
from pathlib import Path
from typing import Any

from llm_werewolf.game_runtime.serialization import serialize_game_state
from llm_werewolf.game_runtime.types import Event, GameStateProtocol
from llm_werewolf.evaluation.models import CheckResult


class EvaluationRecorder:
    """负责把单局评测证据写入磁盘。

    recorder 不做任何判断，只做“留证据”：
    事件流、状态快照、异常、checker 结果都会写到同一个 game 目录下。
    这样即使 checker 以后升级，也可以拿旧产物重新分析。
    """

    def __init__(self, game_dir: str | Path) -> None:
        self.game_dir = Path(game_dir)
        self.game_dir.mkdir(parents=True, exist_ok=True)
        # 每个文件都是单局粒度，便于按 game_id 单独复盘。
        self.events_path = self.game_dir / "events.jsonl"
        self.snapshots_path = self.game_dir / "snapshots.jsonl"
        self.errors_path = self.game_dir / "errors.jsonl"
        self.checks_path = self.game_dir / "checks.json"
        self.vote_intentions_path = self.game_dir / "vote_intentions.jsonl"

    def record_event(self, event: Event) -> None:
        """追加一条游戏事件。

        使用 JSONL 是为了后续流式读取和增量写入；游戏很长时也不需要一次性加载。
        """
        self._append_jsonl(self.events_path, event.model_dump(mode="json"))

    def record_snapshot(self, game_state: GameStateProtocol | None, label: str) -> None:
        """保存某个时间点的 GameState 快照。

        `label` 用于说明快照时机，比如 after_setup / final。
        """
        if game_state is None:
            return

        payload = {
            "label": label,
            "timestamp": datetime.now().isoformat(),
            "state": serialize_game_state(game_state).model_dump(mode="json"),
        }
        self._append_jsonl(self.snapshots_path, payload)

    def record_error(
        self,
        exc: BaseException,
        phase: str | None = None,
        round_number: int | None = None,
        role_name: str | None = None,
    ) -> None:
        """保存异常及其上下文。

        runner 会捕获单局崩溃、超时以及 observation 构建错误。
        这里保留 traceback，便于定位具体源码位置；同时保留 phase/round/role 便于聚合。
        """
        payload = {
            "timestamp": datetime.now().isoformat(),
            "error_type": type(exc).__name__,
            "message": str(exc),
            "phase": phase,
            "round_number": round_number,
            "role_name": role_name,
            "traceback": "".join(traceback.format_exception(type(exc), exc, exc.__traceback__)),
        }
        self._append_jsonl(self.errors_path, payload)

    def record_vote_intentions(self, records: list[dict[str, Any]]) -> None:
        """追加与发言关联的投票意向记录，供说服分析。"""
        for record in records:
            self._append_jsonl(self.vote_intentions_path, record)

    def finalize_checks(self, results: list[CheckResult]) -> None:
        """写入本局所有 checker 结果。

        checks 用 JSON 数组保存，因为它通常较小，而且报告页面会一次性读取。
        """
        payload = [result.model_dump(mode="json") for result in results]
        self.checks_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")

    def _append_jsonl(self, path: Path, payload: dict[str, Any]) -> None:
        """以 UTF-8 JSONL 形式追加一条记录。"""
        with path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(payload, ensure_ascii=False))
            f.write("\n")
