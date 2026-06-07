export interface PresentationStat {
  value: string;
  label: string;
}

export interface PresentationCard {
  title: string;
  description: string;
  icon?: string;
  badges?: string[];
}

export interface PresentationSection {
  id: string;
  num: string;
  title: string;
  tag: string;
  intro?: string;
  cards?: PresentationCard[];
  highlights?: string[];
  bullets?: string[];
  subsections?: {
    title: string;
    cards?: PresentationCard[];
    highlights?: string[];
    bullets?: string[];
    collapsible?: {
      label: string;
      cards?: PresentationCard[];
      bullets?: string[];
      code?: string;
    };
  }[];
}

export const PRESENTATION_HERO = {
  badge: "AGENT TEAMS PRACTICE",
  title: "多智能体协作与博弈",
  titleLine2: "系统工程化实践",
  subtitle: "AgentScope 底座 · 自研 GameEngine · 22 种角色 · 信念矩阵 · 3D 圆桌 · 评测闭环",
  description:
    "Agent 技术正在快速发展，多智能体协作是当前重要方向。狼人杀天然适合检验 Agent Team 能力：多角色、信息不对称、既要协作又要博弈。本系统完整体验从角色设计、协作机制到工程落地的全过程。",
};

export const PRESENTATION_STATS: PresentationStat[] = [
  { value: "22", label: "可扮演角色" },
  { value: "7", label: "Mixin 模块" },
  { value: "15+", label: "PostGame 流水线" },
  { value: "2", label: "进阶方向全选" },
];

export const PRESENTATION_NAV = [
  { id: "agents", label: "角色 Agent" },
  { id: "engine", label: "对局引擎" },
  { id: "isolation", label: "信息隔离" },
  { id: "observability", label: "可观测性" },
  { id: "frontend", label: "前端 UI" },
  { id: "advanced", label: "进阶课题" },
  { id: "scoring", label: "评分对照" },
];

export const ROLE_CHIPS = [
  "村民", "狼人", "预言家", "女巫", "猎人", "守卫",
  "狼王", "白狼", "丘比特", "骑士", "狼美人", "盗贼",
  "长老", "守墓人", "乌鸦", "白痴", "梦魇狼", "血月使徒", "魔术师", "+4",
];

