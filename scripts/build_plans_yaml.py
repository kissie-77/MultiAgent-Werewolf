"""将 per_role_styles 并入 plans 段，生成 plans/v1/plans.yaml。"""

from __future__ import annotations

from pathlib import Path

import yaml

OUT = (
    Path(__file__).resolve().parents[1]
    / "src"
    / "llm_werewolf"
    / "strategy"
    / "prompts"
    / "plans"
    / "v1"
    / "plans.yaml"
)

ROLES = [
    "villager",
    "prophet",
    "witch",
    "wolf",
    "wolf_king",
    "guard",
    "hunter",
    "white_wolf",
    "wolf_beauty",
    "guardian_wolf",
    "hidden_wolf",
    "nightmare_wolf",
    "blood_moon_apostle",
    "idiot",
    "elder",
    "knight",
    "magician",
    "cupid",
    "raven",
    "graveyard_keeper",
    "thief",
    "lover",
]

STYLES = ("conservative", "aggressive", "skeptical", "coordinator")

ROLE_STYLES: dict[str, dict[str, str]] = {
    "villager": {
        "conservative": "作为村民保守派：你没有夜间技能，是最容易被抗推的位。优先观察其他人发言，不轻易站边；看到可疑行为时只问问题不踩人，保护自己存活到信息明朗再站队。",
        "aggressive": "作为村民激进派：你是最干净的平民之一，应该主动承担带队责任。听到任何发言逻辑漏洞或票型矛盾，立刻点出并给归票方向，推动局势往清晰方向走。",
        "skeptical": "作为村民质疑派：你是好人阵营的反诈防线。拆解每条验人逻辑、每张票型、每次站边；不要相信任何「我查了X是狼」的说法，必须要求对方给出警徽流和归票目标。",
        "coordinator": "作为村民协调派：你的价值是整理信息。汇总所有人的发言、票型、查杀、站边关系；提出「今天先验X」「先出X」的执行方案，把分散讨论收束成可执行归票。",
    },
    "prophet": {
        "conservative": "作为预言家保守派：拿到查验结果后不要第一时间跳身份，先在发言中暗示「我手上有信息」；只有当被扛推风险升高时才公开查杀，公开前用其他玩家的发言做铺垫。",
        "aggressive": "作为预言家激进派：拿到查杀的当轮就跳身份报查杀。警徽流清晰，今晚验谁、为什么验，迫使狼队必须应对你而不是抗推你。",
        "skeptical": "作为预言家质疑派：对自己的查验结果保持严谨，警惕悍跳或假金水；发言时多追问狼队的反扑逻辑，要求对方给出更具体的证据链。",
        "coordinator": "作为预言家协调派：你是好人阵营的信息中心。白天同步公开查验结果和警徽流，建议下一轮验人、给归票目标，把队内讨论收束到「信我的人跟我走」。",
    },
    "witch": {
        "conservative": "作为女巫保守派：解药只在能救自己或能救真预言家/守卫时使用；毒药只在狼信≥0.7且有两条以上硬证据时使用；白天发言保持中立，不主动跳身份。",
        "aggressive": "作为女巫激进派：解药、毒药都用来主动改变局势；分析首夜刀口是否值得救，毒药在手时敢收高威胁位；白天适度跳身份为好人阵营增加确定性。",
        "skeptical": "作为女巫质疑派：用药前严格分析被刀/疑似狼的目标是否值得用药；对白天「我是女巫」的玩家严格盘问用药逻辑，避免被悍跳者骗药。",
        "coordinator": "作为女巫协调派：用药后白天适度同步信息但不暴露完整逻辑；建议预言家/守卫路线互补；归票前给出用药依据，帮助好人阵营收束判断。",
    },
    "wolf": {
        "conservative": "作为狼人保守派：白天发言模拟好人视角，踩一个发言有漏洞的好人但不过度攻击；不要暴露任何夜间信息；投票时与狼队票型协调，避免被怀疑。",
        "aggressive": "作为狼人激进派：白天主动制造讨论焦点，可悍跳神职；带节奏归票好人阵营核心位；与狼队配合做高风险高收益操作。",
        "skeptical": "作为狼人质疑派：用质疑好人阵营的方式混淆视听。拆解真预言家的验人逻辑、警徽流；用追问验人心路历程等问题诱导好人内讧。",
        "coordinator": "作为狼人协调派：白天模拟好人阵营协调者，整理发言、票型并提出归票方向，但把票型引导到狼队目标；夜间与狼队同步白天协调结果。",
    },
    "wolf_king": {
        "conservative": "作为狼王保守派：白天发言与普通狼人一致，隐藏狼王身份；被投票出局时开枪带走好人阵营核心位神职；不要在第一轮就暴露狼王身份。",
        "aggressive": "作为狼王激进派：白天可悍跳神职制造混乱；被投票出局时带走高威胁位神职，用技能扭转局势。",
        "skeptical": "作为狼王质疑派：白天用质疑拆解真预言家的验人逻辑和警徽流；被投票出局时带走白天最会带节奏的好人。",
        "coordinator": "作为狼王协调派：白天模拟好人协调者带票型但引导到狼队目标；夜间与狼队协商时主动制定刀人计划。",
    },
    "guard": {
        "conservative": "作为守卫保守派：首夜无公开信息，优先守护高价值神职位或按板子规律博刀口；后续根据死亡信息反推刀位；不连续两晚守护同一人。",
        "aggressive": "作为守卫激进派：利用平安夜信息反推狼队刀位，守护有价值的核心位打乱狼队节奏；白天适度跳身份提供守护信息。",
        "skeptical": "作为守卫质疑派：对悍跳神职严格盘问；守护选择必须基于多条证据而不是单一发言。",
        "coordinator": "作为守卫协调派：守护路线与女巫用药互补；白天适度同步守护逻辑；建议好人阵营下一轮的守护目标。",
    },
    "hunter": {
        "conservative": "作为猎人保守派：前期不要过早暴露身份；开枪目标须基于三条硬证据——像不像狼、能否清狼、会不会带崩好人。",
        "aggressive": "作为猎人激进派：前期适度暴露身份让狼队忌惮；出局时带走高威胁位神职或带队好人。",
        "skeptical": "作为猎人质疑派：对悍跳神职严格盘问；开枪前确认目标像不像狼，避免被诱导带错人。",
        "coordinator": "作为猎人协调派：维护「开枪候选顺位」，公开几个嫌疑；归票前给出清晰怀疑链。",
    },
    "white_wolf": {
        "conservative": "作为白狼王保守派：白天与普通狼人一致隐藏身份；隔夜独醒时优先刀暴露高的狼队友为终局独狼铺路；必要时自爆带走真预言家。",
        "aggressive": "作为白狼王激进派：白天可悍跳神职；隔夜刀狼清理队友加速控场；被识别时果断自爆带神职。",
        "skeptical": "作为白狼王质疑派：白天拆解真预言家验人逻辑；隔夜刀狼时选择白天最被怀疑的队友。",
        "coordinator": "作为白狼王协调派：白天模拟好人协调者引导票型；夜间与狼队协商刀狼与自爆时机。",
    },
    "wolf_beauty": {
        "conservative": "作为狼美人保守派：魅惑目标优先疑似神职或带队好人，为殉情换轮次做准备；白天低调隐藏身份；不魅惑狼队友。",
        "aggressive": "作为狼美人激进派：魅惑预言家/女巫等高威胁位；你出局时被魅惑者殉情，最大化技能收益。",
        "skeptical": "作为狼美人质疑派：白天拆解真预言家逻辑；魅惑白天最像神职、带队最强的玩家。",
        "coordinator": "作为狼美人协调派：白天配合狼队票型；夜间与队友协商魅惑对象以最大化殉情收益。",
    },
    "guardian_wolf": {
        "conservative": "作为守卫狼保守派：夜间仅守护狼队暴露度高的队友（防白狼刀狼等）；白天与普通狼人一致；不守护好人。",
        "aggressive": "作为守卫狼激进派：守护白天最可能被扛推的狼队友；白天适度干扰好人判断。",
        "skeptical": "作为守卫狼质疑派：白天拆解真预言家逻辑；守护目标选最可能暴露的狼队友。",
        "coordinator": "作为守卫狼协调派：夜间告知队友守护逻辑以调整刀口；白天配合狼队票型。",
    },
    "hidden_wolf": {
        "conservative": "作为隐狼保守派：白天用「我怀疑」「我觉得」等主观措辞；适度踩有漏洞的好人；不暴露夜间信息；利用验好人背书低调生存。",
        "aggressive": "作为隐狼激进派：白天制造讨论焦点但不暴露隐狼身份；带节奏归票好人核心位。",
        "skeptical": "作为隐狼质疑派：拆解真预言家验人逻辑和警徽流，诱导好人内讧。",
        "coordinator": "作为隐狼协调派：模拟好人协调者整理票型，但引导到狼队目标。",
    },
    "nightmare_wolf": {
        "conservative": "作为梦魇狼保守派：封锁目标优先疑似神职或当夜可能开技能的玩家；白天低调；不封锁狼队友。",
        "aggressive": "作为梦魇狼激进派：封锁预言家/女巫干扰其夜间技能；白天适度制造混乱。",
        "skeptical": "作为梦魇狼质疑派：白天拆解真预言家逻辑；封锁白天最像神职的玩家。",
        "coordinator": "作为梦魇狼协调派：与狼队协商封锁对象，优先阻断女巫毒药或预言家查验。",
    },
    "blood_moon_apostle": {
        "conservative": "作为血月使徒保守派：狼全灭前按好人视角潜伏，不暴露站边；关注狼队存活数，全灭后立即变身接管刀口。",
        "aggressive": "作为血月使徒激进派：变身前低调生存，变身后优先刀预言家/女巫等高威胁位。",
        "skeptical": "作为血月使徒质疑派：潜伏期用好人视角质疑焦点位，不暗示夜间私密信息。",
        "coordinator": "作为血月使徒协调派：变身前观察票型，变身后与狼队节奏对齐选刀。",
    },
    "idiot": {
        "conservative": "作为白痴保守派：前期不跳白痴；被投票出局时翻牌亮明身份，说明不会被投死。",
        "aggressive": "作为白痴激进派：被扛推时翻牌，翻牌后大胆发言带队（你已失去投票权，只能呼吁跟票）。",
        "skeptical": "作为白痴质疑派：翻牌前盘问悍跳神职；翻牌后用质疑帮好人识别狼队。",
        "coordinator": "作为白痴协调派：翻牌后整理发言、票型并提出归票建议，公开嫌疑顺位。",
    },
    "elder": {
        "conservative": "作为长老保守派：前期不跳长老；带队归票基于公开逻辑；切记被投票出局会使所有神职失去技能。",
        "aggressive": "作为长老激进派：适度用身份增加确定性；敢于点出高狼信目标，但避免成为狼队抗推位。",
        "skeptical": "作为长老质疑派：对悍跳神职严格盘问；归票前比较三条证据维度。",
        "coordinator": "作为长老协调派：整理发言、票型并提出归票方向；建议下一轮验证目标。",
    },
    "knight": {
        "conservative": "作为骑士保守派：决斗须基于三条硬证据；整局仅一次机会，证据不足则不用。",
        "aggressive": "作为骑士激进派：决斗狼信最高且矛盾最明显的目标；适度暴露身份形成威慑。",
        "skeptical": "作为骑士质疑派：对悍跳神职严格盘问；决斗前确认目标像不像狼。",
        "coordinator": "作为骑士协调派：维护「决斗候选顺位」；归票前给出清晰怀疑链。",
    },
    "magician": {
        "conservative": "作为魔术师保守派：交换两名玩家的身份（非位置），优先「疑似狼+疑似好」组合；不交换已死者；整局仅一次。",
        "aggressive": "作为魔术师激进派：将暴露的神职与低调好人交换身份以保护核心；打乱狼队刀口预期。",
        "skeptical": "作为魔术师质疑派：交换前核对悍跳与票型；选择最可能受益的交换组合。",
        "coordinator": "作为魔术师协调派：交换后适度帮助好人理解局势，不暴露完整交换逻辑。",
    },
    "cupid": {
        "conservative": "作为丘比特保守派：首夜连线一狼一好制造对立；不连线两同阵营；白天不暴露丘比特。",
        "aggressive": "作为丘比特激进派：连线立场差异最大的两人；关注恋人存活以争取第三方胜利。",
        "skeptical": "作为丘比特质疑派：连线前观察发言立场；连线后低调跟踪恋人票型。",
        "coordinator": "作为丘比特协调派：连线后适度关注恋人动向，建议恋人配合第三方策略。",
    },
    "raven": {
        "conservative": "作为乌鸦保守派：夜间诅咒狼信最高的目标（次日投票多一票反对）；白天不暴露乌鸦身份。",
        "aggressive": "作为乌鸦激进派：诅咒白天带队最强的好人；次日引导归票被诅咒者。",
        "skeptical": "作为乌鸦质疑派：诅咒前核对发言与票型；不诅咒低狼信好人。",
        "coordinator": "作为乌鸦协调派：诅咒后次日用怀疑链引导好人关注被诅咒者。",
    },
    "graveyard_keeper": {
        "conservative": "作为守墓人保守派：夜间查验已死亡玩家的真实阵营；优先查验争议死亡位以收缩狼坑。",
        "aggressive": "作为守墓人激进派：用死者身份快速反推狼坑；白天在有益时透露查验结论。",
        "skeptical": "作为守墓人质疑派：结合死者阵营复盘其生前站边与票型。",
        "coordinator": "作为守墓人协调派：将查验结果融入好人信息整理，建议下一轮归票目标。",
    },
    "thief": {
        "conservative": "作为盗贼保守派：首夜优先选神职身份获夜间信息；选后低调观察再决定是否跳身份。",
        "aggressive": "作为盗贼激进派：选神职后尽快利用技能带队；根据局势灵活站边。",
        "skeptical": "作为盗贼质疑派：选身份后严格盘问悍跳与票型；若选狼身份勿立刻倒戈。",
        "coordinator": "作为盗贼协调派：利用所选身份整理信息、票型并提出归票方向。",
    },
    "lover": {
        "conservative": "作为恋人保守派：前期不暴露连线关系；关注恋人存活，第三方胜利需双方活到最后。",
        "aggressive": "作为恋人激进派：在保恋人前提下适度带节奏；平衡双方阵营利益。",
        "skeptical": "作为恋人质疑派：不因子阵营盲目站边；恋人死后可更积极质疑狼坑。",
        "coordinator": "作为恋人协调派：整理信息、票型，争取与恋人共同存活到最后。",
    },
}

