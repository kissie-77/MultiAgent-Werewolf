"""狼人杀角色策略提示词。

Prompt：每身份小包 strategy/prompts/roles/<role>/<version>/ + shared agent_base.md。
发言/遗言等圆桌任务：JSON Schema（SpeechDecision / generate_response）。
选座、投票、女巫用药：[[ ]] 文本格式。
另保留 ROLE_SEAT_ACTION 供 bridge / 扩展角色使用。
"""

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
    """游戏流程提示词"""

    NIGHT_BEGIN = "天黑请闭眼"

    GUARD_ACTION = "守卫请睁眼，今晚你要守谁？回答编号，放在[[]]里"
    GUARD_CLOSE = "守卫请闭眼"

    WOLF_OPEN = "狼人请睁眼，今晚你要刀谁？请回答玩家编号，并放在[[]]里"
    WOLF_TEAMMATES = "你的另外三个队友的代号：{teammates}"
    WOLF_RECHOOSE = "你的队友选了{targets}号玩家，请重新选一次，可以重复，你的决定将是最终目标,请回答玩家编号，并放在[[]]里"
    WOLF_RESULT = "狼人最终选择刀{target}号玩家"
    WOLF_CLOSE = "狼人请闭眼"

    WITCH_OPEN = "女巫请睁眼"
    WITCH_NO_POTION = "你没有药了"
    WITCH_ANTIDOTE = (
        "今晚{target}死了，你有一瓶解药，你要使用吗？请在回答中说[[0]]或[[1]]（1代表yes，0代表no）"
    )
    WITCH_POISON = "你有一瓶毒药，今晚你要使用吗？请在回答中说[[0]]或[[1]]（1代表yes，0代表no）"
    WITCH_POISON_TARGET = "你要毒谁？请回答玩家编号，并放在[[]]里"
    WITCH_CLOSE = "女巫请闭眼"

    PROPHET_ACTION = "预言家请睁眼，选择你要验的玩家编号，回答编号，放在[[]]里"
    PROPHET_RESULT_GOOD = "他是个好人，预言家请闭眼"
    PROPHET_RESULT_BAD = "他是个坏人，预言家请闭眼"

    DAY_BEGIN = "天亮了"
    PEACEFUL_NIGHT = "今晚是个平安夜"
    DEATH_ANNOUNCE_ONE = "今晚{player}号玩家死了"
    DEATH_ANNOUNCE_TWO = "今晚{player1}号玩家和{player2}号玩家死了"

    LAST_WORDS = "你死了，请发表遗言"
    LAST_WORDS_ANNOUNCE = "{player}号玩家的遗言是：{words}"
    FIRST_NIGHT_NO_WORDS = "第一晚没有遗言"

    SPEECH_BEGIN = "发言阶段，请玩家轮流发言，每天顺序交替，第一次1-12，第二次12-1，以此类推"
    SPEECH_PROMPT = (
        "请完成本轮公开发言任务：仅通过 generate_response 提交 SpeechDecision，"
        "勿用 [[...]] 或 {...} 自由格式代替 Schema 字段。"
    )
    SPEECH_ANNOUNCE = "{player}号玩家的发言：{speech}"
    PLAYER_DEAD_SKIP = "{player}号玩家已死亡，跳过发言。"

    VOTE_BEGIN = "请各位玩家轮流投票，必须回复[[座位号]]，一定要把要投的座位号放在[[]]里，弃票的话必须回复[[0]]，每天投票顺序交替，第一次1-12，第二次12-1，以此类推"
    VOTE_ANNOUNCE = "{player}号玩家投给了{target}号"
    VOTE_ABSTAIN = "{player}号玩家弃票"
    VOTE_DEAD_SKIP = "{player}号玩家已死亡，跳过投票"
    VOTE_TIE = "平票，无人出局"
    VOTE_RESULT = "公投结果：{player}号玩家出局"
    VOTE_ALL_ABSTAIN = "全体玩家弃票"

    WOLF_KING_DEATH = "你被投票处决死了，你作为狼王可以发动技能杀死一名玩家，请回答存活的玩家编号，并放在[[]]中，[[]]中不要放发言，不发动技能请回答[[0]]"
    WOLF_KING_KILL = "有人发动了技能，把{target}号玩家杀死了"

    HUNTER_DEATH = "你被击杀了，你作为猎人可以发动技能带走一名玩家，请回答存活的玩家编号，并放在[[]]中，[[]]中不要放发言，不发动技能请回答[[0]]"
    HUNTER_KILL = "有人发动了技能，把{target}号玩家杀死了"
    HUNTER_POISON_DEATH = "你被女巫毒死了，无法发动猎人技能"

    GOOD_WIN = "好人阵营胜利"
    BAD_WIN = "狼人阵营胜利"


