"""Format belief matrices for agent prompts."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from llm_werewolf.strategy.belief_state import BeliefState, BeliefSnapshotRecord
from llm_werewolf.strategy.wolf_camp_mind import WolfCampMindModel, format_wolf_camp_board, is_wolf_player

if TYPE_CHECKING:
    from llm_werewolf.game_runtime.types import PlayerProtocol


def _format_first_order_lines(state: BeliefState, *, max_entries: int) -> list[str]:
    entries = sorted(
        state.first_order.values(),
        key=lambda entry: (-entry.wolf_probability, entry.target_seat),
    )[:max_entries]
    parts: list[str] = []
    for entry in entries:
        note = entry.note or ""
        suffix = f" ({note})" if note else ""
        parts.append(f"{entry.target_seat}→{entry.wolf_probability:.2f}{suffix}")
    return parts


def _format_second_order_lines(state: BeliefState, *, max_entries: int) -> list[str]:
    parts: list[str] = []
    for entry in sorted(state.second_order.values(), key=lambda item: (-item.suspects_me_as_wolf, item.observer_seat))[
        :max_entries
    ]:
        note = entry.note or ""
        suffix = f" ({note})" if note else ""
        parts.append(f"{entry.observer_seat}→{entry.suspects_me_as_wolf:.2f}{suffix}")
    return parts


def format_belief_context(state: BeliefState | None, *, max_entries: int = 12) -> str:
    """Read-only belief summary for speech / formal vote prompts."""
    if state is None or not state.first_order:
        return ""

    lines = ["【当前信念矩阵 · 仅自己可见】"]
    first_parts = _format_first_order_lines(state, max_entries=max_entries)
    if first_parts:
        lines.append(f"一阶（狼概率，高→低）: {', '.join(first_parts)}")

    if state.second_order:
        second_parts = _format_second_order_lines(state, max_entries=max_entries)
        if second_parts:
            lines.append(f"二阶（他人疑我，高→低）: {', '.join(second_parts)}")

    if state.last_vote_seat is not None:
        if state.last_vote_seat == 0:
            lines.append("当前投票意向: 观望（seat=0）")
        else:
            lines.append(f"当前投票意向: {state.last_vote_seat} 号")

    lines.append("请结合公开信息与上述信念做出发言或投票决策。")
    return "\n".join(lines)


def format_belief_summary(state: BeliefState | None, *, max_entries: int = 8) -> str:
    """Mind-state collection: show current matrix + partial-update rules."""
    if state is None or not state.first_order:
        return ""

    lines = ["【当前信念矩阵 · 仅自己可见】"]
    first_parts = _format_first_order_lines(state, max_entries=max_entries)
    if first_parts:
        lines.append(f"一阶（狼概率）: {', '.join(first_parts)}")

    if state.second_order:
        second_parts = _format_second_order_lines(state, max_entries=max_entries)
        if second_parts:
            lines.append(f"二阶（他人疑我）: {', '.join(second_parts)}")

    if state.last_vote_seat is not None:
        if state.last_vote_seat == 0:
            lines.append("上一帧投票意向: 观望（seat=0）")
        else:
            lines.append(f"上一帧投票意向: {state.last_vote_seat} 号")

    lines.extend([
        "",
        "【信念/意向更新规则】",
        "- first_order / second_order 仅填写需要修改的条目；无变化则留空数组 []。",
        "- 每条信念修改必须含 reason，说明依据。",
        "- 若 seat 与上一帧不同，必须在顶层 reason 说明改票理由。",
    ])
    return "\n".join(lines)


def format_wolf_camp_context(model: WolfCampMindModel | None) -> str:
    if model is None or model.revision == 0:
        return ""
    return format_wolf_camp_board(model)


def build_agent_belief_context(
    player: PlayerProtocol,
    *,
    alive: list[PlayerProtocol],
    wolf_camp_mind: WolfCampMindModel | None = None,
) -> str:
    from llm_werewolf.strategy.belief_updater import ensure_agent_belief_state

    parts: list[str] = []
    state = ensure_agent_belief_state(player, alive)
    belief_ctx = format_belief_context(state)
    if belief_ctx:
        parts.append(belief_ctx)
    if is_wolf_player(player) and wolf_camp_mind is not None:
        wolf_ctx = format_wolf_camp_context(wolf_camp_mind)
        if wolf_ctx:
            parts.append(wolf_ctx)
    return "\n\n".join(parts)


def sync_player_belief_memory(
    player: PlayerProtocol,
    *,
    alive: list[PlayerProtocol],
    wolf_camp_mind: WolfCampMindModel | None = None,
) -> None:
    """Write latest B1/B2 (+ wolf panel) into the player's WorkingMemory."""
    from llm_werewolf.strategy.belief_updater import ensure_agent_belief_state

    agent = player.agent
    if agent is None:
        return
    memory_manager = getattr(agent, "memory_manager", None)
    if memory_manager is None:
        return

    state = ensure_agent_belief_state(player, alive)
    wolf_text = ""
    if is_wolf_player(player) and wolf_camp_mind is not None:
        wolf_text = format_wolf_camp_context(wolf_camp_mind)
    memory_manager.sync_belief_context(state, wolf_camp_text=wolf_text)


