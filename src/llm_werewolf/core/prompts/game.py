"""游戏流程旁白提示（中文，供扩展；引擎主路径使用 locale）。"""


class GamePrompts:
    NIGHT_BEGIN = "天黑请闭眼"
    DAY_BEGIN = "天亮了"
    GOOD_WIN = "好人阵营胜利"
    BAD_WIN = "狼人阵营胜利"


class PlanStrategies:
    """玩家策略计划（注入系统提示中的 plan 字段）。"""

    @classmethod
    def get_plan_by_name(cls, name: str) -> dict:
        plans = {
            "default": {"name": "default", "plan": "自由发挥"},
            "complicated": {"name": "complicated", "plan": "深度分析局势后再行动"},
            "simple": {"name": "simple", "plan": "简化思考，快速决策"},
            "cautious": {"name": "cautious", "plan": "谨慎发言，保守用药"},
            "bold": {"name": "bold", "plan": "大胆发言，主动带队"},
            "crazy": {"name": "crazy", "plan": "混淆视听，适度伪装"},
        }
        return plans.get(name, plans["default"])
