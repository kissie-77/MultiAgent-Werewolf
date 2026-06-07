"""Static and semi-static content for intro / guide pages."""

from __future__ import annotations

from llm_werewolf.game_runtime.roles.catalog import get_catalog
from llm_werewolf.interface.api.models.common import NavLink
from llm_werewolf.interface.api.models.pages import (
    StrategyTip,
    ContentSection,
    NightPhaseStep,
    ContentPageData,
    StrategyPageData,
    NightPhasePageData,
)
from llm_werewolf.game_runtime.prompts.identity import get_identity_template

CAMP_LABELS = {
    "werewolf": "狼人阵营",
    "villager": "好人阵营",
    "neutral": "第三方",
}


def default_nav_links() -> list[NavLink]:
    return [
        NavLink(key="home", title="首页", path="/", description="进入 AI 狼人杀"),
        NavLink(key="game", title="开始对局", path="/game", description="主游戏页"),
        NavLink(key="about", title="AI 狼人杀", path="/about"),
        NavLink(key="features", title="功能介绍", path="/features"),
        NavLink(key="how-to-play", title="玩法说明", path="/how-to-play"),
        NavLink(key="night-phase", title="夜晚阶段", path="/night-phase"),
        NavLink(key="roles", title="角色列表", path="/roles"),
        NavLink(key="models", title="AI 模型", path="/models"),
        NavLink(key="strategy", title="攻略", path="/strategy"),
        NavLink(key="replay", title="复盘", path="/replay"),
    ]


def get_home_content() -> tuple[str, str]:
    return (
        "AI 狼人杀",
        "多智能体狼人杀博弈平台 — 观看 AI 对局、复盘分析、对比模型表现。",
    )


def get_about_page() -> ContentPageData:
    return ContentPageData(
        page_key="about",
        title="AI 狼人杀介绍",
        summary="基于 AgentScope + 自研 GameEngine 的多智能体狼人杀系统。",
        sections=[
            ContentSection(
                heading="项目定位",
                body="每个 Agent 根据所扮演角色拥有独立目标与信息视野，在信息隔离约束下进行推理、发言与投票。",
                bullets=[
                    "AgentScope 负责 LLM 调用与 ReAct 推理",
                    "GameEngine 负责规则、阶段流转与信息隔离",
                    "PostGame 管线生成复盘、评分与 Skill 沉淀",
                ],
            ),
            ContentSection(
                heading="适用场景",
                body="适合 AI 能力评测、多 Agent 协作/对抗研究，以及狼人杀规则教学演示。",
            ),
        ],
        related_links=default_nav_links(),
    )


def get_features_page() -> ContentPageData:
    return ContentPageData(
        page_key="features",
        title="功能介绍",
        summary="平台核心能力一览。",
        sections=[
            ContentSection(
                heading="对局运行",
                body="支持 6–20 人标准/扩展板子，CLI/TUI/API 多种入口。",
                bullets=["全自动 AI 对局", "人类座位接入", "警长/警徽流程", "结构化决策输出"],
            ),
            ContentSection(
                heading="评测与复盘",
                body="赛后自动生成多视角日志、投票摇摆分析、阵营说服评分与 MVP。",
                bullets=["events.jsonl 事件流", "log_views 多 POV 视图", "Leaderboard 批量对比", "Coach Skill 沉淀"],
            ),
            ContentSection(
                heading="角色与模型",
                body="22 种角色目录 + 多配置文件切换不同 LLM 后端。",
            ),
        ],
        related_links=default_nav_links(),
    )


