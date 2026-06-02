"""Format belief matrices for agent prompts."""

from __future__ import annotations

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
