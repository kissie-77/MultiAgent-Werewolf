"""Role prompt/skill libraries for catalog pages."""

from __future__ import annotations

from llm_werewolf.game_runtime.prompts.manager import PromptManager
from llm_werewolf.game_runtime.roles.registry import build_catalog_to_runtime_map
from llm_werewolf.interface.api.models.pages import (
    RoleAbility,
    RoleListItem,
    RolePromptEntry,
    RoleSkillEntry,
)

_CATALOG_TO_RUNTIME = build_catalog_to_runtime_map()

_ROLE_TAGLINES: dict[str, str] = {
    "Werewolf": "月下猎杀，白昼隐匿",
    "AlphaWolf": "王座陨落，带走一人",
    "WhiteWolf": "独狼之夜，刀向同族",
    "WolfBeauty": "魅惑殉情，扰乱人心",
    "GuardianWolf": "暗夜守护，护狼周全",
    "HiddenWolf": "查验为善，真身为狼",
    "BloodMoonApostle": "血月潜伏，终化狼形",
    "NightmareWolf": "梦魇封锁，神职失声",
    "Villager": "无术平民，凭票定乾坤",
    "Seer": "洞察黑夜，验明正邪",
    "Witch": "一瓶解药，一瓶毒药",
    "Hunter": "临终一枪，带走疑凶",
    "Guard": "连续守护，免疫狼刀",
    "Idiot": "翻牌免死，失票带队",
    "Elder": "抵挡一刀，勿被放逐",
    "Knight": "白昼决斗，一决生死",
    "Magician": "交换座位，扰乱刀口",
    "Cupid": "中立连理，恋人同生",
    "Raven": "标记放逐，双倍出局",
    "GraveyardKeeper": "验尸追刀，还原真相",
    "Thief": "首夜择牌，随营取胜",
    "Lover": "恋人羁绊，共赴终局",
}

_ROLE_DIFFICULTY: dict[str, str] = {
    "Villager": "EASY",
    "Idiot": "EASY",
    "WhiteWolf": "HEAVY",
    "Magician": "HEAVY",
    "Thief": "HEAVY",
    "BloodMoonApostle": "HEAVY",
    "WolfBeauty": "HEAVY",
    "NightmareWolf": "HEAVY",
}

_PROMPT_CATEGORY_LABELS = {
    "role_instruction": "身份指令",
    "core_principles": "核心原则",
    "phase_strategies": "阶段策略",
    "forbidden_actions": "禁忌行为",
    "examples": "范例话术",
    "suggestion": "行动建议",
}

# Keep rendered suggestion / instruction as one card, not line-split.
_SINGLE_BLOCK_PROMPT_FIELDS = frozenset({"role_instruction", "suggestion"})


def catalog_prompt_role_key(catalog_name: str) -> str:
    runtime_name = _CATALOG_TO_RUNTIME.get(catalog_name, catalog_name)
    return PromptManager.get_prompt_role_key(runtime_name)


def role_tagline(catalog_name: str) -> str:
    return _ROLE_TAGLINES.get(catalog_name, "命运刻印，待你解读")


def role_difficulty(catalog_name: str) -> str:
    return _ROLE_DIFFICULTY.get(catalog_name, "MEDIUM")


def _split_lines(text: str) -> list[str]:
    return [line.strip() for line in text.splitlines() if line.strip()]


def resolve_prompt_version(prompt_role_key: str) -> str:
    from llm_werewolf.strategy.registry.role_version_manifest import get_active_manifest

    return get_active_manifest().prompt_version_for(prompt_role_key)


def resolve_skill_version(prompt_role_key: str) -> str:
    from llm_werewolf.strategy.registry.role_version_manifest import get_active_manifest

    return get_active_manifest().skill_version_for(prompt_role_key)


