"""程序记忆：对既有角色策略和计划模板的薄封装。"""

from llm_werewolf.game_runtime.prompts.manager import PromptManager
from llm_werewolf.strategy.registry.role_prompts import PlanStrategies


class ProceduralMemory:
    """封装固定规则、角色提示和计划模板。"""

    def get_role_rules(self, prompt_role_key: str) -> dict[str, str]:
        """获取角色对应的固定策略规则。"""
        return PromptManager.get_role_strategy_config(prompt_role_key)

    def get_plan_text(self, plan_name: str, prompt_role_key: str) -> str:
        """获取指定计划在当前角色下的文本。"""
        return PromptManager.resolve_plan_text(plan_name, prompt_role_key)

    def get_available_plans(self) -> list[dict]:
        """获取所有内置计划。"""
        return PlanStrategies.get_all_plans()

    def build_plan_summary(self, plan_name: str, prompt_role_key: str) -> str:
        """生成可注入提示词的程序记忆摘要。"""
        plan_text = self.get_plan_text(plan_name, prompt_role_key)
        role_rules = self.get_role_rules(prompt_role_key)
        return (
            f"角色固定职责：{role_rules['role_instruction']}\n"
            f"当前采用计划：{plan_name} -> {plan_text}"
        )