export const PRESENTATION_SECTIONS: PresentationSection[] = [
  {
    id: "agents",
    num: "01",
    title: "角色 Agent · 技能卡驱动的差异化决策",
    tag: "基础",
    intro: "22 种角色，每种拥有独立的提升词库（role.yaml）与技能库（Markdown 技能卡），版本由 RoleVersionManifest 统一管理，支持切换与回滚。",
    subsections: [
      {
        title: "技能卡体系",
        highlights: [
          "每张技能卡为 Markdown + YAML frontmatter（skill_id、status、belief_signals）",
          "InformationHub 按信念矩阵实时匹配注入，而非全量灌入 System Prompt",
          "稀疏 bump：仅全新场景才 vN→vN+1；否则原地更新。status：draft → active → skipped",
        ],
      },
      {
        title: "信念矩阵 · Theory of Mind",
        cards: [
          { title: "B1 一阶信念", description: "我对各座位身份的概率分布（wolf_probability + confidence）" },
          { title: "B2 二阶信念", description: "我认为他人如何看待我——「我暴露了吗」" },
          { title: "W-G 神职定位", description: "仅狼人可见：我认为 j 像什么神职" },
          { title: "W-E 暴露雷达", description: "仅狼人自维护：我认为 i 对我的怀疑程度" },
        ],
      },
      {
        title: "四层记忆体系",
        collapsible: {
          label: "查看记忆架构详情",
          bullets: [
            "工作记忆：按回合/标签的动态窗口，LLM 压缩防 token 溢出",
            "情景记忆：EventLogger 完整事件流，赛后导出 episode_report",
            "语义记忆：跨局经验沉淀，Coach 提取候选并 merge 入库",
            "程序记忆：角色行动计划模板，开局注入 persistent context",
          ],
        },
      },
      {
        title: "结构化决策输出",
        cards: [
          { title: "SpeechDecision", description: "public_speech + private_thought（内心 OS）" },
          { title: "SeatChoiceDecision", description: "选座 + reason，用于查验/投票/守护" },
          { title: "MindStateDecision", description: "信念矩阵 + 投票意向联合输出" },
          { title: "VoteIntentionDecision", description: "投票意向追踪，定位摇摆与说服" },
        ],
      },
    ],
  },
  {
    id: "engine",
    num: "02",
    title: "对局引擎 · Mixin 组合 + 异步并发",
    tag: "基础",
    subsections: [
      {
        title: "Mixin 组合式架构",
        cards: [
          { title: "DeathHandlerMixin", description: "死亡结算：狼刀、毒、殉情、长老惩罚" },
          { title: "ActionProcessorMixin", description: "技能优先级、同步/互斥、保护/反弹" },
          { title: "NightPhaseMixin", description: "狼队讨论、夜间技能执行" },
          { title: "SheriffElectionMixin", description: "警长竞选、投票、警徽移交" },
          { title: "DayPhaseMixin", description: "圆桌发言、白狼自爆" },
          { title: "VotingPhaseMixin", description: "并发投票、平票 PK" },
          { title: "GameEngineBase", description: "主循环、状态持久化" },
        ],
      },
      {
        title: "NightSkillScheduler",
        bullets: [
          "Pre-Wolf：丘比特、梦魇狼、守卫等先于狼刀",
          "Wolf Vote：狼队私密讨论后投票刀口",
          "Witch：女巫获知刀口后用药",
          "Post-Witch：预言家查验、守墓人、乌鸦、魔术师",
        ],
      },
      {
        title: "死亡结算边界",
        cards: [
          { title: "毒奶冲突", description: "守卫+女巫同夜守同一人 → 死亡" },
          { title: "长老两条命", description: "首刀不死，被投票出局则神职失效" },
          { title: "情侣殉情", description: "一方死亡另一方连带，不递归触发" },
          { title: "警徽移交", description: "警长死亡可撕毁或指定继承" },
        ],
      },
    ],
    highlights: ["asyncio 全链路非阻塞", "投票 gather 并发", "per-step 超时配置", "GameState JSON 持久化"],
  },
  {
    id: "isolation",
    num: "03",
    title: "信息隔离 · 双路径保险",
    tag: "基础",
    intro: "信息隔离是项目最核心的工程挑战，采用双路径策略：",
    cards: [
      {
        title: "路径一：LLM 决策记忆隔离",
        description: "MsgHub 按 PUBLIC / WOLF_TEAM / PRIVATE 路由；决策 prompt 不含越权事件日志。",
      },
      {
        title: "路径二：事件日志可见性过滤",
        description: "Event.visible_to 为权威依据；VOTE_INTENTION_SNAPSHOT / BELIEF_SNAPSHOT 标为 REPLAY_ONLY。",
      },
    ],
    highlights: [
      "专项对抗测试：构造越权样本，断言零泄露",
      "狼队频道隔离 + 夜聊分工（提案/综合/风险/收束）避免重复发言",
    ],
  },
  {
    id: "observability",
    num: "04",
    title: "可观测性 · 事件流 + 告警 + 复盘",
    tag: "基础",
    subsections: [
      {
        title: "结构化事件流",
        bullets: [
          "EventLogger 全量记录发言、技能、投票、死亡、信念/意向快照",
          "发言含 private_thought；SUB_PHASE 轻量阶段提示",
        ],
      },
      {
        title: "告警体系",
        collapsible: {
          label: "8 项 Phase 1 告警规则",
          cards: [
            { title: "run_failed", description: "对局运行失败" },
            { title: "post_game_failed", description: "PostGame 流水线失败" },
            { title: "info_leak_detected", description: "信息泄露" },
            { title: "vote_timeout", description: "投票超时" },
            { title: "provider_429", description: "LLM 限流" },
            { title: "phase_order_violation", description: "阶段顺序违规" },
          ],
        },
      },
      {
        title: "复盘体系",
        cards: [
          { title: "Replayer", description: "事件序列重放，断点回溯" },
          { title: "ReplayAgent", description: "LLM 驱动结构化复盘" },
          { title: "Bad Case 扫描", description: "空发言、泄露、技能违规等 6 类检测" },
          { title: "Vote Swing", description: "追踪投票意向摇摆，定位说服事件" },
        ],
      },
    ],
  },
  {
    id: "frontend",
    num: "05",
    title: "前端 UI · 3D 圆桌 + 人机混战",
    tag: "基础",
    highlights: ["React 19", "Vite", "TypeScript", "Zustand", "Three.js", "Tailwind CSS 4", "SSE 实时观战"],
    cards: [
      { title: "ThreeCanvas", description: "圆形审判桌 + 法阵纹理 + 夜间光照与粒子特效" },
      { title: "CameraTracker", description: "平滑聚焦当前发言座位，空闲时慢速轨道镜头" },
      { title: "SpeechConsole", description: "羊皮纸发言气泡 + 内心 OS（上帝视角）" },
      { title: "ReplayPage", description: "时间线回放、信念矩阵、MVP 评分" },
    ],
    subsections: [
      {
        title: "人机混战",
        bullets: [
          "人类座位接入：发言 / 投票 / 夜间技能底部面板",
          "CLI：--human_seat 多人类玩家，极简输入 + 非法重试",
          "revealView：god（全信息）vs suspense（悬念模式）",
        ],
      },
    ],
  },
  {
    id: "advanced",
    num: "06",
    title: "进阶 · 评测 + 自进化",
    tag: "双方向全选",
    subsections: [
      {
        title: "评测体系（B 方向）",
        cards: [
          { title: "VoteSwing", description: "发言前后意向快照对比，归因关键说服" },
          { title: "信念信号匹配", description: "技能卡 belief_signals 驱动运行时注入" },
          { title: "Leaderboard", description: "win_rate、MVP、安全性指标多维排行" },
          { title: "A/B 对比", description: "双样本 z 检验 + Wilson 置信区间" },
        ],
      },
      {
        title: "自进化体系（C 方向）",
        cards: [
          { title: "PromptEvolver", description: "6 种补丁类型，evidence_ledger 证据链" },
          { title: "版本管理", description: "RoleVersionManifest + evolution_summary 回溯" },
          { title: "闭环验证", description: "终局 vs 初始 Agent 自动对战评估提升" },
        ],
        highlights: ["对局 → 分析 → 调整 → 再对局 自动闭环"],
      },
    ],
  },
];