def get_how_to_play_page() -> ContentPageData:
    return ContentPageData(
        page_key="how-to-play",
        title="玩法说明",
        summary="标准狼人杀流程、胜利条件与平台观战指引。",
        sections=[
            ContentSection(
                heading="游戏目标",
                body="每位玩家扮演一名角色，在信息不完全的情况下通过发言、投票与夜间技能争取己方阵营胜利。",
                bullets=[
                    "好人阵营：找出并淘汰所有狼人",
                    "狼人阵营：隐藏身份，使狼人数量达到胜利阈值",
                    "第三方角色：拥有独立胜利条件（恋人、盗贼等）",
                ],
            ),
            ContentSection(
                heading="回合循环",
                body="对局在「夜晚 → 白天讨论 → 白天投票」中循环推进，直至一方达成胜利条件。",
                bullets=[
                    "夜晚：狼队刀人，神职按序私密行动",
                    "白天：公布死亡信息，全员发言后投票放逐",
                    "警长：首夜后可竞选，拥有 1.5 票与归票权",
                    "平票：进入 PK 发言后再投，仍平票则无人出局",
                ],
            ),
            ContentSection(
                heading="信息隔离",
                body="每位 Agent 只能看到与其角色/阵营匹配的信息；查验、用药、刀口等私密结果不会广播给其他玩家。",
                bullets=[
                    "狼队拥有私密讨论频道",
                    "预言家查验结果仅自己可见，白天可选择公开",
                    "女巫仅知晓当晚刀口目标，解药/毒药各限一次",
                ],
            ),
            ContentSection(
                heading="人类座位",
                body="开启人类模式后，轮到你的回合时底部面板会提示发言、投票或夜间技能操作。",
                bullets=[
                    "发言：输入观点后提交，进入下一位玩家",
                    "投票：选择放逐目标或弃票",
                    "技能：按角色提示选择目标（查验、用药、守护等）",
                ],
            ),
            ContentSection(
                heading="观战与复盘",
                body="完成的对局保存在 artifacts/runs/，可通过复盘页查看事件时间线、信念矩阵与赛后评分。",
                bullets=[
                    "实时观战：SSE 事件流驱动 3D 牌桌与发言台",
                    "赛后报告：MVP 评分、投票摇摆、阵营说服分析",
                    "Skill 沉淀：优质对局经验写入各角色技能库",
                ],
            ),
        ],
        related_links=default_nav_links(),
    )


def get_night_phase_page() -> NightPhasePageData:
    steps = [
        NightPhaseStep(
            order=1,
            role_group="pre_wolf",
            title="预狼阶段",
            description="丘比特（首夜）、梦魇狼、守卫、守卫狼、盗贼等先于狼刀行动。",
        ),
        NightPhaseStep(
            order=2,
            role_group="wolf_discussion",
            title="狼队讨论",
            description="狼人阵营通过私密频道协商刀口目标。",
        ),
        NightPhaseStep(
            order=3,
            role_group="wolf_vote",
            title="狼刀投票",
            description="各狼人提交击杀目标；平票时由狼队代表裁定最终刀口。",
        ),
        NightPhaseStep(
            order=4,
            role_group="witch",
            title="女巫行动",
            description="得知刀口后可选择救人、毒人或跳过（各药仅一次）。",
        ),
        NightPhaseStep(
            order=5,
            role_group="post_witch",
            title="其余夜间角色",
            description="预言家查验、守墓人验尸、乌鸦标记等按顺序行动。",
        ),
        NightPhaseStep(
            order=6,
            role_group="resolution",
            title="死亡结算",
            description="结算狼刀、毒药、守卫、长老等交互后的最终死亡名单。",
        ),
    ]
    base = ContentPageData(
        page_key="night-phase",
        title="狼人杀夜晚阶段",
        summary="一夜间各角色行动顺序与信息可见性说明。",
        sections=[
            ContentSection(
                heading="为何夜晚重要",
                body="多数关键信息（查验、用药、刀口）在夜间产生，且默认仅相关角色可见。",
            ),
        ],
        related_links=default_nav_links(),
    )
    return NightPhasePageData(**base.model_dump(), steps=steps)


def get_strategy_page() -> StrategyPageData:
    general = [
        StrategyTip(
            role_key=None,
            title="记录发言逻辑链",
            content="关注谁在什么信息下改变立场，比单句内容更能暴露阵营。",
            tags=["通用", "白天"],
        ),
        StrategyTip(
            role_key=None,
            title="警惕跟风投票",
            content="平票 PK 与警长 1.5 票会放大煽动效果，注意独立判断。",
            tags=["投票"],
        ),
    ]
    role_tips: list[StrategyTip] = []
    for role in get_catalog():
        fields = get_identity_template(role.name)
        role_tips.append(
            StrategyTip(
                role_key=role.name,
                title=f"{role.display_name}（{CAMP_LABELS.get(role.camp.value, role.camp.value)}）",
                content=fields.get("suggestion", ""),
                tags=[role.camp.value, "角色"],
            )
        )
    return StrategyPageData(
        title="攻略",
        general_tips=general,
        role_tips=role_tips,
        post_game_links=[
            NavLink(key="replay", title="查看复盘", path="/replay"),
            NavLink(key="models", title="模型对比", path="/models"),
        ],
    )