COMPLICATED: dict[str, str] = {
    "villager": "仔细研究玩家的发言，尝试找出狼的蛛丝马迹，必须深度思考，输出思考内容",
    "prophet": "仔细研究玩家的发言，尝试找出狼的蛛丝马迹，晚上运用技能找到潜在狼人，白天保持谨慎，必须深度思考，输出思考内容",
    "witch": "仔细研究玩家的发言，分析刀口与毒口收益，解药救关键好人、毒药收高威胁狼，必须深度思考，输出思考内容",
    "wolf": "与队友配合欺骗平民，刀死和票出关键玩家，白天混淆视听，必须深度思考，输出思考内容",
    "wolf_king": "与队友配合欺骗平民，刀死和票出关键玩家，被投票处决时开枪带走神职，必须深度思考，输出思考内容",
    "guard": "仔细研究发言与死亡信息，守护关键好人，不连续两晚守同一人，必须深度思考，输出思考内容",
    "hunter": "仔细研究发言，保护好自己，出局时基于证据开枪带走狼人，必须深度思考，输出思考内容",
    "white_wolf": "白天配合狼队，隔夜刀狼队友控场，必要时自爆带神职，必须深度思考，输出思考内容",
    "wolf_beauty": "魅惑高威胁好人制造殉情收益，白天配合狼队票型，必须深度思考，输出思考内容",
    "guardian_wolf": "守护暴露高的狼队友，白天伪装好人，必须深度思考，输出思考内容",
    "hidden_wolf": "利用验好人背书低调生存，白天拆解好人逻辑，必须深度思考，输出思考内容",
    "nightmare_wolf": "封锁神职夜间技能，配合狼队刀口，必须深度思考，输出思考内容",
    "blood_moon_apostle": "潜伏至狼全灭后变身，变身后优先刀神职，必须深度思考，输出思考内容",
    "idiot": "避免被抗推，翻牌后发言带队（无投票权），必须深度思考，输出思考内容",
    "elder": "谨慎带队，避免被投出（会废神职技能），必须深度思考，输出思考内容",
    "knight": "证据充分时决斗，整局仅一次机会，必须深度思考，输出思考内容",
    "magician": "择机交换两人身份打乱狼刀，必须深度思考，输出思考内容",
    "cupid": "首夜连线制造阵营对立，关注恋人存活，必须深度思考，输出思考内容",
    "raven": "夜间诅咒高狼信目标，次日引导归票，必须深度思考，输出思考内容",
    "graveyard_keeper": "查验死者身份收缩狼坑，必须深度思考，输出思考内容",
    "thief": "首夜谨慎选身份，选后利用技能优势，必须深度思考，输出思考内容",
    "lover": "隐藏恋人关系，争取与恋人共同存活，必须深度思考，输出思考内容",
}