def sync_all_belief_memories(
    players: list[PlayerProtocol],
    *,
    alive: list[PlayerProtocol],
    wolf_camp_mind: WolfCampMindModel | None = None,
) -> None:
    for player in players:
        if not player.is_alive():
            continue
        sync_player_belief_memory(player, alive=alive, wolf_camp_mind=wolf_camp_mind)


def append_working_memory_context(
    parts: list[str], player: PlayerProtocol, *, include_belief: bool = True
) -> None:
    """Append WorkingMemory prompt block when memory_manager is present."""
    agent = player.agent
    if agent is None:
        return
    memory_manager = getattr(agent, "memory_manager", None)
    if memory_manager is None:
        return
    memory_context = memory_manager.get_context_for_decision(include_belief=include_belief)
    if memory_context:
        parts.append(memory_context)


def append_belief_context_fallback(
    parts: list[str],
    player: PlayerProtocol,
    *,
    alive: list[PlayerProtocol],
    wolf_camp_mind: WolfCampMindModel | None,
    belief_enabled: bool,
) -> None:
    """Direct prompt injection when WorkingMemory is unavailable (e.g. DemoAgent)."""
    if not belief_enabled:
        return
    if player.agent and getattr(player.agent, "memory_manager", None):
        return
    belief_ctx = build_agent_belief_context(player, alive=alive, wolf_camp_mind=wolf_camp_mind)
    if belief_ctx:
        parts.append(belief_ctx)


def _top_first_order_summary(first_order: list[dict], *, limit: int = 4) -> str:
    entries = []
    for row in first_order:
        seat = row.get("target_seat")
        prob = row.get("wolf_probability")
        if seat is None or prob is None:
            continue
        try:
            entries.append((int(seat), float(prob)))
        except (TypeError, ValueError):
            continue
    entries.sort(key=lambda item: (-item[1], item[0]))
    if not entries:
        return "—"
    return ", ".join(f"{seat}:{prob:.2f}" for seat, prob in entries[:limit])


def _top_second_order_summary(second_order: list[dict], *, limit: int = 3) -> str:
    entries = []
    for row in second_order:
        seat = row.get("observer_seat")
        prob = row.get("suspects_me_as_wolf")
        if seat is None or prob is None:
            continue
        try:
            prob_f = float(prob)
        except (TypeError, ValueError):
            continue
        if prob_f <= 0.05:
            continue
        entries.append((int(seat), prob_f))
    entries.sort(key=lambda item: (-item[1], item[0]))
    if not entries:
        return "—"
    return ", ".join(f"{seat}:{prob:.2f}" for seat, prob in entries[:limit])


