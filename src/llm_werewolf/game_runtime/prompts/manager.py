"""单轨提示构建器：系统提示 + 各角色身份（中文）。"""

import re

from llm_werewolf.game_runtime.types.enums import Camp
from llm_werewolf.game_runtime.roles.catalog import VICTORY_GOAL_DESCRIPTIONS
from llm_werewolf.game_runtime.prompts.system import SYSTEM_PROMPT
from llm_werewolf.game_runtime.prompts.identity import format_identity_prompt
from llm_werewolf.game_runtime.roles.definition import RoleDefinition

_CAMP_LABELS = {Camp.WEREWOLF: "狼人阵营", Camp.VILLAGER: "好人阵营", Camp.NEUTRAL: "中立"}


class PromptManager:
    """为狼人杀 agent 构建 AgentScope 兼容的聊天消息。"""

    GAME_ROLE_TO_PROMPT_KEY: dict[str, str] = {
        "Villager": "villager",
        "Seer": "prophet",
        "Witch": "witch",
        "Hunter": "hunter",
        "Guard": "guard",
        "Werewolf": "wolf",
        "Alpha Wolf": "wolf_king",
        "White Wolf": "white_wolf",
        "Wolf Beauty": "wolf_beauty",
        "Guardian Wolf": "guardian_wolf",
        "Hidden Wolf": "hidden_wolf",
        "Nightmare Wolf": "nightmare_wolf",
        "Blood Moon Apostle": "blood_moon_apostle",
        "Idiot": "idiot",
        "Elder": "elder",
        "Knight": "knight",
        "Cupid": "cupid",
        "Raven": "raven",
        "Magician": "magician",
        "Graveyard Keeper": "graveyard_keeper",
        "Thief": "thief",
        "Lover": "lover",
    }

    @staticmethod
    def build_system_prompt(player_name: str, seat_number: int, plan: str = "自由发挥") -> str:
        """所有角色共用的系统提示。"""
        return SYSTEM_PROMPT.format(player_name=player_name, seat_number=seat_number, plan=plan)

    @staticmethod
    def get_prompt_role_key(game_role_name: str) -> str:
        """将运行时角色名映射为角色策略 prompt 键。"""
        return PromptManager.GAME_ROLE_TO_PROMPT_KEY.get(game_role_name, "villager")

    @staticmethod
    def get_role_strategy_config(
        prompt_role_key: str, prompt_version: str = "v2"
    ) -> dict[str, str]:
        """返回角色策略 prompt 配置。"""
        from llm_werewolf.strategy.prompt_registry import get_registry

        return get_registry(prompt_version).role_card_by_prompt_key(
            prompt_role_key, version=prompt_version
        )

    @staticmethod
    def get_role_strategy_configs(prompt_version: str = "v2") -> dict[str, dict[str, str]]:
        """返回所有角色策略 prompt 配置。"""
        keys = tuple(PromptManager.GAME_ROLE_TO_PROMPT_KEY.values())
        return {
            key: PromptManager.get_role_strategy_config(key, prompt_version=prompt_version)
            for key in keys
        }

    @staticmethod
    def resolve_plan_text(plan_name: str, prompt_role_key: str) -> str:
        """将策略计划名称解析为当前角色的 plan 文本。"""
        from llm_werewolf.strategy.role_prompts import PlanStrategies

        plan = PlanStrategies.get_plan_by_name(plan_name)
        return plan.get(prompt_role_key, plan.get("villager", "自由发挥"))

    @staticmethod
    def build_prompt_key_strategy_prompt(
        seat_number: int, prompt_role_key: str, plan_text: str, prompt_version: str = "v2"
    ) -> str:
        """根据角色策略键构建 AgentScope 系统 prompt。"""
        from llm_werewolf.strategy.prompt_registry import get_registry

        registry = get_registry(prompt_version)
        role_config = registry.role_card_by_prompt_key(prompt_role_key, version=prompt_version)
        return registry.resolve(
            f"{prompt_version}.agent.base",
            number=seat_number,
            role_name=role_config["role_name"],
            role_instruction=role_config["role_instruction"],
            suggestion=role_config["suggestion"],
            plan=plan_text,
        )

    @staticmethod
    def build_role_strategy_prompt(
        seat_number: int, game_role_name: str, plan_text: str, prompt_version: str = "v2"
    ) -> str:
        """根据运行时角色名构建 AgentScope 系统 prompt。"""
        prompt_role_key = PromptManager.get_prompt_role_key(game_role_name)
        return PromptManager.build_prompt_key_strategy_prompt(
            seat_number, prompt_role_key, plan_text, prompt_version=prompt_version
        )

    @staticmethod
    def build_identity_prompt(definition: RoleDefinition) -> str:
        """单个角色的身份提示。"""
        camp_label = _CAMP_LABELS.get(definition.camp, definition.camp.value)
        return format_identity_prompt(
            display_name=definition.display_name,
            role_name=definition.name,
            camp_label=camp_label,
            victory_goal=definition.victory_goal,
        )

    @staticmethod
    def build_initial_chat_history(
        definition: RoleDefinition, player_name: str, seat_number: int, plan: str = "自由发挥"
    ) -> list[dict[str, str]]:
        """初始消息：system（全局）+ system（该角色专属身份）。"""
        return [
            {
                "role": "system",
                "content": PromptManager.build_system_prompt(player_name, seat_number, plan),
            },
            {"role": "system", "content": PromptManager.build_identity_prompt(definition)},
        ]

    @staticmethod
    def get_role_description(definition: RoleDefinition) -> str:
        """供 RoleConfig / 私有备注使用的中文描述。"""
        identity = PromptManager.build_identity_prompt(definition)
        victory = VICTORY_GOAL_DESCRIPTIONS.get(definition.victory_goal, "")
        return f"{identity}\n{victory}"

    @staticmethod
    def build_target_selection_prompt(
        role_display_name: str,
        action_description: str,
        possible_targets: list,
        *,
        allow_skip: bool = False,
        additional_context: str = "",
        round_number: int | None = None,
        phase: str | None = None,
    ) -> str:
        """选择单一目标的中文提示（[[n]]）。"""
        parts: list[str] = [f"【行动】{role_display_name}：{action_description}"]
        if round_number is not None and phase:
            parts.append(f"当前：第 {round_number} 轮 · {phase}")
        elif round_number is not None:
            parts.append(f"当前：第 {round_number} 轮")
        if additional_context:
            parts.extend(["", additional_context])
        parts.extend(["", "可选目标："])
        for idx, target in enumerate(possible_targets, 1):
            parts.append(f"{idx}. {target.name}")
        if allow_skip:
            parts.append(f"{len(possible_targets) + 1}. 跳过本技能")
        parts.extend(["", "请仅回复目标编号，放在 [[]] 中，例如 [[2]]。不要输出其他内容。"])
        return "\n".join(parts)

    @staticmethod
    def build_yes_no_prompt(
        role_display_name: str,
        question: str,
        context: str = "",
        round_number: int | None = None,
        phase: str | None = None,
    ) -> str:
        """中文是/否提示（[[1]] 是，[[0]] 否）。"""
        parts = [f"【询问】{role_display_name}：{question}"]
        if round_number is not None and phase:
            parts.append(f"当前：第 {round_number} 轮 · {phase}")
        if context:
            parts.extend(["", context])
        parts.extend(["", "请仅回复 [[1]] 表示是/使用，[[0]] 表示否/跳过。"])
        return "\n".join(parts)

    @staticmethod
    def build_multi_target_prompt(
        role_display_name: str,
        action_description: str,
        possible_targets: list,
        num_targets: int,
        additional_context: str = "",
        round_number: int | None = None,
        phase: str | None = None,
    ) -> str:
        """选择多个目标的中文提示。"""
        parts = [
            f"【行动】{role_display_name}：{action_description}",
            f"需要选择 {num_targets} 个不同目标。",
        ]
        if round_number is not None and phase:
            parts.append(f"当前：第 {round_number} 轮 · {phase}")
        if additional_context:
            parts.extend(["", additional_context])
        parts.extend(["", "可选目标："])
        for idx, target in enumerate(possible_targets, 1):
            parts.append(f"{idx}. {target.name}")
        parts.extend([
            "",
            f"请回复 {num_targets} 个编号，逗号分隔，每个放在 [[]] 中或合并为 [[1,3]] 形式。",
            "示例：[[1]] [[3]] 或 1,3",
        ])
        return "\n".join(parts)

    @staticmethod
    def parse_bracket_number(response: str) -> int | None:
        """从 [[n]] 或纯数字中解析第一个整数。"""
        match = re.search(r"\[\[\s*(\d+)\s*\]\]", response)
        if match:
            return int(match.group(1))
        numbers = re.findall(r"\d+", response.strip())
        if numbers:
            return int(numbers[0])
        return None

    @staticmethod
    def parse_yes_no(response: str) -> bool:
        """解析 [[1]]/[[0]] 或 是/否（严格格式，与 Bridge 一致）。"""
        from llm_werewolf.game_runtime.prompts.yes_no_parse import parse_yes_no_strict

        return parse_yes_no_strict(response)