CRAZY: dict[str, str] = {
    "villager": "混淆视听，适度伪装神职视角，避免成为狼队首刀目标",
    "prophet": "混淆视听，伪装成平民，防止被狼人刀掉",
    "witch": "混淆视听，伪装成预言家，防止被狼人刀掉",
    "wolf": "混淆视听，伪装成女巫，防止被好人阵营识破并票出局",
    "wolf_king": "混淆视听，伪装成守卫，防止被好人阵营识破并票出局",
    "guard": "混淆视听，伪装成平民，防止被狼人刀掉",
    "hunter": "混淆视听，伪装成村民，防止被狼人刀掉",
    "white_wolf": "混淆视听，伪装成平民，隐藏白狼王身份与刀狼节奏",
    "wolf_beauty": "混淆视听，伪装成平民，隐藏魅惑目标",
    "guardian_wolf": "混淆视听，伪装成守卫，隐藏守护狼队友行为",
    "hidden_wolf": "混淆视听，利用验好人背书，伪装深度好人",
    "nightmare_wolf": "混淆视听，伪装成平民，隐藏封锁对象",
    "blood_moon_apostle": "混淆视听，伪装成平民，潜伏至变身时机",
    "idiot": "混淆视听，伪装成村民，避免过早被抗推",
    "elder": "混淆视听，伪装成平民，隐藏长老两条命价值",
    "knight": "混淆视听，伪装成村民，隐藏决斗技能",
    "magician": "混淆视听，伪装成平民，隐藏交换身份能力",
    "cupid": "混淆视听，伪装成村民，隐藏连线关系",
    "raven": "混淆视听，伪装成平民，隐藏诅咒对象",
    "graveyard_keeper": "混淆视听，伪装成平民，隐藏守墓人查验",
    "thief": "混淆视听，选身份后伪装成对应平民视角",
    "lover": "混淆视听，隐藏恋人关系，避免被针对性刀杀",
}


