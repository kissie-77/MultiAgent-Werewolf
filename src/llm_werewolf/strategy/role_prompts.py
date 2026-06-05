"""狼人杀角色策略提示词。

Prompt：每身份小包 strategy/prompts/roles/<role>/<version>/ + shared agent_base.md。
流程文案：strategy/prompts/phase/<version>/（GamePrompts）。
Plan 策略：strategy/prompts/plans/<version>/（PlanStrategies）。
发言/遗言等圆桌任务：JSON Schema（SpeechDecision / generate_response）。
选座、投票、女巫用药：SeatChoiceDecision / YesNoDecision（bridge 仍支持 [[ ]] 回退解析）。
"""

from llm_werewolf.strategy.phase_prompt_registry import (
    hydrate_prompt_namespace,
    load_plan_bundle,
    load_phase_prompts,
    load_seat_action_map,
    resolve_latest_phase_version,
    resolve_latest_plan_version,
)
from llm_werewolf.strategy.role_prompt_registry import (
    agent_base_template_path,
    get_role_card,
    resolve_latest_prompt_version,
)


class RolePrompts:
    """各角色的系统提示词（由 per-role 外置文件注入）。"""

    BASE_PROMPT: str = ""
    VILLAGER: dict[str, str] = {}
    PROPHET: dict[str, str] = {}
    WITCH: dict[str, str] = {}
    WOLF: dict[str, str] = {}
    WOLF_KING: dict[str, str] = {}
    GUARD: dict[str, str] = {}
    HUNTER: dict[str, str] = {}


def _hydrate_role_prompts_from_registry() -> None:
    RolePrompts.BASE_PROMPT = agent_base_template_path().read_text(encoding="utf-8").strip()
    RolePrompts.VILLAGER = get_role_card("villager", resolve_latest_prompt_version("villager"))
    RolePrompts.PROPHET = get_role_card("prophet", resolve_latest_prompt_version("prophet"))
    RolePrompts.WITCH = get_role_card("witch", resolve_latest_prompt_version("witch"))
    RolePrompts.WOLF = get_role_card("wolf", resolve_latest_prompt_version("wolf"))
    RolePrompts.WOLF_KING = get_role_card("wolf_king", resolve_latest_prompt_version("wolf_king"))
    RolePrompts.GUARD = get_role_card("guard", resolve_latest_prompt_version("guard"))
    RolePrompts.HUNTER = get_role_card("hunter", resolve_latest_prompt_version("hunter"))


_hydrate_role_prompts_from_registry()


class GamePrompts:
    """游戏流程提示词（由 strategy/prompts/phase/<version>/ 外置加载）。"""


def _hydrate_game_prompts() -> None:
    hydrate_prompt_namespace(GamePrompts, load_phase_prompts(resolve_latest_phase_version()))


_hydrate_game_prompts()


ROLE_SEAT_ACTION: dict[str, str] = load_seat_action_map(resolve_latest_phase_version())


class PlanStrategies:
    """玩家策略计划（由 strategy/prompts/plans/<version>/ 外置加载）。"""

    DEFAULT: dict[str, str] = {}
    COMPLICATED: dict[str, str] = {}
    SIMPLE: dict[str, str] = {}
    CAUTIOUS: dict[str, str] = {}
    BOLD: dict[str, str] = {}
    CRAZY: dict[str, str] = {}
    STYLE_ORDER: tuple[str, ...] = ()
    ROLE_LABELS: dict[str, str] = {}
    STYLE_TEMPLATES: dict[str, str] = {}

    _PLAN_BY_NAME: dict[str, dict[str, str]] = {}

    @classmethod
    def get_all_plans(cls) -> list[dict[str, str]]:
        return [
            cls.DEFAULT,
            cls.COMPLICATED,
            cls.SIMPLE,
            cls.CAUTIOUS,
            cls.BOLD,
            cls.CRAZY,
        ]

    @classmethod
    def default_role_style_plan_names(cls, role_key: str) -> list[str]:
        if role_key not in cls.ROLE_LABELS:
            return []
        return [f"{role_key}_{style}" for style in cls.STYLE_ORDER]

    @classmethod
    def _resolve_role_style_plan(cls, name: str) -> dict[str, str] | None:
        for style in cls.STYLE_ORDER:
            suffix = f"_{style}"
            if not name.endswith(suffix):
                continue
            role_key = name[: -len(suffix)]
            role_label = cls.ROLE_LABELS.get(role_key)
            template = cls.STYLE_TEMPLATES.get(style)
            if role_label is None or template is None:
                return None
            return {"name": name, role_key: template.format(role=role_label)}
        return None

    @classmethod
    def get_plan_by_name(cls, name: str) -> dict[str, str]:
        plan = cls._PLAN_BY_NAME.get(name)
        if plan is not None:
            return plan
        role_style_plan = cls._resolve_role_style_plan(name)
        if role_style_plan is not None:
            return role_style_plan
        return cls.DEFAULT


def _hydrate_plan_strategies() -> None:
    bundle = load_plan_bundle(resolve_latest_plan_version())
    PlanStrategies._PLAN_BY_NAME = dict(bundle.plans)
    PlanStrategies.DEFAULT = bundle.plans.get("default", {"name": "default"})
    PlanStrategies.COMPLICATED = bundle.plans.get("complicated", PlanStrategies.DEFAULT)
    PlanStrategies.SIMPLE = bundle.plans.get("simple", PlanStrategies.DEFAULT)
    PlanStrategies.CAUTIOUS = bundle.plans.get("cautious", PlanStrategies.DEFAULT)
    PlanStrategies.BOLD = bundle.plans.get("bold", PlanStrategies.DEFAULT)
    PlanStrategies.CRAZY = bundle.plans.get("crazy", PlanStrategies.DEFAULT)
    PlanStrategies.ROLE_LABELS = dict(bundle.role_labels)
    PlanStrategies.STYLE_TEMPLATES = dict(bundle.style_templates)
    PlanStrategies.STYLE_ORDER = bundle.style_order


_hydrate_plan_strategies()