def format_belief_batch_log(
    records: list[BeliefSnapshotRecord],
    *,
    round_number: int,
    phase: str,
    anchor: str,
    speaker_name: str | None,
    player_names: dict[str, str],
) -> str:
    """God-view compact belief matrix block for console / game_log."""
    if anchor == "initial":
        title = f"【信念矩阵 · 第{round_number}轮 · 讨论初始】"
    elif speaker_name:
        title = f"【信念矩阵 · 第{round_number}轮 · 听完 {speaker_name} 发言后】"
    else:
        title = f"【信念矩阵 · 第{round_number}轮 · {phase} · {anchor}】"

    lines = [title]
    for record in sorted(records, key=lambda item: item.observer_seat):
        name = player_names.get(record.observer_id, record.observer_id)
        vote = f"意向→{record.vote_seat}号" if record.vote_seat > 0 else "意向→观望"
        if record.vote_reason:
            reason = record.vote_reason.strip().replace("\n", " ")
            if len(reason) > 40:
                reason = reason[:37] + "..."
            vote = f"{vote} ({reason})"
        b1 = _top_first_order_summary(record.first_order)
        b2 = _top_second_order_summary(record.second_order)
        lines.append(f"  {record.observer_seat}号 {name} | {vote} | B1[{b1}] | B2[{b2}]")
    return "\n".join(lines)


@dataclass
class BeliefPatternSummary:
    pattern: str = ""
    when_clause: str = ""
    vote_seat: int = 0
    b1_top: list[tuple[int, float]] = field(default_factory=list)
    b2_high: list[tuple[int, float]] = field(default_factory=list)
    signals: frozenset[str] = field(default_factory=frozenset)
    signal_descriptions: tuple[str, ...] = field(default_factory=tuple)


@dataclass(frozen=True)
class BeliefSignalSnapshot:
    signals: frozenset[str]
    descriptions: tuple[str, ...]


def _count_b1_above(entries: list[tuple[int, float]], threshold: float) -> int:
    return sum(1 for _, prob in entries if prob > threshold)


def _any_b1_at_least(entries: list[tuple[int, float]], threshold: float) -> bool:
    return any(prob >= threshold for _, prob in entries)


def build_belief_signal_snapshot(
    *,
    observer_seat: int,
    vote_seat: int,
    b1_non_self: list[tuple[int, float]],
    b2_entries: list[tuple[int, float]],
    b1_self_prob: float | None = None,
) -> BeliefSignalSnapshot:
    """Rule-based belief triggers shared by runtime injection and PostGame skill generation."""
    b1_sorted = sorted(b1_non_self, key=lambda item: (-item[1], item[0]))
    b2_sorted = sorted(b2_entries, key=lambda item: (-item[1], item[0]))
    active: list[str] = []
    descriptions: list[str] = []

    def _add(signal_id: str, description: str) -> None:
        active.append(signal_id)
        descriptions.append(description)

    if _any_b1_at_least(b1_sorted, 0.999):
        _add("b1_target_certain", "存在目标狼信=1.0")
    if _count_b1_above(b1_sorted, 0.8) >= 2:
        _add("b1_two_above_0_8", "至少两个目标狼信>0.8")
    if _count_b1_above(b1_sorted, 0.5) >= 2:
        _add("b1_multi_above_0_5", "至少两个目标狼信>0.5")
    if b1_sorted and b1_sorted[0][1] >= 0.7:
        _add("b1_top_above_0_7", f"最高目标狼信≥0.7（{b1_sorted[0][1]:.2f}）")
    if b1_self_prob is not None and b1_self_prob >= 0.999:
        _add("b1_self_wolf_certain", "自问狼信=1.0")
    if _any_b1_at_least(b2_sorted, 0.999):
        _add("b2_observer_certain_on_me", "存在他人对你判狼=1.0")
    if _count_b1_above(b2_sorted, 0.5) >= 2:
        _add("b2_multi_above_0_5_on_me", "不止一人对你狼信>0.5")
    if b2_sorted and b2_sorted[0][1] > 0.8:
        _add("b2_top_above_0_8_on_me", f"最高他人疑狼>0.8（{b2_sorted[0][1]:.2f}）")
    if vote_seat > 0:
        _add("vote_intention_set", "投票意向已锁定到单一座位")
    elif b1_sorted and b1_sorted[0][1] < 0.4:
        _add("vote_watching", "意向观望且狼信未收敛")

    return BeliefSignalSnapshot(signals=frozenset(active), descriptions=tuple(descriptions))


