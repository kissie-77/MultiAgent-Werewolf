"""Per-wolf private tactical belief panel (W-G / W-E).

Each werewolf maintains an isolated radar — updates from one wolf are never
merged into teammates' panels.
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING, Any
from pathlib import Path
from dataclasses import field, dataclass

from llm_werewolf.strategy.wolf.team import participates_in_wolf_team
from llm_werewolf.strategy.voting.seat import get_player_seat

if TYPE_CHECKING:
    from llm_werewolf.strategy.contracts.decisions import WolfCampDelta

WolfCampMindMap = dict[int, "WolfCampMindModel"]

_GOD_ROLES = ("Seer", "Witch", "Guard", "Hunter", "Villager")
_THREAT_WEIGHTS = {"Seer": 0.45, "Witch": 0.30, "Guard": 0.15, "Hunter": 0.05, "Villager": 0.05}


@dataclass
class GodRoleBelief:
    target_seat: int
    role_distribution: dict[str, float] = field(default_factory=dict)
    threat_score: float = 0.0
    priority: str = "watch"
    evidence: list[str] = field(default_factory=list)
    updated_round: int = 0
    contributors: list[int] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "target_seat": self.target_seat,
            "role_distribution": self.role_distribution,
            "threat_score": round(self.threat_score, 4),
            "priority": self.priority,
            "evidence": self.evidence,
            "updated_round": self.updated_round,
            "contributors": self.contributors,
        }


@dataclass
class WolfExposureProfile:
    wolf_seat: int
    overall_exposure: float = 0.0
    cells: dict[int, float] = field(default_factory=dict)
    suggested_stance: str = "hide"
    top_suspectors: list[dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "wolf_seat": self.wolf_seat,
            "overall_exposure": round(self.overall_exposure, 4),
            "cells": {str(k): round(v, 4) for k, v in self.cells.items()},
            "suggested_stance": self.suggested_stance,
            "top_suspectors": self.top_suspectors,
        }


@dataclass
class WolfCampMindModel:
    owner_seat: int = 0
    wolf_seats: list[int] = field(default_factory=list)
    god_role_intel: dict[int, GodRoleBelief] = field(default_factory=dict)
    exposure_radar: dict[int, WolfExposureProfile] = field(default_factory=dict)
    revision: int = 0
    history: list[dict[str, Any]] = field(default_factory=list)


def compute_threat_score(role_distribution: dict[str, float]) -> float:
    score = 0.0
    for role, weight in _THREAT_WEIGHTS.items():
        score += weight * float(role_distribution.get(role, 0.0))
    return min(1.0, max(0.0, score))


def _priority_from_threat(threat: float) -> str:
    if threat >= 0.75:
        return "kill_tonight"
    if threat >= 0.45:
        return "watch"
    return "low"


def _stance_from_exposure(overall: float) -> str:
    if overall >= 0.85:
        return "sacrifice"
    if overall >= 0.60:
        return "bus"
    if overall >= 0.45:
        return "counter"
    if overall >= 0.25:
        return "hide"
    return "push"


def _normalize_role_distribution(raw: dict[str, float]) -> dict[str, float]:
    merged = {role: max(0.0, float(raw.get(role, 0.0))) for role in _GOD_ROLES}
    total = sum(merged.values())
    if total <= 0:
        merged["Villager"] = 1.0
        return merged
    return {role: value / total for role, value in merged.items()}


def _merge_role_distribution(existing: dict[str, float], incoming: dict[str, float], *, weight: float) -> dict[str, float]:
    base = _normalize_role_distribution(existing)
    inc = _normalize_role_distribution(incoming)
    alpha = min(1.0, max(0.0, weight))
    merged = {role: (1 - alpha) * base[role] + alpha * inc[role] for role in _GOD_ROLES}
    return _normalize_role_distribution(merged)


def init_private_wolf_camp_mind(owner_seat: int, *, round_number: int = 0) -> WolfCampMindModel:
    """Create an empty private panel for a single werewolf seat."""
    model = WolfCampMindModel(owner_seat=owner_seat, wolf_seats=[owner_seat])
    model.exposure_radar[owner_seat] = WolfExposureProfile(wolf_seat=owner_seat)
    model.revision = 1
    _ = round_number
    return model


def init_wolf_camp_minds(wolf_players: list[Any], *, round_number: int = 0) -> WolfCampMindMap:
    """Initialize one isolated panel per werewolf player."""
    minds: WolfCampMindMap = {}
    for player in wolf_players:
        seat = get_player_seat(player)
        if seat is None:
            continue
        minds[seat] = init_private_wolf_camp_mind(seat, round_number=round_number)
    return minds


def init_wolf_camp_mind(wolf_players: list[Any], *, round_number: int = 0) -> WolfCampMindModel:
    """Initialize a private panel for the first wolf (tests / single-wolf helpers)."""
    for player in wolf_players:
        seat = get_player_seat(player)
        if seat is not None:
            return init_private_wolf_camp_mind(seat, round_number=round_number)
    return init_private_wolf_camp_mind(0, round_number=round_number)


def get_wolf_camp_mind(
    minds: WolfCampMindMap | WolfCampMindModel | None,
    player: Any,
) -> WolfCampMindModel | None:
    """Resolve the private panel visible to ``player``."""
    if minds is None or not is_wolf_player(player):
        return None
    if isinstance(minds, WolfCampMindModel):
        return minds
    seat = get_player_seat(player)
    if seat is None:
        return None
    return minds.get(seat)


def merge_wolf_camp_delta(
    model: WolfCampMindModel,
    delta: WolfCampDelta | None,
    *,
    contributor_seat: int,
    round_number: int,
) -> WolfCampMindModel:
    if delta is None:
        return model

    for item in delta.god_role_intel:
        existing = model.god_role_intel.get(item.target_seat)
        incoming_roles = item.delta or {}
        if existing is None:
            roles = _normalize_role_distribution(incoming_roles)
            belief = GodRoleBelief(
                target_seat=item.target_seat,
                role_distribution=roles,
                threat_score=compute_threat_score(roles),
                priority=_priority_from_threat(compute_threat_score(roles)),
                evidence=[item.reason] if item.reason else [],
                updated_round=round_number,
                contributors=[contributor_seat],
            )
            model.god_role_intel[item.target_seat] = belief
        else:
            merged = _merge_role_distribution(existing.role_distribution, incoming_roles, weight=0.55)
            existing.role_distribution = merged
            existing.threat_score = compute_threat_score(merged)
            existing.priority = _priority_from_threat(existing.threat_score)
            if item.reason:
                existing.evidence = ([*existing.evidence, item.reason])[-5:]
            existing.contributors = [contributor_seat]
            existing.updated_round = round_number

    for item in delta.exposure_radar:
        if item.wolf_seat != contributor_seat:
            continue
        profile = model.exposure_radar.get(contributor_seat)
        if profile is None:
            profile = WolfExposureProfile(wolf_seat=contributor_seat)
            model.exposure_radar[contributor_seat] = profile
        profile.cells[item.observer_seat] = max(
            profile.cells.get(item.observer_seat, 0.0),
            min(1.0, float(item.suspicion)),
        )
        profile.overall_exposure = max(profile.cells.values()) if profile.cells else 0.0
        profile.suggested_stance = _stance_from_exposure(profile.overall_exposure)
        top = sorted(profile.cells.items(), key=lambda pair: pair[1], reverse=True)[:3]
        profile.top_suspectors = [
            {"seat": seat, "suspicion": round(score, 4)} for seat, score in top if score > 0
        ]

    model.revision += 1
    model.history.append(
        {
            "round": round_number,
            "contributor_seat": contributor_seat,
            "owner_seat": model.owner_seat,
            "god_role_intel": {str(k): v.to_dict() for k, v in model.god_role_intel.items()},
            "exposure_radar": {str(k): v.to_dict() for k, v in model.exposure_radar.items()},
        }
    )
    return model


def format_wolf_camp_board(model: WolfCampMindModel) -> str:
    if model.revision == 0:
        return ""

    owner = model.owner_seat or (model.wolf_seats[0] if model.wolf_seats else 0)
    lines = [
        f"【个人战术雷达 · {owner}号狼 · 仅本人可见 · revision {model.revision}】",
        "",
        "■ 神职定位（本人推断）",
    ]
    ranked = sorted(model.god_role_intel.values(), key=lambda b: b.threat_score, reverse=True)
    if not ranked:
        lines.append("  （暂无）")
    else:
        for idx, belief in enumerate(ranked[:5], start=1):
            roles = belief.role_distribution
            lines.append(
                f"  {idx}. {belief.target_seat}号 threat={belief.threat_score:.2f} "
                f"Seer={roles.get('Seer', 0):.0%} Witch={roles.get('Witch', 0):.0%} "
                f"Guard={roles.get('Guard', 0):.0%} → {belief.priority}"
            )

    lines.extend(["", "■ 暴露雷达（本人）"])
    profile = model.exposure_radar.get(owner)
    if profile is None:
        lines.append("  （暂无）")
    else:
        top = profile.top_suspectors[0]["seat"] if profile.top_suspectors else "—"
        lines.append(
            f"  综合={profile.overall_exposure:.2f} 最疑={top} 建议={profile.suggested_stance}"
        )
    return "\n".join(lines)


def save_wolf_camp_history(model: WolfCampMindModel, path: str | Path) -> None:
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("w", encoding="utf-8") as handle:
        for item in model.history:
            handle.write(
                json.dumps(
                    {"schema": "wolf_camp_mind_v2", "owner_seat": model.owner_seat, **item},
                    ensure_ascii=False,
                )
            )
            handle.write("\n")


def save_all_wolf_camp_histories(minds: WolfCampMindMap, path: str | Path) -> None:
    """Persist per-wolf private panel histories to a single JSONL file."""
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("w", encoding="utf-8") as handle:
        for owner_seat in sorted(minds):
            model = minds[owner_seat]
            for item in model.history:
                handle.write(
                    json.dumps(
                        {"schema": "wolf_camp_mind_v2", "owner_seat": owner_seat, **item},
                        ensure_ascii=False,
                    )
                )
                handle.write("\n")


def is_wolf_player(player: Any) -> bool:
    return participates_in_wolf_team(player)
