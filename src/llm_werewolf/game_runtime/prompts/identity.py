"""各角色身份提示词（仅中文，仅注入匹配角色）。"""

from llm_werewolf.game_runtime.types.enums import VictoryGoal

# victory_goal → 简短中文描述（追加到身份块末尾）
_VICTORY_TEXT = {
    VictoryGoal.WEREWOLF_PARITY: "胜利目标：狼人数量不少于好人即可获胜。",
    VictoryGoal.VILLAGER_ELIMINATE_WEREWOLVES: "胜利目标：找出并淘汰所有狼人。",
    VictoryGoal.NEUTRAL_LOVER: "胜利目标：与恋人一起存活到最后。",
    VictoryGoal.NEUTRAL_THIEF: "胜利目标：首夜选择身份后，随所选阵营获胜。",
    VictoryGoal.NEUTRAL_WHITE_LOVER_WOLF: "胜利目标：与恋人消灭其余所有玩家。",
    VictoryGoal.FOLLOW_ASSIGNED_CAMP: "胜利目标：随你当前阵营而定。",
}

IDENTITY_PROMPTS: dict[str, dict[str, str]] = {
    "Werewolf": {
        "instruction": "你是狼人。每晚与狼队友协商并投票击杀一名非狼玩家，白天隐藏身份。",
        "suggestion": "首夜可与队友商量刀口；白天可伪装神职，引导好人互投。",
    },
    "AlphaWolf": {
        "instruction": "你是狼王。参与狼刀；被投票出局或被女巫毒杀时可开枪带走一人（毒杀除外）。",
        "suggestion": "过早暴露风险大，可在关键轮次发动技能。",
    },
    "WhiteWolf": {
        "instruction": "你是白狼。参与狼刀；奇数夜晚可额外击杀一名狼人（可跳过）。白天发言轮可自爆（self_explode），跳过投票直入黑夜并开枪带走一人。",
        "suggestion": "独狼阶段可刀狼加快局势，注意守卫狼的守护。",
    },
    "WolfBeauty": {
        "instruction": "你是狼美人。参与狼刀；整局可魅惑一名玩家，你死亡时被魅惑者殉情。",
        "suggestion": "魅惑好人可扰乱好人阵营。",
    },
    "GuardianWolf": {
        "instruction": "你是守卫狼。参与狼刀；每晚可守护一名狼队友（可挡白狼额外刀）。",
        "suggestion": "优先保护关键狼队友或自己。",
    },
    "HiddenWolf": {
        "instruction": "你是隐狼。参与狼刀；被预言家查验时显示为好人。",
        "suggestion": "可大胆冲神职位，干扰预言家信息。",
    },
    "BloodMoonApostle": {
        "instruction": "你是血月使徒。未转化前不参与狼刀、查验显示好人；其他狼全灭后转化为普通狼人参与刀人。",
        "suggestion": "前期低调，转化后积极刀人。",
    },
    "NightmareWolf": {
        "instruction": "你是梦魇狼。参与狼刀；每晚可封锁一名玩家的夜间技能。",
        "suggestion": "优先封锁预言家、女巫等神职。",
    },
    "Villager": {
        "instruction": "你是平民。无夜间技能，依靠发言与投票找出狼人。",
        "suggestion": "记录发言逻辑，避免跟风投票。",
    },
    "Seer": {
        "instruction": "你是预言家。每晚查验一名存活玩家阵营（狼/好人）。",
        "suggestion": "查验信息谨慎公开，避免首夜被刀。",
    },
    "Witch": {
        "instruction": "你是女巫。拥有一瓶解药和一瓶毒药，各只能用一次；解药可救当晚狼刀目标（可自救）。",
        "suggestion": "首夜谨慎用药；毒药留给高置信狼人。",
    },
    "Hunter": {
        "instruction": "你是猎人。被投票出局或被狼刀（非毒）时可开枪带走一人；被毒杀不能开枪。",
        "suggestion": "隐藏身份，发动技能时选择最可疑目标。",
    },
    "Guard": {
        "instruction": "你是守卫。每晚守护一名玩家免疫狼刀；不能连续两晚守同一人。",
        "suggestion": "首夜可自守；注意与女巫同守同目标仍会死亡。",
    },
    "Idiot": {
        "instruction": "你是白痴。被投票出局时翻牌免死但失去投票权。",
        "suggestion": "可利用翻牌带队，但之后无法投票。",
    },
    "Elder": {
        "instruction": "你是长老。可抵挡一次狼刀；若被投票出局则好人神职永久失效。",
        "suggestion": "避免被投出局，否则团队损失惨重。",
    },
    "Knight": {
        "instruction": "你是骑士。整局白天可与一人决斗一次：对方是狼则其死，否则你死。",
        "suggestion": "在信息较充分时使用决斗。",
    },
    "Magician": {
        "instruction": "你是魔术师。整局可在夜晚交换两名玩家的身份一次（若技能已开放）。",
        "suggestion": "在关键轮次打乱狼人判断。",
    },
    "Cupid": {
        "instruction": "你是丘比特（中立第三方）。首夜连接两名玩家为恋人，恋人共生死、知彼此身份。",
        "suggestion": "连接策略影响全局，可连强弱搭配；你不属于好人或狼人阵营。",
    },
    "Raven": {
        "instruction": "你是乌鸦。每晚可标记一名玩家，次日公投时其额外获得一票。",
        "suggestion": "标记可疑玩家增加出局概率。",
    },
    "GraveyardKeeper": {
        "instruction": "你是守墓人。每晚可查验一名已死亡玩家的身份。",
        "suggestion": "根据死者身份倒推存活狼人。",
    },
    "Thief": {
        "instruction": "你是盗贼。首夜从两张额外身份牌中选择一张，此后按该身份行动与获胜。",
        "suggestion": "根据局面选择强势神职或狼人身份。",
    },
    "Lover": {
        "instruction": "你是恋人（丘比特所连）。与恋人互相知晓身份，一方死亡另一方殉情，可形成独立胜利条件。",
        "suggestion": "与恋人协作，平衡原阵营与恋人胜利。",
    },
}


def get_identity_template(role_name: str) -> dict[str, str]:
    """返回角色的身份字段；无匹配时回退为村民风格文案。"""
    return IDENTITY_PROMPTS.get(
        role_name,
        {
            "instruction": f"你的身份是{role_name}，请根据游戏规则行动。",
            "suggestion": "根据场上局势灵活决策。",
        },
    )


def format_identity_prompt(
    display_name: str, role_name: str, camp_label: str, victory_goal: VictoryGoal
) -> str:
    """构建仅含身份的提示词块。"""
    fields = get_identity_template(role_name)
    victory_text = _VICTORY_TEXT.get(victory_goal, "")
    return (
        "【身份提示】\n"
        f"身份：{display_name}（{role_name}）\n"
        f"阵营：{camp_label}\n"
        f"{victory_text}\n"
        f"技能说明：{fields['instruction']}\n"
        f"策略建议：{fields['suggestion']}"
    )