# 目录键 / 运行时 role_name → 选座/行动提示（bridge / night_plans 使用运行时名）
_CATALOG_ROLE_SEAT_ACTION: dict[str, str] = {
    "Seer": GamePrompts.PROPHET_ACTION,
    "Witch": GamePrompts.WITCH_POISON_TARGET,
    "Guard": GamePrompts.GUARD_ACTION,
    "Werewolf": GamePrompts.WOLF_OPEN,
    "AlphaWolf": GamePrompts.WOLF_OPEN,
    "WhiteWolf": GamePrompts.WOLF_OPEN,
    "WolfBeauty": GamePrompts.WOLF_OPEN,
    "GuardianWolf": GamePrompts.WOLF_OPEN,
    "HiddenWolf": GamePrompts.WOLF_OPEN,
    "NightmareWolf": GamePrompts.WOLF_OPEN,
    "BloodMoonApostle": GamePrompts.WOLF_OPEN,
    "Hunter": GamePrompts.HUNTER_DEATH,
    "GraveyardKeeper": "守墓人请睁眼，选择一名已死亡玩家查验身份，回答编号，放在[[]]里",
    "Raven": "乌鸦请睁眼，选择一名玩家施加诅咒，回答编号，放在[[]]里",
    "Cupid": "丘比特请睁眼，选择两名玩家结为情侣，回答编号，放在[[]]里",
}


def build_role_seat_action_map() -> dict[str, str]:
    """将运行时 Role.config.name 与目录键映射到选座/行动 prompt。"""
    from llm_werewolf.game_runtime.roles.registry import CATALOG_TO_RUNTIME_NAME

    merged = dict(_CATALOG_ROLE_SEAT_ACTION)
    for catalog, runtime in CATALOG_TO_RUNTIME_NAME.items():
        if catalog in _CATALOG_ROLE_SEAT_ACTION:
            merged[runtime] = _CATALOG_ROLE_SEAT_ACTION[catalog]
    return merged


ROLE_SEAT_ACTION: dict[str, str] = build_role_seat_action_map()


