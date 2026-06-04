from pathlib import Path
import json

from llm_werewolf.agent_team.skill_support import skill_loader
from llm_werewolf.agent_team.skill_support.skill_loader import (
    parse_skill_belief_pattern,
    parse_skill_belief_signals,
    select_skills_for_belief,
)
from llm_werewolf.agent_team.skill_support.skill_markdown import (
    parse_frontmatter,
    extract_description,
    split_description_line,
    ensure_description_format,
    render_frontmatter_markdown,
)


def test_parse_frontmatter_keeps_simple_yaml_like_behavior() -> None:
    text = "---\nskill_id: wolf_demo\nnote: a:b:c\n---\n\n# Body\n"

    meta, body = parse_frontmatter(text)

    assert meta == {"skill_id": "wolf_demo", "note": "a:b:c"}
    assert body == "# Body"


def test_parse_frontmatter_falls_back_to_plain_body_on_broken_header() -> None:
    text = "---\nskill_id: wolf_demo\n# Body"

    meta, body = parse_frontmatter(text)

    assert meta == {}
    assert body == text


def test_description_line_and_when_to_use_share_fixed_format() -> None:
    description, body = split_description_line("描述：首夜狼队需要统一刀口\n\n# 正文")

    assert description == "首夜狼队需要统一刀口的情况下，使用该 skill"
    assert body == "# 正文"
    assert (
        ensure_description_format("首夜狼队需要统一刀口的情况下")
        == "首夜狼队需要统一刀口的情况下，使用该 skill"
    )


def test_extract_description_prefers_when_to_use_section() -> None:
    content = (
        "# 技能\n"
        "## 提取依据\n"
        "这段不是触发条件。\n"
        "## 何时使用\n"
        "- 首夜狼队私密频道，落刀前需要统一目标。\n"
        "## 行动\n"
        "先报建议刀口。"
    )

    assert (
        extract_description(content)
        == "首夜狼队私密频道，落刀前需要统一目标的情况下，使用该 skill"
    )


def test_render_frontmatter_markdown_skips_empty_values() -> None:
    rendered = render_frontmatter_markdown(
        {"skill_id": "wolf_demo", "status": "", "weight": "1.00"}, "# Body"
    )

    assert "skill_id: wolf_demo" in rendered
    assert "status:" not in rendered
    assert rendered.rstrip().endswith("# Body")


def _role_skill_dir(root: Path, role: str, version: str = "v1") -> Path:
    path = root / role / version
    path.mkdir(parents=True, exist_ok=True)
    return path


def _write_concentrated_skill(wolf_dir: Path) -> None:
    (wolf_dir / "wolf_concentrated.md").write_text(
        "---\n"
        "skill_id: wolf_concentrated\n"
        "prompt_role_key: wolf\n"
        "status: active\n"
        "belief_pattern: concentrated\n"
        "weight: 1.5\n"
        "---\n\n"
        "# 归票推动\n\n"
        "## 何时使用\n"
        "怀疑收敛于单一目标的情况下，使用该 skill\n\n"
        "## 公开行为\n"
        "顺势强化既有怀疑链，给出可跟票的公开理由。\n\n"
        "## 避免\n"
        "不要在票型已收敛时继续分票。\n",
        encoding="utf-8",
    )


def _write_dispersed_skill(wolf_dir: Path) -> None:
    (wolf_dir / "wolf_dispersed.md").write_text(
        "---\n"
        "skill_id: wolf_dispersed\n"
        "prompt_role_key: wolf\n"
        "status: active\n"
        "belief_pattern: dispersed\n"
        "weight: 1.1\n"
        "---\n\n"
        "# 带节奏\n\n"
        "## 何时使用\n"
        "场上狼信分散的情况下，使用该 skill\n\n"
        "## 公开行为\n"
        "主动收束票型，提出单一怀疑目标。\n",
        encoding="utf-8",
    )


def _write_signal_skill(wolf_dir: Path) -> None:
    (wolf_dir / "wolf_certain_vote.md").write_text(
        "---\n"
        "skill_id: wolf_certain_vote\n"
        "prompt_role_key: wolf\n"
        "status: active\n"
        "belief_signals: b1_target_certain,vote_intention_set\n"
        "weight: 2.0\n"
        "---\n\n"
        "# 铁票归票\n\n"
        "## 何时使用\n"
        "对单一目标狼信=1.0且投票意向已锁定时，使用该 skill\n",
        encoding="utf-8",
    )


