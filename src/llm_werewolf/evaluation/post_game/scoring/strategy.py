"""角色策略执行分（夜间技能、票型等）。"""

from __future__ import annotations

from typing import Any

from llm_werewolf.game_runtime.types.enums import Camp
from llm_werewolf.game_runtime.prompts.manager import PromptManager
from llm_werewolf.evaluation.post_game.run_context import RunContext, target_id_to_camp


def _role_key(role_name: str | None) -> str:
    if not role_name:
        return "villager"
    return PromptManager.get_prompt_role_key(role_name)


def build_strategy_scores(
    ctx: RunContext, events: list[dict[str, Any]] | None = None
) -> dict[str, dict[str, Any]]:
    scores: dict[str, dict[str, Any]] = {pid: {"total": 0, "details": []} for pid in ctx.roster}
    source = events if events is not None else ctx.events

    for event in source:
        etype = event.get("event_type")
        data = event.get("data") or {}
        actor = str(data.get("player_id", ""))
        if not actor or actor not in scores:
            continue

        entry = ctx.roster.get(actor)
        camp = entry.camp if entry else None

        if etype == "seer_checked":
            result = str(data.get("result", "")).lower()
            target_id = str(data.get("target_id", ""))
            target_camp = target_id_to_camp(target_id, ctx.roster)
            if target_camp == Camp.WEREWOLF.value or "werewolf" in result or "狼" in result:
                scores[actor]["total"] += 25
                scores[actor]["details"].append("seer_hit_wolf")
            elif target_camp == Camp.VILLAGER.value:
                scores[actor]["total"] -= 10
                scores[actor]["details"].append("seer_false_positive")

        elif etype == "witch_saved":
            target_id = str(data.get("target_id", ""))
            if target_id_to_camp(target_id, ctx.roster) == Camp.VILLAGER.value:
                scores[actor]["total"] += 20
                scores[actor]["details"].append("witch_save_good")

        elif etype in {"witch_poison_used", "witch_poisoned"}:
            target_id = str(data.get("target_id", ""))
            target_camp = target_id_to_camp(target_id, ctx.roster)
            if target_camp == Camp.WEREWOLF.value:
                scores[actor]["total"] += 25
                scores[actor]["details"].append("witch_poison_wolf")
            elif target_camp == Camp.VILLAGER.value:
                scores[actor]["total"] -= 15
                scores[actor]["details"].append("witch_poison_good")

        elif etype == "guard_protected":
            scores[actor]["total"] += 12
            scores[actor]["details"].append("guard_protect")

        elif etype == "vote_cast":
            voter = str(data.get("voter_id", ""))
            target = str(data.get("target_id", ""))
            if voter not in scores:
                continue
            vcamp = ctx.roster[voter].camp if voter in ctx.roster else None
            tcamp = target_id_to_camp(target, ctx.roster)
            if vcamp == Camp.WEREWOLF.value and tcamp == Camp.VILLAGER.value:
                scores[voter]["total"] += 8
                scores[voter]["details"].append("vote_push_villager")
            elif vcamp == Camp.VILLAGER.value and tcamp == Camp.WEREWOLF.value:
                scores[voter]["total"] += 10
                scores[voter]["details"].append("vote_push_wolf")
            elif vcamp and tcamp == vcamp:
                scores[voter]["total"] -= 12
                scores[voter]["details"].append("vote_harm_team")

    for pid, entry in ctx.roster.items():
        if _role_key(entry.role_name) in {"wolf", "wolf_king"} and scores[pid]["total"] == 0:
            if entry.camp == Camp.WEREWOLF.value:
                scores[pid]["total"] += 2
                scores[pid]["details"].append("wolf_participation")

    return scores