class PlanStrategies:
    """玩家策略计划"""

    DEFAULT = {
        "name": "default",
        "villager": "自由发挥",
        "prophet": "自由发挥",
        "witch": "自由发挥",
        "wolf": "自由发挥",
        "wolf_king": "自由发挥",
        "guard": "自由发挥",
        "hunter": "自由发挥",
    }

    COMPLICATED = {
        "name": "complicated",
        "villager": "仔细研究玩家的发言，尝试找出狼的蛛丝马迹，必须深度思考，输出思考内容",
        "prophet": "仔细研究玩家的发言，尝试找出狼的蛛丝马迹，晚上运用技能找到潜在狼人，白天保持谨慎，必须深度思考，输出思考内容",
        "witch": "仔细研究玩家的发言，尝试找出狼的蛛丝马迹，发挥技能解药救人，觉得是狼人之后使用毒药毒死玩家，必须深度思考，输出思考内容",
        "wolf": "使用诡计，第一晚自刀骗药，与队友配合欺骗平民，杀死和票出关键玩家，混淆视听，必须深度思考，输出思考内容",
        "wolf_king": "使用诡计，第一晚最好配合刀队友一号骗药，与队友配合欺骗平民，杀死和票出关键玩家，被投票处决时杀死关键玩家，必须深度思考，输出思考内容",
        "guard": "仔细研究玩家的发言，尝试找出狼的蛛丝马迹，守护关键玩家，白天保持谨慎，必须深度思考，输出思考内容",
        "hunter": "仔细研究玩家的发言，尝试找出狼的蛛丝马迹，保护好自己，当被击杀时选择一个认为是狼人的玩家带走，必须深度思考，输出思考内容",
    }

    SIMPLE = {
        "name": "simple",
        "villager": "自由发挥，尽量简化发言和思考",
        "prophet": "自由发挥，尽量简化发言和思考",
        "witch": "自由发挥，尽量简化发言和思考",
        "wolf": "自由发挥，尽量简化发言和思考",
        "wolf_king": "自由发挥，尽量简化发言和思考",
        "guard": "自由发挥，尽量简化发言和思考",
        "hunter": "自由发挥，尽量简化发言和思考",
    }

    CAUTIOUS = {
        "name": "cautious",
        "villager": "谨慎发言",
        "prophet": "谨慎发言",
        "witch": "谨慎发言",
        "wolf": "谨慎发言",
        "wolf_king": "谨慎发言",
        "guard": "谨慎发言",
        "hunter": "谨慎发言",
    }

    BOLD = {
        "name": "bold",
        "villager": "大胆发言",
        "prophet": "大胆发言",
        "witch": "大胆发言",
        "wolf": "大胆发言",
        "wolf_king": "大胆发言",
        "guard": "大胆发言",
        "hunter": "大胆发言",
    }

    CRAZY = {
        "name": "crazy",
        "villager": "混淆视听，伪装成女巫，防止狼人把女巫刀掉",
        "prophet": "混淆视听，伪装成平民，防止被狼人刀掉",
        "witch": "混淆视听，伪装成预言家，防止被狼人刀掉",
        "wolf": "混淆视听，伪装成女巫，防止被好人阵营识破并票出局",
        "wolf_king": "混淆视听，伪装成守卫，防止被好人阵营识破并票出局",
        "guard": "混淆视听，伪装成平民，防止被狼人刀掉",
        "hunter": "混淆视听，伪装成村民，防止被狼人刀掉",
    }

    STYLE_ORDER = ("conservative", "aggressive", "skeptical", "coordinator")

    ROLE_LABELS = {
        "villager": "村民",
        "prophet": "预言家",
        "witch": "女巫",
        "wolf": "狼人",
        "wolf_king": "狼王",
        "guard": "守卫",
        "hunter": "猎人",
        "white_wolf": "白狼",
        "wolf_beauty": "狼美人",
        "guardian_wolf": "守墓狼",
        "hidden_wolf": "隐狼",
        "nightmare_wolf": "噩梦狼",
        "blood_moon_apostle": "血月使徒",
        "idiot": "白痴",
        "elder": "长老",
        "knight": "骑士",
        "magician": "魔术师",
        "cupid": "丘比特",
        "raven": "乌鸦",
        "graveyard_keeper": "守墓人",
        "thief": "盗贼",
        "lover": "恋人",
    }

    STYLE_TEMPLATES = {
        "conservative": (
            "你本局采用{role}保守派打法：优先保证信息边界和身份收益，"
            "先观察发言、票型和死亡信息，再给出判断；不要过早站死边或暴露关键意图。"
        ),
        "aggressive": (
            "你本局采用{role}激进派打法：主动制造讨论焦点，敢于提出明确怀疑和投票方向；"
            "发言要推动局势前进，但所有进攻都必须基于你可见的信息。"
        ),
        "skeptical": (
            "你本局采用{role}质疑派打法：重点拆解他人的逻辑、票型和前后矛盾；"
            "多追问理由，少直接跟风，用质疑帮助阵营发现隐藏风险。"
        ),
        "coordinator": (
            "你本局采用{role}协调派打法：整理多名玩家的发言和投票关系，"
            "尝试收束分散讨论，提出可执行的下一步验证或归票方案。"
        ),
    }

    @classmethod
    def get_all_plans(cls) -> list:
        return [cls.DEFAULT, cls.COMPLICATED, cls.SIMPLE, cls.CAUTIOUS, cls.BOLD, cls.CRAZY]

    @classmethod
    def default_role_style_plan_names(cls, role_key: str) -> list[str]:
        if role_key not in cls.ROLE_LABELS:
            return []
        return [f"{role_key}_{style}" for style in cls.STYLE_ORDER]

    @classmethod
    def _resolve_role_style_plan(cls, name: str) -> dict | None:
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
    def get_plan_by_name(cls, name: str) -> dict:
        for plan in cls.get_all_plans():
            if plan["name"] == name:
                return plan
        role_style_plan = cls._resolve_role_style_plan(name)
        if role_style_plan is not None:
            return role_style_plan
        return cls.DEFAULT