def test_parse_skill_belief_pattern_from_frontmatter_and_body() -> None:
    meta = {"belief_pattern": "concentrated"}
    assert parse_skill_belief_pattern("", meta) == "concentrated"
    body = "## 信念分布依据\n- 分布模式：split_focus\n"
    assert parse_skill_belief_pattern(body, {}) == "split_focus"
    assert parse_skill_belief_signals({"belief_signals": "b1_target_certain,vote_intention_set"}) == frozenset(
        {"b1_target_certain", "vote_intention_set"}
    )


def test_detect_belief_signals_rules() -> None:
    from llm_werewolf.strategy.belief_format import detect_belief_signals
    from llm_werewolf.strategy.belief_state import BeliefState
    from llm_werewolf.strategy.decisions import BeliefEntry, SecondOrderEntry

    state = BeliefState(observer_seat=2, last_vote_seat=6)
    state.set_entry(BeliefEntry(target_seat=6, wolf_probability=1.0))
    state.set_entry(BeliefEntry(target_seat=3, wolf_probability=0.85))
    state.second_order[4] = SecondOrderEntry(observer_seat=4, suspects_me_as_wolf=1.0)
    state.second_order[5] = SecondOrderEntry(observer_seat=5, suspects_me_as_wolf=0.6)

    snapshot = detect_belief_signals(state)
    assert "b1_target_certain" in snapshot.signals
    assert "b1_two_above_0_8" in snapshot.signals
    assert "b2_observer_certain_on_me" in snapshot.signals
    assert "b2_multi_above_0_5_on_me" in snapshot.signals
    assert "vote_intention_set" in snapshot.signals


def test_select_skills_for_belief_matches_signals(tmp_path: Path, monkeypatch) -> None:
    from llm_werewolf.strategy.belief_state import BeliefState
    from llm_werewolf.strategy.decisions import BeliefEntry

    root = tmp_path / "skills"
    wolf_dir = _role_skill_dir(root, "wolf")
    _write_signal_skill(wolf_dir)
    _write_dispersed_skill(wolf_dir)
    monkeypatch.setattr(skill_loader, "agent_skills_root", lambda: root)
    skill_loader.list_role_skill_files.cache_clear()

    skills = skill_loader.load_role_skills("wolf", max_skills=10)
    state = BeliefState(observer_seat=2, last_vote_seat=6)
    state.set_entry(BeliefEntry(target_seat=6, wolf_probability=1.0))

    selected, pattern, active_signals = select_skills_for_belief(skills, state, top_k=2)
    assert "b1_target_certain" in active_signals
    assert [skill["skill_id"] for skill in selected] == ["wolf_certain_vote"]


def test_select_skills_for_belief_matches_pattern(tmp_path: Path, monkeypatch) -> None:
    from llm_werewolf.strategy.belief_state import BeliefState
    from llm_werewolf.strategy.decisions import BeliefEntry

    root = tmp_path / "skills"
    wolf_dir = _role_skill_dir(root, "wolf")
    _write_concentrated_skill(wolf_dir)
    _write_dispersed_skill(wolf_dir)
    monkeypatch.setattr(skill_loader, "agent_skills_root", lambda: root)
    skill_loader.list_role_skill_files.cache_clear()

    skills = skill_loader.load_role_skills("wolf", max_skills=10)
    state = BeliefState(observer_seat=2, last_vote_seat=6)
    state.set_entry(BeliefEntry(target_seat=6, wolf_probability=1.0))
    state.set_entry(BeliefEntry(target_seat=3, wolf_probability=0.33))

    selected, pattern, _active_signals = select_skills_for_belief(skills, state, top_k=2)
    assert pattern == "concentrated"
    assert [skill["skill_id"] for skill in selected] == ["wolf_concentrated"]


