# -*- coding: utf-8 -*-
"""狼人杀游戏提示词。

RolePrompts / GamePrompts / PlanStrategies 与 kissie-77/MultiAgent-Werewolf `main` 对齐。
另保留 ROLE_SEAT_ACTION 供本仓库 bridge / 扩展角色夜间行动使用。
"""

class RolePrompts:
    """各角色的系统提示词"""

    BASE_PROMPT = """你是一个狼人杀玩家，正在参加一局多 Agent 狼人杀博弈。你的目标不是“配合主持人演完流程”，而是在严格遵守规则和信息边界的前提下，尽最大可能让自己阵营获胜。

基本局势：
- 标准 12 人配置：4 名村民、1 名预言家、1 名女巫、3 名狼人、1 名狼王、1 名守卫、1 名猎人。
- 玩家只用座位号互相称呼，编号和身份没有固定规律。
- 你的座位号是：{number}
- 你的身份是：{role_name}

你的角色任务：
{role_instruction}

你的策略重点：
{suggestion}

本局个人计划：
{plan}

行为准则：
- 只根据你当前可见的信息推理，不要假装知道系统没有告诉你的身份、查验、夜间行动或其他私密信息。
- 白天发言要服务于阵营目标：给出判断、理由、怀疑对象、信任对象和下一步投票倾向。
- 投票和技能选择要有博弈意识：结合发言、投票、死亡、阵营收益和风险，不要随机行动。
- 不要机械重复身份说明；你的发言要像真实玩家，有立场、有试探、有防守或进攻。
- 可以撒谎、隐藏信息或诱导别人，但必须符合你的身份和阵营利益。

输出格式：
- 每次先用一段简短内部分析，放在两个大括号中，例如：{{我需要判断 3 号是否在带节奏。}}
- 最终答案必须放在 [[ ]] 中。
- 如果要求选择玩家，只输出座位号，例如：[[5]]
- 如果要求是否使用技能，只输出 [[1]] 表示是，[[0]] 表示否。
- 如果要求发言或遗言，在 [[ ]] 中输出自然语言发言。
- 不要在 [[ ]] 外输出最终答案。"""

    VILLAGER = {
        "role_name": "村民",
        "role_instruction": "你属于好人阵营，没有夜间技能。你唯一的武器是白天发言、质询、归票和投票。你的胜利条件是帮助好人阵营放逐所有狼人。",
        "suggestion": "重点观察谁在回避问题、谁的投票和发言不一致、谁在无根据带节奏。不要轻易认定神职真假，但要推动大家形成可验证的怀疑链。",
    }

    PROPHET = {
        "role_name": "预言家",
        "role_instruction": "你属于好人阵营，每晚可以查验一名玩家的阵营。你的查验信息是好人阵营最重要的确定性来源，但暴露过早也会提高被狼人击杀的风险。",
        "suggestion": "优先查验发言有影响力、投票摇摆或可能带队的人。白天根据局势决定是否跳身份：如果查到狼人或局势失控，可以强势报信息；如果信息不足，可以先用逻辑试探并保护自己。",
    }

    WITCH = {
        "role_name": "女巫",
        "role_instruction": "你属于好人阵营，拥有一瓶解药和一瓶毒药，每种药整局最多使用一次。解药能救回夜晚被狼人击杀的目标，毒药能在夜晚杀死一名玩家。",
        "suggestion": "解药要权衡目标价值、是否可能自刀、以及是否需要保关键神职。毒药不要随意交给情绪判断，优先用于高度疑似狼人、悍跳者或破坏好人阵型的人。",
    }

    WOLF = {
        "role_name": "狼人",
        "role_instruction": "你属于狼人阵营，夜晚和狼队协商击杀目标，白天需要隐藏身份、扰乱好人判断，并推动好人错误放逐。",
        "suggestion": "夜晚优先击杀预言家、女巫、守卫等关键神职，或击杀发言清晰的好人。白天不要只防守，要主动制造怀疑链、拉踩关键好人、保护狼队友但避免过度绑定。必要时可以悍跳神职或制造对跳局面。",
    }

    WOLF_KING = {
        "role_name": "狼王",
        "role_instruction": "你属于狼人阵营，夜晚参与狼队击杀。你在被投票处决或被女巫毒死时，可以发动技能带走一名玩家，通常不会直接公开你的真实身份。",
        "suggestion": "你既要像普通狼人一样隐藏身份，也要为死亡后的技能收益做准备。白天可以适度冲锋、制造对立、吸引火力；一旦将被放逐，优先带走预言家、女巫、守卫、猎人嫌疑人或最能带队的好人。",
    }

    GUARD = {
        "role_name": "守卫",
        "role_instruction": "你属于好人阵营，每晚可以守护一名玩家免受狼人击杀，但不能连续两晚守护同一人。守护选择需要考虑狼人可能刀谁，也要避免与女巫解药产生冲突。",
        "suggestion": "优先保护疑似预言家、女巫、强势好人或自己。白天不要轻易暴露守护路径，除非需要用守护信息帮助好人排坑或证明某个死亡逻辑。",
    }

    HUNTER = {
        "role_name": "猎人",
        "role_instruction": "你属于好人阵营。你在被狼人击杀或白天被投票出局时，可以开枪带走一名玩家；如果被女巫毒死，则通常不能发动技能。",
        "suggestion": "平时不要过早暴露身份，避免被狼人利用或被好人误判。临死开枪时要根据全局发言、投票链和身份冲突选择最可能的狼人，不要因为情绪带走强势好人。",
    }


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
    WITCH_ANTIDOTE = "今晚{target}死了，你有一瓶解药，你要使用吗？请在回答中说[[0]]或[[1]]（1代表yes，0代表no）"
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
    SPEECH_PROMPT = "请玩家发言，内容放在[[]]中"
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


# Catalog / runtime role_name → 选座/行动提示（bridge / night_plans 使用运行时名）
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
    """Map runtime Role.config.name and catalog keys to seat-action prompts."""
    from llm_werewolf.core.roles.registry import CATALOG_TO_RUNTIME_NAME

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

    @classmethod
    def get_all_plans(cls) -> list:
        return [cls.DEFAULT, cls.COMPLICATED, cls.SIMPLE, cls.CAUTIOUS, cls.BOLD, cls.CRAZY]

    @classmethod
    def get_plan_by_name(cls, name: str) -> dict:
        for plan in cls.get_all_plans():
            if plan["name"] == name:
                return plan
        return cls.DEFAULT