export const SCORE_ROWS = [
  {
    dimension: "单 Agent 能力",
    weight: "20%",
    standard: "Prompt 精细、角色行为差异显著、决策可追溯、能分析 bad case",
    implementation: "22 角色独立词库/技能库 + 信念矩阵 + 结构化输出 + PromptEvolver",
    tier: "满分档",
  },
  {
    dimension: "多 Agent 协作",
    weight: "20%",
    standard: "公共/私有信息分离清晰，技能调度抽象良好，有明确博弈行为",
    implementation: "MsgHub 三层隔离 + 投票意向 + 狼队心智 + 夜聊分工",
    tier: "满分档",
  },
  {
    dimension: "工程实现",
    weight: "30%",
    standard: "全流程正确、边界完善、隔离经测试、前端好用、文档齐全",
    implementation: "Mixin 引擎 + PostGame 15 步 + 告警 + 隔离测试 + Docker",
    tier: "满分档",
  },
  {
    dimension: "进阶课题",
    weight: "30%",
    standard: "评测能定位失误；自进化胜率显著提升且可回溯",
    implementation: "VoteSwing + Leaderboard/A/B + PromptEvolver 版本链",
    tier: "双方向全选",
  },
];

export const MVP_CHECKLIST = [
  "至少 5 种角色 → 22 种，独立词库与技能库",
  "完整对局流程 → 夜晚/白天/投票/警长全流程",
  "信息隔离有效 → 双路径 + 对抗测试零泄露",
  "对局日志完整 → 事件流 + 信念/意向快照",
  "前端界面 → 3D 观战 + 人机 + 复盘",
  "进阶课题 → B 评测 + C 自进化双选",
];