def test_sync_belief_context_injects_matched_skills(tmp_path: Path, monkeypatch) -> None:
    from llm_werewolf.agent_team.memory.runtime_memory_manager import RuntimeMemoryManager
    from llm_werewolf.game_runtime.config.memory_config import MemoryConfig
    from llm_werewolf.strategy.belief_state import BeliefState
    from llm_werewolf.strategy.decisions import BeliefEntry

    root = tmp_path / "skills"
    _write_concentrated_skill(_role_skill_dir(root, "villager"))
    monkeypatch.setattr(skill_loader, "agent_skills_root", lambda: root)
    skill_loader.list_role_skill_files.cache_clear()

    manager = RuntimeMemoryManager(
        event_logger=object(),
        role="villager",
        player_id="player_1",
        config=MemoryConfig(skill_belief_top_k=2),
    )
    state = BeliefState(observer_seat=1, last_vote_seat=6)
    state.set_entry(BeliefEntry(target_seat=6, wolf_probability=0.95))
    state.set_entry(BeliefEntry(target_seat=3, wolf_probability=0.2))

    manager.sync_belief_context(state)
    context = manager.get_context_for_decision()

    assert "【信念匹配的对局经验" in context
    assert "b1_top_above_0_7" in context or "当前触发信号" in context
    assert "wolf_concentrated" in context
    assert "顺势强化既有怀疑链" in context
    assert "wolf_concentrated" in manager._used_card_ids


REAL_RUN_DIR = Path("artifacts/runs/12p-doubao-20260531-203127")


def _belief_row_to_state(row: dict):
    from llm_werewolf.strategy.belief_state import BeliefState
    from llm_werewolf.strategy.decisions import BeliefEntry, SecondOrderEntry

    vote = row.get("vote_intention") or {}
    state = BeliefState(
        observer_seat=int(row.get("observer_seat", 0) or 0),
        last_vote_seat=int(vote.get("seat", 0) or 0),
    )
    for item in row.get("first_order") or []:
        if not isinstance(item, dict):
            continue
        state.set_entry(
            BeliefEntry(
                target_seat=int(item["target_seat"]),
                wolf_probability=float(item["wolf_probability"]),
                reason=item.get("reason"),
                note=item.get("note"),
            )
        )
    for item in row.get("second_order") or []:
        if not isinstance(item, dict):
            continue
        seat = int(item["observer_seat"])
        state.second_order[seat] = SecondOrderEntry(
            observer_seat=seat,
            suspects_me_as_wolf=float(item["suspects_me_as_wolf"]),
            reason=item.get("reason"),
            note=item.get("note"),
        )
    return state


def _load_beliefs_rows(run_dir: Path) -> list[dict]:
    path = run_dir / "beliefs.jsonl"
    rows: list[dict] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            rows.append(json.loads(line))
    return rows


def _resolve_belief_row(skill: dict, ctx: dict, beliefs: list[dict]) -> dict | None:
    pid = str(skill.get("source_player_id", ""))
    rnd = int(ctx.get("round_number", 0) or 0)
    anchor = str(ctx.get("anchor", ""))
    candidates = [
        row
        for row in beliefs
        if str(row.get("observer_id", "")) == pid
        and int(row.get("round", 0) or 0) == rnd
        and str(row.get("anchor", "")) == anchor
    ]
    if not candidates:
        return None
    if anchor == "after_speech" and skill.get("source_kind") == "persuasion_speech":
        for row in candidates:
            if str(row.get("speaker_id", "")) == pid:
                return row
        return None
    if len(candidates) == 1:
        return candidates[0]

    expected_top: set[int] = set()
    for item in ctx.get("b1_top") or []:
        if isinstance(item, dict) and item.get("seat") is not None:
            expected_top.add(int(item["seat"]))

    def _row_top_seats(row: dict) -> set[int]:
        entries: list[tuple[int, float]] = []
        for item in row.get("first_order") or []:
            if not isinstance(item, dict):
                continue
            try:
                entries.append((int(item["target_seat"]), float(item["wolf_probability"])))
            except (TypeError, ValueError):
                continue
        entries.sort(key=lambda pair: (-pair[1], pair[0]))
        observer_seat = int(row.get("observer_seat", 0) or 0)
        seats: set[int] = set()
        for seat, _ in entries:
            if seat != observer_seat:
                seats.add(seat)
            if len(seats) >= 4:
                break
        return seats

    return max(candidates, key=lambda row: len(expected_top & _row_top_seats(row)))


