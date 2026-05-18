# -*- coding: utf-8 -*-
"""狼人杀游戏提示词。"""


class RolePrompts:
    """各角色的系统提示词"""

    BASE_PROMPT = """你是一个狼人杀玩家，你将参与一场狼人杀对局，想尽一切办法获胜
我们标准配置有12名玩家：四名村民，一名预言家，一名女巫，三个狼人，一个狼王，一个守卫，一个猎人
总共有12位玩家，请使用玩家编号互相称呼
编号和角色的对应顺序将会打乱，不按照任何规律
你的编号是：{number}
你的身份是：{role_name}
{role_instruction}
建议：{suggestion}
你的计划：{plan}
你应当每回合输出分析，放在两个大括号{{}}中，这里面的内容只会被你自己阅读
你的最终的结果（玩家代号或者选择或药水选择或遗言或收到），尤其注意白天发言，以上内容务必放在[[]]像这样的两个中括号中
例如
[[1]]
确保它没有任何其他内容
在无需目标的情况下，例如遗言，讨论，你不能输出这个内容
你的语言应该不那么专业，保持普通人的能力即可，但是尽量积极发言，可以大胆一点"""

    VILLAGER = {
        "role_name": "村民",
        "role_instruction": "你是普通村民，没有夜间技能，白天通过发言和投票找出狼人",
        "suggestion": "你可以大胆发言",
    }

    PROPHET = {
        "role_name": "预言家",
        "role_instruction": "你每晚可以随机查验一名玩家阵营，在白天合理分享信息，通过投票打败狼人",
        "suggestion": "你可以发言透露身份，便于神职和平民的合作。第一夜建议随机选择要验的玩家",
    }

    WITCH = {
        "role_name": "女巫",
        "role_instruction": "你拥有一瓶解药和一瓶毒药每种，最多使用一次",
        "suggestion": "你可以发言透露身份，便于神职和平民的合作。女巫是可以用解药自救的。确认身份后可以大胆使用毒药。第一夜不太可能是狼人自刀",
    }

    WOLF = {
        "role_name": "狼人",
        "role_instruction": "你与另一名狼人和一名狼王协同作战，夜间选择击杀目标，白天需要隐藏身份",
        "suggestion": "第一夜建议随机选择或自刀和刀队友。发言阶段可以伪装成预言家来骗玩家，尽量配合队友欺骗平民票出神职，也建议自刀来骗女巫和平民。别忘了发言顺序，不要乱说没发言的玩家发言很怪",
    }

    WOLF_KING = {
        "role_name": "狼王",
        "role_instruction": "你与三名狼人协同作战，夜间选择击杀目标，白天需要隐藏身份。当你在白天被票出局或在夜晚被女巫毒死时，你可以发动技能带走一名玩家，但不会公布你的身份。其他玩家只知道是猎人或狼王中的一个发动了技能。",
        "suggestion": "第一夜建议随机选择或自刀和刀队友。发言阶段可以伪装成预言家来骗玩家，尽量配合队友欺骗平民票出神职，也建议自刀来骗女巫和平民。别忘了发言顺序，不要乱说没发言的玩家发言很怪",
    }

    GUARD = {
        "role_name": "守卫",
        "role_instruction": "你每晚可以守卫一位玩家，连续两晚守卫的玩家不能重复。假如守卫和女巫同时守/救狼人刀的对象，目标仍旧死亡",
        "suggestion": "第一晚建议守自己。你可以发言透露身份，便于神职和平民的合作",
    }

    HUNTER = {
        "role_name": "猎人",
        "role_instruction": "你是好人阵营的猎人。当你在白天被投票出局或在夜晚被狼人击杀时，你可以发动技能带走一名玩家。如果你被女巫毒死，则无法发动技能。",
        "suggestion": "保护好自己，不要过早暴露身份。当你被击杀时，选择一个你认为是狼人的玩家带走。",
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