def detect_belief_signals(state: BeliefState) -> BeliefSignalSnapshot:
    b1_all = [(entry.target_seat, entry.wolf_probability) for entry in state.first_order.values()]
    b1_non_self = [(seat, prob) for seat, prob in b1_all if seat != state.observer_seat]
    b1_self_prob = next((prob for seat, prob in b1_all if seat == state.observer_seat), None)
    b2_entries = [
        (entry.observer_seat, entry.suspects_me_as_wolf) for entry in state.second_order.values()
    ]
    vote_seat = state.last_vote_seat if state.last_vote_seat is not None else 0
    return build_belief_signal_snapshot(
        observer_seat=state.observer_seat,
        vote_seat=vote_seat,
        b1_non_self=b1_non_self,
        b2_entries=b2_entries,
        b1_self_prob=b1_self_prob,
    )


def detect_belief_signals_from_snapshot(snapshot: dict[str, object]) -> BeliefSignalSnapshot:
    observer_seat = int(snapshot.get("observer_seat", 0) or 0)
    vote_info = snapshot.get("vote_intention") or {}
    vote_seat = 0
    if isinstance(vote_info, dict):
        try:
            vote_seat = int(vote_info.get("seat", 0) or 0)
        except (TypeError, ValueError):
            vote_seat = 0

    b1_all: list[tuple[int, float]] = []
    for row in snapshot.get("first_order") or []:
        if not isinstance(row, dict):
            continue
        try:
            seat = int(row.get("target_seat", 0) or 0)
            prob = float(row.get("wolf_probability", 0.0))
        except (TypeError, ValueError):
            continue
        if seat > 0:
            b1_all.append((seat, prob))

    b1_non_self = [(seat, prob) for seat, prob in b1_all if seat != observer_seat]
    b1_self_prob = next((prob for seat, prob in b1_all if seat == observer_seat), None)
    b2_entries: list[tuple[int, float]] = []
    for row in snapshot.get("second_order") or []:
        if not isinstance(row, dict):
            continue
        try:
            seat = int(row.get("observer_seat", 0) or 0)
            prob = float(row.get("suspects_me_as_wolf", 0.0))
        except (TypeError, ValueError):
            continue
        if seat > 0:
            b2_entries.append((seat, prob))

    return build_belief_signal_snapshot(
        observer_seat=observer_seat,
        vote_seat=vote_seat,
        b1_non_self=b1_non_self,
        b2_entries=b2_entries,
        b1_self_prob=b1_self_prob,
    )


def refresh_player_belief_skills(
    player: PlayerProtocol,
    *,
    alive: list[PlayerProtocol],
    wolf_camp_mind: WolfCampMindModel | None = None,
) -> None:
    """Refresh belief-matched skills immediately before a speech/decision turn."""
    from llm_werewolf.strategy.belief_updater import ensure_agent_belief_state

    agent = player.agent
    if agent is None:
        return
    memory_manager = getattr(agent, "memory_manager", None)
    if memory_manager is None:
        return
    if getattr(memory_manager.config, "skill_injection_mode", "static") != "belief":
        return
    state = ensure_agent_belief_state(player, alive)
    memory_manager.refresh_belief_skills(state)


def _belief_prob_summary(probs: list[float], *, limit: int = 3) -> str:
    if not probs:
        return "-"
    return ", ".join(f"{prob:.2f}" for prob in probs[:limit])