def _write_run_skill_md(path: Path, skill: dict) -> None:
    card = skill.get("skill_card") or {}
    ctx = (skill.get("evidence") or {}).get("belief_context") or {}
    lines = [
        "---",
        f"skill_id: {skill['skill_id']}",
        f"prompt_role_key: {skill.get('prompt_role_key', '')}",
        "status: active",
        f"weight: {skill.get('weight', 1.0)}",
    ]
    pattern = ctx.get("pattern")
    if pattern:
        lines.append(f"belief_pattern: {pattern}")
    signals = ctx.get("signals")
    if isinstance(signals, list) and signals:
        lines.append(f"belief_signals: {','.join(str(item) for item in signals)}")
    when_to_use = card.get("when_to_use")
    if when_to_use:
        lines.append(f"when_to_use: {when_to_use}")
    lines.extend(["---", "", f"# {card.get('title_zh', skill['skill_id'])}", ""])
    if card.get("public_behavior"):
        lines.append("## 公开行为")
        lines.append(str(card["public_behavior"]))
        lines.append("")
    if card.get("avoid"):
        lines.append("## 避免")
        lines.append(str(card["avoid"]))
        lines.append("")
    path.write_text("\n".join(lines), encoding="utf-8")


def test_auto_gen_belief_skills_from_real_run(tmp_path: Path, monkeypatch, capsys) -> None:
    """方案 A：用 12p 真实对局 role_skills + beliefs 验证自动生成 signal 与注入匹配。"""
    if not REAL_RUN_DIR.is_dir():
        import pytest

        pytest.skip(f"missing run dir {REAL_RUN_DIR}")

    from llm_werewolf.strategy.belief_format import detect_belief_signals_from_snapshot

    role_skills = json.loads((REAL_RUN_DIR / "role_skills.json").read_text(encoding="utf-8"))
    beliefs = _load_beliefs_rows(REAL_RUN_DIR)
    skills_root = tmp_path / "skills"
    report_lines: list[str] = ["=== 方案 A 真实对局 belief skill 注入测试 ===", ""]

    for skill in role_skills.get("skills") or []:
        skill["status"] = "active"
        ctx = (skill.get("evidence") or {}).get("belief_context")
        if isinstance(ctx, dict):
            row = _resolve_belief_row(skill, ctx, beliefs)
            if row is not None:
                snap = detect_belief_signals_from_snapshot(row)
                ctx["signals"] = sorted(snap.signals)
                ctx["signal_descriptions"] = list(snap.descriptions)
                ctx["pattern"] = ctx.get("pattern") or ""

        role_key = str(skill.get("prompt_role_key", "villager"))
        role_dir = skills_root / role_key / "v1"
        role_dir.mkdir(parents=True, exist_ok=True)
        _write_run_skill_md(role_dir / f"{skill['skill_id']}.md", skill)

    monkeypatch.setattr(skill_loader, "agent_skills_root", lambda: skills_root)
    skill_loader.list_role_skill_files.cache_clear()
    loaded = {
        role: skill_loader.load_role_skills(role, max_skills=20)
        for role in ("villager", "prophet", "guard", "witch")
    }

    matched_at_source = 0
    for skill in role_skills.get("skills") or []:
        ctx = (skill.get("evidence") or {}).get("belief_context")
        if not isinstance(ctx, dict):
            continue
        row = _resolve_belief_row(skill, ctx, beliefs)
        if row is None:
            report_lines.append(f"- {skill['skill_id']} | beliefs row NOT FOUND")
            continue
        state = _belief_row_to_state(row)
        role_key = str(skill.get("prompt_role_key"))
        pool = loaded.get(role_key) or []
        selected, pattern, active_signals = select_skills_for_belief(pool, state, top_k=3)
        hit = any(str(s.get("skill_id")) == skill["skill_id"] for s in selected)
        if hit:
            matched_at_source += 1
        context, _ = skill_loader.refresh_belief_skill_context(
            role_key, state, top_k=3, pool_size=20
        )
        rnd = int(ctx.get("round_number", 0) or 0)
        anchor = str(ctx.get("anchor", ""))
        report_lines.append(
            f"- {skill['skill_id']} @ R{rnd} {anchor} | pattern={pattern} | "
            f"skill_signals={ctx.get('signals')} | active={sorted(active_signals)} | "
            f"inject={'YES' if hit else 'NO'}"
        )
        if hit:
            assert skill["skill_id"] in context

    report_lines.append("")
    report_lines.append(
        f"生成时刻回匹配：{matched_at_source}/{len(role_skills.get('skills') or [])} 条 skill"
    )
    print("\n".join(report_lines))

    assert matched_at_source == len(role_skills.get("skills") or []), (
        "方案 A：生成时刻应全部回匹配"
    )