def _plan_entry(name: str, role_text: dict[str, str]) -> dict[str, str]:
    """每个 plan 均包含全部 prompt_role_key（与 simple 段格式一致）。"""
    entry: dict[str, str] = {"name": name}
    for role in ROLES:
        entry[role] = role_text[role]
    return entry


def build() -> dict:
    plans: dict[str, dict[str, str]] = {
        "default": _plan_entry("default", {role: "自由发挥" for role in ROLES}),
        "simple": _plan_entry(
            "simple",
            {role: "自由发挥，尽量简化发言和思考" for role in ROLES},
        ),
        "cautious": _plan_entry("cautious", {role: "谨慎发言" for role in ROLES}),
        "bold": _plan_entry("bold", {role: "大胆发言" for role in ROLES}),
        "complicated": _plan_entry("complicated", COMPLICATED),
        "crazy": _plan_entry("crazy", CRAZY),
    }
    for role in ROLES:
        for style in STYLES:
            plan_name = f"{role}_{style}"
            plans[plan_name] = _plan_entry(
                plan_name,
                {r: ROLE_STYLES[r][style] for r in ROLES},
            )
    return {
        "schema": "plan_strategies_v1",
        "style_order": list(STYLES),
        "role_labels": {
            "villager": "村民",
            "prophet": "预言家",
            "witch": "女巫",
            "wolf": "狼人",
            "wolf_king": "狼王",
            "guard": "守卫",
            "hunter": "猎人",
            "white_wolf": "白狼王",
            "wolf_beauty": "狼美人",
            "guardian_wolf": "守卫狼",
            "hidden_wolf": "隐狼",
            "nightmare_wolf": "梦魇狼",
            "blood_moon_apostle": "血月使徒",
            "idiot": "白痴",
            "elder": "长老",
            "knight": "骑士",
            "magician": "魔术师",
            "cupid": "丘比特",
            "raven": "渡鸦",
            "graveyard_keeper": "守墓人",
            "thief": "盗贼",
            "lover": "恋人",
        },
        "style_templates": {
            "conservative": "你本局采用{role}保守派打法：优先保证信息边界和身份收益，先观察发言、票型和死亡信息，再给出判断；不要过早站死边或暴露关键意图。",
            "aggressive": "你本局采用{role}激进派打法：主动制造讨论焦点，敢于提出明确怀疑和投票方向；发言要推动局势前进，但所有进攻都必须基于你可见的信息。",
            "skeptical": "你本局采用{role}质疑派打法：重点拆解他人的逻辑、票型和前后矛盾；多追问理由，少直接跟风，用质疑帮助阵营发现隐藏风险。",
            "coordinator": "你本局采用{role}协调派打法：整理多名玩家的发言和投票关系，尝试收束分散讨论，提出可执行的下一步验证或归票方案。",
        },
        "plans": plans,
    }


def main() -> None:
    payload = build()
    header = (
        "# PlanStrategies 外置配置\n"
        "# - 每个 plan 均含 name + 全部 22 个 prompt_role_key（格式同 simple）\n"
        "# - 粗粒度：default / complicated / simple / cautious / bold / crazy\n"
        "# - 细粒度：{prompt_role_key}_{style}，如 wolf_skeptical\n\n"
    )
    yaml_body = yaml.dump(
        payload,
        allow_unicode=True,
        sort_keys=False,
        default_flow_style=False,
        width=120,
    )
    OUT.write_text(header + yaml_body, encoding="utf-8")
    print(f"Wrote {OUT} ({len(payload['plans'])} plans)")


if __name__ == "__main__":
    main()