def detect_belief_pattern(
    b1_top: list[tuple[int, float]],
    b2_high: list[tuple[int, float]],
    vote_seat: int,
) -> str:
    if not b1_top:
        return "unknown"

    top_prob = b1_top[0][1]
    second_prob = b1_top[1][1] if len(b1_top) > 1 else 0.0

    if len(b1_top) >= 2 and top_prob >= 0.45 and abs(top_prob - second_prob) <= 0.12:
        return "split_focus"
    if top_prob >= 0.7:
        return "concentrated"
    if top_prob >= 0.45 and (top_prob - second_prob) >= 0.12:
        return "converging"
    if len(b1_top) >= 3 and top_prob < 0.45:
        spread = top_prob - b1_top[2][1]
        if spread <= 0.12:
            return "dispersed"
    if vote_seat <= 0 and top_prob < 0.4:
        return "undecided"
    if b2_high and b2_high[0][1] >= 0.5:
        return "self_exposed"
    return "mixed"


def _b1_entries_from_state(state: BeliefState) -> list[tuple[int, float]]:
    entries = [
        (entry.target_seat, entry.wolf_probability)
        for entry in state.first_order.values()
        if entry.target_seat != state.observer_seat
    ]
    entries.sort(key=lambda item: (-item[1], item[0]))
    return entries


def _b2_entries_from_state(state: BeliefState, *, min_prob: float = 0.25) -> list[tuple[int, float]]:
    entries: list[tuple[int, float]] = []
    for entry in state.second_order.values():
        if entry.suspects_me_as_wolf < min_prob:
            continue
        entries.append((entry.observer_seat, entry.suspects_me_as_wolf))
    entries.sort(key=lambda item: (-item[1], item[0]))
    return entries


def summarize_belief_pattern(state: BeliefState | None) -> BeliefPatternSummary | None:
    if state is None or not state.first_order:
        return None

    vote_seat = state.last_vote_seat if state.last_vote_seat is not None else 0
    b1_top = _b1_entries_from_state(state)
    b2_high = _b2_entries_from_state(state)
    pattern = detect_belief_pattern(b1_top, b2_high, vote_seat)
    signal_snapshot = detect_belief_signals(state)

    parts: list[str] = ["信念分布（运行时）"]
    if pattern == "dispersed":
        parts.append(f"场上狼信分散（Top狼信 {_belief_prob_summary([p for _, p in b1_top])}）")
    elif pattern == "split_focus":
        parts.append(f"怀疑焦点分散（Top狼信 {_belief_prob_summary([p for _, p in b1_top[:2]])}）")
    elif pattern == "concentrated" and b1_top:
        parts.append(f"对单一目标狼信极高（{b1_top[0][1]:.2f}）")
    elif pattern == "converging" and b1_top:
        parts.append(f"怀疑收敛于单一目标（狼信{b1_top[0][1]:.2f}）")
    elif pattern == "undecided":
        parts.append(f"信息不足、狼信未收敛（Top狼信 {_belief_prob_summary([p for _, p in b1_top])}）")
    elif b1_top:
        parts.append(f"Top狼信 {_belief_prob_summary([p for _, p in b1_top])}")

    if vote_seat > 0:
        parts.append("投票意向已收敛到单一目标")
    else:
        parts.append("意向仍观望")

    b2_text = _belief_prob_summary([p for _, p in b2_high], limit=2)
    if b2_text != "-":
        parts.append(f"自身被他人高怀疑（B2强度 {b2_text}）")

    usage_hints = {
        "dispersed": "适合主动带节奏、收束票型",
        "split_focus": "适合在双怀疑位中择一归票或拆局",
        "concentrated": "适合顺势推动既有怀疑链",
        "converging": "适合强化归票理由、避免分票",
        "undecided": "适合先整理公开矛盾再定目标",
        "self_exposed": "适合先洗清自身嫌疑再带票",
        "mixed": "适合结合公开信息与票型缺口发言",
    }
    parts.append(usage_hints.get(pattern, usage_hints["mixed"]))
    if signal_snapshot.descriptions:
        parts.append("触发信号：" + "；".join(signal_snapshot.descriptions))

    return BeliefPatternSummary(
        pattern=pattern,
        when_clause="；".join(parts),
        vote_seat=vote_seat,
        b1_top=b1_top,
        b2_high=b2_high,
        signals=signal_snapshot.signals,
        signal_descriptions=signal_snapshot.descriptions,
    )