def list_prompt_library(prompt_role_key: str) -> list[RolePromptEntry]:
    from llm_werewolf.strategy.registry.role_prompt_registry import get_role_card

    version = resolve_prompt_version(prompt_role_key)
    try:
        card = get_role_card(prompt_role_key, version)
    except FileNotFoundError:
        return []

    entries: list[RolePromptEntry] = []
    for field, label in _PROMPT_CATEGORY_LABELS.items():
        raw = str(card.get(field, "")).strip()
        if not raw:
            continue
        if field in _SINGLE_BLOCK_PROMPT_FIELDS:
            entries.append(
                RolePromptEntry(
                    id=field,
                    category=label,
                    title=label,
                    content=raw,
                    version=version,
                )
            )
            continue
        if field == "phase_strategies":
            for idx, line in enumerate(_split_lines(raw)):
                if ":" in line:
                    phase, rule = line.split(":", 1)
                    title = f"{phase.strip()} 策略"
                    content = rule.strip()
                else:
                    title = f"阶段策略 {idx + 1}"
                    content = line
                entries.append(
                    RolePromptEntry(
                        id=f"{field}_{idx}",
                        category=label,
                        title=title,
                        content=content,
                        version=version,
                    )
                )
            continue
        lines = _split_lines(raw)
        for idx, line in enumerate(lines):
            entries.append(
                RolePromptEntry(
                    id=f"{field}_{idx}" if len(lines) > 1 else field,
                    category=label,
                    title=label if len(lines) == 1 else f"{label} {idx + 1}",
                    content=line,
                    version=version,
                )
            )
    return entries


def list_skill_library(prompt_role_key: str) -> list[RoleSkillEntry]:
    from llm_werewolf.agent_team.skill_support.skill_loader import list_role_skill_files

    version = resolve_skill_version(prompt_role_key)
    entries: list[RoleSkillEntry] = []
    for path in list_role_skill_files(prompt_role_key, version):
        from llm_werewolf.agent_team.skill_support.skill_loader import _load_skill_file

        item = _load_skill_file(path)
        if item is None or item.get("status") == "deprecated":
            continue
        skill_id = str(item.get("skill_id", path.stem))
        description = str(item.get("description", "")).strip()
        if not description:
            body = str(item.get("body", "")).strip()
            description = body.split("\n", 1)[0][:200] if body else skill_id
        entries.append(
            RoleSkillEntry(
                id=skill_id,
                title=skill_id.replace("_", " "),
                description=description,
                status=str(item.get("status", "active")),
                weight=float(item.get("weight", 1.0)),
                version=str(item.get("skill_version", version)),
            )
        )
    entries.sort(key=lambda s: s.weight, reverse=True)
    return entries


def infer_abilities(
    catalog_name: str,
    instruction: str,
    *,
    has_night_action: bool,
) -> list[RoleAbility]:
    text = instruction.strip()
    if not text:
        return []
    timing = "NIGHT" if has_night_action else "PASSIVE"
    if any(k in text for k in ("白天", "决斗", "自爆", "发言轮")):
        timing = "DAY"
    elif any(k in text for k in ("无夜间", "无技能", "依靠发言")):
        timing = "PASSIVE"
    name = "夜间行动" if timing == "NIGHT" else "被动刻印" if timing == "PASSIVE" else "白昼权能"
    return [
        RoleAbility(
            name=name,
            description=text,
            timing=timing,
        )
    ]


def enrich_list_item(defn, base: RoleListItem) -> RoleListItem:
    prompt_key = catalog_prompt_role_key(defn.name)
    prompt_lib = list_prompt_library(prompt_key)
    skill_lib = list_skill_library(prompt_key)
    fields = base.model_dump()
    instruction = fields.get("instruction", "")
    if not instruction:
        from llm_werewolf.game_runtime.prompts.identity import get_identity_template

        instruction = get_identity_template(defn.name).get("instruction", "")
    short_desc = instruction[:120] + ("…" if len(instruction) > 120 else "")
    fields.update(
        {
            "runtime_name": _CATALOG_TO_RUNTIME.get(defn.name, defn.name),
            "prompt_role_key": prompt_key,
            "prompt_version": resolve_prompt_version(prompt_key),
            "skill_version": resolve_skill_version(prompt_key),
            "tagline": role_tagline(defn.name),
            "short_desc": short_desc,
            "difficulty": role_difficulty(defn.name),
            "prompt_count": len(prompt_lib),
            "skill_count": len(skill_lib),
        }
    )
    return RoleListItem(**fields)
