# 多Agent协作满分补强：上下文链路审查

> **模块**：architecture / game_runtime / agent_team / evaluation
> **状态**：active
> **最后更新**：2026-06-05
> **关联代码**：`src/llm_werewolf/game_runtime/`、`src/llm_werewolf/agent_team/`、`src/llm_werewolf/evaluation/`
> **关联测试**：`tests/game_runtime/test_information_isolation.py`、`tests/game_runtime/test_night_skill_flow.py`、`tests/agent_team/test_working_memory_compression.py`、`tests/evaluation/test_bad_case_report.py`
> **Agent Skill**：`.agents/skills/generated/game-runtime/`、`.agents/skills/generated/agent-team/`、`.agents/skills/generated/evaluation/`

> 范围：Task 1-7，上下文管理、信息隔离、夜间技能元数据化、信念矩阵与赛后证据链补强。
> 边界：本报告记录本轮工程补强和验证证据；真实 20 局以上 A/B 显著提升、真实 run 的 0 泄漏汇总报告仍作为后续评分证据补跑项。

## 一句话结论

当前 Agent 可见上下文链路已经打通：事件先由 `Event.visible_to` 定义可见范围，再经 `ObservationBuilder` 变成玩家视角文本；对话内容不靠事件日志硬塞给 LLM，而是由 `InformationHub` / `MsgHub` 按 PUBLIC、WOLF_TEAM、PRIVATE 通道路由；最后 `WorkingMemory.get_context()` 把本局固定信息、内心信念、稳定经验和本轮记忆按块注入决策 prompt。  

整体判断：这条链路可以作为“多 Agent 协作与系统设计”评分证据。当前主要疏漏不是发现了明确泄露，而是还有几个边界需要在答辩材料和后续测试里说清楚：`visible_to=None` 与 `visible_to=[]` 的语义、公共事实和私密事实的分界、本局固定信息与长期经验的分界、信念矩阵只进 Agent 内部决策上下文的分界。

## 1. Agent 可见上下文链路

核心链条可以概括为：

```text
Event.visible_to
  -> EventLogger.get_events_for_player / get_events_for_players
  -> GameEngineBase.build_player_observation / build_shared_observation
  -> ObservationBuilder.build / format_for_prompt
  -> InformationHub._merge_private_context 或 run_roundtable / collect_speech
  -> MsgHub 按 PUBLIC / WOLF_TEAM / PRIVATE 投递对话
  -> RuntimeMemoryManager.get_context_for_decision
  -> WorkingMemory.get_context
  -> WerewolfAdapterBridge 请求 Agent 发言、投票、夜间技能等 prompt
```

### 1.1 `Event.visible_to` 是日志可见性的权威入口

相关实现：

- `src/llm_werewolf/game_runtime/types/models.py`
- `src/llm_werewolf/game_runtime/events/event_visibility.py`
- `src/llm_werewolf/game_runtime/events/events.py`
- `src/llm_werewolf/game_runtime/engine/base.py`

语义如下：

| `visible_to` 值 | 含义 |
| --- | --- |
| `None` | 全员可见，例如白天公开发言、投票结果、公开死亡 |
| `["player_1"]` | 只给指定玩家看，例如预言家查验、守卫守护、女巫用药 |
| `["wolf_1", "wolf_2"]` | 阵营或小组可见，例如狼队夜聊、部分狼队技能 |
| `[]` | 写入日志但对玩家 observation 不可见，常用于复盘/评测快照 |

`GameEngineBase._log_event()` 在没有显式传 `visible_to` 时，会调用 `resolve_visible_to()` 自动推导默认可见范围。随后 `EventLogger.get_events_for_player()` 只返回 `event.is_visible_to(player_id)` 为真的事件。

这意味着：事件日志可以保留完整复盘证据，但每个 Agent 看到的是按自己座位过滤后的局内视角。

### 1.2 `ObservationBuilder` 把可见事件变成玩家视角文本

相关实现：

- `src/llm_werewolf/game_runtime/observation.py`
- `src/llm_werewolf/game_runtime/engine/base.py`
- `src/llm_werewolf/game_runtime/state/player.py`

`build_player_observation()` 做了三件事：

1. 使用 `game_state.get_public_info()` 注入公共局面，只包含阶段、轮次、总人数、存活人数。
2. 使用 `event_logger.get_events_for_player(player.player_id)` 获取当前玩家可见事件。
3. 使用 `player.get_private_notes(game_state)` 注入角色私密事实，例如自己身份、队友、技能状态或查验结果。

当 `for_agent_decision=True` 时，`build_player_observation()` 会排除 `HUB_DIALOGUE_EVENT_TYPES`。也就是说，玩家发言、狼队夜聊、警上发言这些“对话内容”不会重复出现在事件块里，避免 LLM 同时从事件日志和 MsgHub 读到两份不一致的发言历史。

`build_shared_observation()` 用于狼队等多人共享上下文，它调用 `get_events_for_players()` 取“这一组人都能看见”的事件，避免把某个个体私密事件塞给整个小组。

### 1.3 `InformationHub` / `MsgHub` 管对话记忆隔离

相关实现：

- `src/llm_werewolf/agent_team/communication/information_hub.py`
- `src/llm_werewolf/agent_team/communication/message_router.py`
- `src/llm_werewolf/game_runtime/events/visibility.py`
- `src/llm_werewolf/game_runtime/phase_interaction.py`

这层处理“谁能听到谁说话”：

| 通道 | 听众 |
| --- | --- |
| `PUBLIC` | 所有存活玩家 |
| `WOLF_TEAM` | 存活狼队成员 |
| `PRIVATE` | 单个行动者 |

`MessageRouter` 根据通道解析受众，`InformationHub` 再把消息放进对应 `MsgHub` 作用域。Agent 只产出 `public_speech` 和可选 `private_thought`；受众不是 Agent 自己决定，而是引擎和 Hub 决定。

关键点：

- `run_roundtable()` 在每个发言人行动前刷新信念匹配 Skill，然后组装该玩家的上下文。
- `run_roundtable()` 会把前面已经说过的公开发言或狼队夜聊作为本轮可见对话传给后续发言者。
- `_run_private_session()` 只把私密上下文广播给当前行动者。
- `_deliver_private()` 只把 `private_thought` 投递给发言者自己。
- 对话事件仍会写入 Event 日志用于 UI/复盘，但决策 prompt 主要从 MsgHub / ReAct 历史读取对话。

### 1.4 `WorkingMemory.get_context()` 管决策前动态上下文

相关实现：

- `src/llm_werewolf/agent_team/memory/working_memory.py`
- `src/llm_werewolf/agent_team/memory/runtime_memory_manager.py`
- `src/llm_werewolf/strategy/belief_format.py`
- `src/llm_werewolf/agent_team/agents/factory.py`

`WorkingMemory.get_context()` 会按块输出：

| 块 | 来源 | 边界 |
| --- | --- | --- |
| `【本局固定信息】` | `role_pool` 等固定规则事实 | 本局内所有 Agent 可使用，不属于长期经验 |
| `【内心信念】` | `belief`、`wolf_camp`、`belief_rules` | 只进入 Agent 内部决策上下文 |
| `【稳定经验】` | 程序记忆、语义经验 | 不应混入本局角色池等固定事实 |
| `【历史回顾】` | 每轮压缩摘要 | 控制长期上下文长度 |
| `【本轮记忆】` | 本轮发言、事件、决策 | 短期可用，按优先级保留 |

`RuntimeMemoryManager.get_context_for_decision()` 先取 `WorkingMemory.get_context()`，再追加信念匹配 Skill。系统 prompt 本身只写角色策略和“Skill 会动态注入”的说明，真正的局内动态上下文是在每次决策前拼接。

信念矩阵链路是：

```text
InformationHub 采集投票意向/信念
  -> merge_llm_beliefs 更新每个 Agent 的 BeliefState
  -> sync_player_belief_memory / sync_all_belief_memories
  -> RuntimeMemoryManager.sync_belief_context
  -> WorkingMemory protected persistent tags
  -> get_context_for_decision
  -> Agent prompt
```

这保证了信念矩阵是“内心状态”，不是公开事实。

## 2. 当前已做到什么

已经做到的部分可以直接作为实现证据：

| 能力 | 当前证据 |
| --- | --- |
| 事件可见性有统一默认规则 | `resolve_visible_to()` 覆盖私有角色行动、狼队事件、刀口给狼队和女巫、复盘专用快照隐藏 |
| Observation 按玩家过滤 | `EventLogger.get_events_for_player()` 只返回当前玩家可见事件 |
| 群体上下文取交集 | `build_shared_observation()` 只取一组玩家共同可见事件 |
| 决策 observation 不重复注入对话 | `for_agent_decision=True` 排除 `HUB_DIALOGUE_EVENT_TYPES` |
| 对话走 MsgHub 隔离 | PUBLIC、WOLF_TEAM、PRIVATE 三类通道由 `MessageRouter` 和 `InformationHub` 控制 |
| 公共发言有泄密提醒 | `EngineContexts.public_speech_information_boundary()` 要求私密信息只能放在 `private_thought`，公开发言不能无意识泄露 |
| 本局固定信息单独分块 | `role_pool` 进入 `【本局固定信息】`，不混进 `【稳定经验】` |
| 信念矩阵受保护 | `belief`、`wolf_camp`、`belief_rules` 是 protected persistent tags，不会被普通经验挤掉 |
| 人类玩家上下文更克制 | 现有测试要求人类讨论上下文不展示信念矩阵、内心信念、信念规则 |
| 运行身份不进入可见文本 | 现有测试要求 observation 文本不出现 `ai_model`、`model`、`backend`、`human`、`demo` |

现有测试已经覆盖的方向包括：

- 预言家查验、女巫用药、守卫保护、丘比特连线、特殊狼技能只给有权限的人看。
- 狼队讨论和狼队夜间旁白只给狼队看。
- 刀口结算不是公开事件，只给狼队和女巫看。
- `VOTE_INTENTION_SNAPSHOT`、`BELIEF_SNAPSHOT` 对玩家 observation 隐藏。
- 决策 observation 排除发言正文，发言正文从 MsgHub 读取。
- `WorkingMemory` 能把信念、本局固定信息、稳定经验和本轮记忆分块输出。

## 3. 还可能的疏漏点

这些不是已确认泄露，而是后续答辩、回归测试或代码审查里应该盯住的边界。

### 3.1 `visible_to=None` 和 `visible_to=[]` 必须持续讲清楚

`None` 是公开，`[]` 是无人可见。这个语义很好用，但也容易被误读。建议在答辩材料里明确说明：复盘专用事件可以写日志，但通过 `[]` 不进入任何玩家 observation。

### 3.2 不要绕过 `ObservationBuilder.format_for_prompt()`

`PlayerInfo` 模型中仍有 `ai_model` 字段，当前 prompt 文本没有打印它，测试也覆盖了“模型/后端/人类/demo 不进 observation 文本”。  

风险在于：如果未来有人直接把 `PlayerObservation.model_dump()` 或 `PlayerInfo.model_dump()` 拼进 Agent prompt，就可能重新暴露运行身份字段。建议把“Agent prompt 只能使用 `format_for_prompt()` 的文本结果”作为工程约束写入后续规范或测试。

### 3.3 公共事实、私密事实和主动公开之间要区分

白天公开发言可以主动跳身份、报验人或公开用药信息，但这属于 Agent 自己选择公开，不等于系统可以提前把这些私密事实注入所有人上下文。当前 `public_speech_information_boundary()` 已经提醒模型这一点。  

后续验证时要看两件事：

- 未公开前，私密技能结果不能出现在其他人的 observation 或 MsgHub 历史里。
- 主动公开后，其他人只能从公开发言记忆里得知，而不是从事件私密字段里得知。

### 3.4 本局固定信息不能和长期经验混在一起

`role_pool` 已经进入 `【本局固定信息】`，这是正确方向。它和 `【稳定经验】` 的区别要继续保持：

- 本局固定信息：本局角色池、人数配置、规则约束。
- 稳定经验：跨局策略、程序记忆、语义 Skill。

如果把“本局角色池”写成“稳定经验”，模型可能把某一局配置误当成所有局都成立。

### 3.5 信念矩阵是内心状态，不是公开事件

当前 `format_belief_context()` 标题写明“仅自己可见”，并由 `WorkingMemory` 作为 `【内心信念】` 注入。狼人私有战术雷达 `wolf_camp`（`wolf_camp_minds[seat]`）同样仅注入该狼本人决策上下文，狼间不共享。  

后续要继续防两类误用：

- 把 `BELIEF_SNAPSHOT` 当作普通可见事件进入 observation。
- 把某个 Agent 的 `BeliefState` 或**其他狼的** W 面板同步给非狼人、其他狼或人类 UI 输入界面。

### 3.6 `collect_speech()` 的调用者要承担上下文拼接责任

`InformationHub.run_roundtable()` 会在每个发言前刷新信念匹配 Skill，并通过 `context_builder` 获取上下文。`collect_speech()` 也刷新 Skill，但它收到的是调用者传入的 `context`。  

这意味着：未来如果新增单次发言入口，必须确保传入的 `context` 已包含应该有的 observation、公开边界提醒和必要 WorkingMemory，否则刷新了 Skill 也可能没有进入 prompt。

### 3.7 已弃用的 `MessageAdapter.visible_to` 不应被当成权威规则

`agent_team/communication/message.py` 里已经说明旧 Msg metadata 上的 `visible_to` 未接入引擎事件日志。真正权威规则是 `Event.visible_to` 加 `InformationHub` / `MsgHub` 路由。后续不要新增第四套手写 history 或 metadata 规则。

## 4. 如何作为评分证据

这份链路审查可对应“多 Agent 协作与系统设计 20 分”中的以下证据项：

| 评分点 | 可展示证据 | 说明 |
| --- | --- | --- |
| 多 Agent 协作机制 | `InformationHub.run_roundtable()`、`MessageRouter`、`MsgHub` 通道 | 多个 Agent 按阶段、座位、阵营进行公开讨论、狼队讨论和私密行动 |
| 信息隔离与局内视角 | `Event.visible_to`、`ObservationBuilder`、`get_events_for_player()` | 每个 Agent 只看到自己该看到的事件和私密笔记 |
| 上下文管理能力 | `WorkingMemory.get_context()`、`RuntimeMemoryManager.get_context_for_decision()` | prompt 不是一次性堆全部日志，而是分块、按轮、按优先级注入 |
| 系统模块化设计 | `game_runtime` 管规则和事件，`agent_team` 管通信和记忆，`strategy` 管信念和 Skill | 职责清晰，后续角色、事件、评测都能扩展 |
| 可观测性与可验证性 | events、visible_to、belief snapshot、vote intention snapshot、现有信息隔离测试 | 既能复盘上帝视角，也能验证玩家 POV 是否泄露 |
| 人机混战边界 | 人类上下文不注入信念矩阵和内部记忆 | 人类 UI 输入输出与 Agent 内部推理分开 |

答辩时可以这样表述：

> 我们不是让所有 Agent 共用一份大上下文，而是给每个 Agent 构建自己的局内视角。事件日志保留完整复盘证据，但进入 Agent prompt 前会经过 `visible_to` 和 observation 过滤；发言历史走 MsgHub 通道，公开、狼队、私聊三种受众分开；工作记忆再把本局固定信息、内心信念和短期事件按块注入。所以系统既支持多 Agent 协作，也能证明信息隔离。

## 5. 本轮落地记录（2026-06-05）

| 顺序 | 工作 | 状态 | 代码/文档证据 |
| --- | --- | --- | --- |
| 1 | 梳理 `WorkingMemory.get_context()` 分区 | 已完成 | 本文第 1.4 节；`tests/agent_team/test_working_memory_compression.py` |
| 2 | 审查 `visible_to`、observation、`InformationHub` | 已完成 | 本文第 1.1-1.3 节 |
| 3 | 补信息隔离测试 | 已完成 | `tests/game_runtime/test_information_isolation.py` 覆盖预言家、女巫、狼队、守卫、刀口、复盘快照、丘比特等可见性边界 |
| 4 | 规范夜间技能元数据 | 已完成 | `game_runtime/registries/role_night_plans.py` 增加 `NightStage`、`NightPlanSpec`、`NIGHT_PLAN_SPECS` 与注册校验 |
| 5 | 补夜间技能调度测试 | 已完成 | `tests/game_runtime/test_night_skill_flow.py` 与 `tests/game_runtime/test_night_scheduler.py` 覆盖守卫、狼人、女巫、预言家、魔术师与注册完整性 |
| 6 | 检查信念矩阵注入和赛后复盘记录 | 已完成 | `docs/evaluation/ROADMAP.md` 新增 Task 6/7 证据链；`evaluation/post_game/bad_case_report.py` 接入 PostGame pipeline |
| 7 | 写入文档证据 | 已完成 | `docs/game_runtime/DESIGN.md`、`docs/evaluation/ROADMAP.md`、`docs/architecture/evaluation/评分标准对照自评.md`、本文 |

### 5.1 夜间技能扩展证据

本轮把夜间角色调度从分散硬编码收敛到 `NIGHT_PLAN_SPECS`。`NightSkillScheduler` 读取规格表决定唤醒批次与顺序，角色自身的行动请求由 planner 负责，主流程不再为每个角色维护专用分支。

复杂角色演示选择 `Magician`：通过 `MagicianSwapAction`、`plan_magician_swap`、`EventType.MAGICIAN_SWAPPED` 和夜间计划注册接入。这个例子可以用于答辩说明：新增复杂夜间角色时，主要改角色定义、动作、事件可见性和计划注册，主调度器几乎不用动。

### 5.2 信息隔离测试证据

新增的信息隔离测试把本轮关注的泄露边界固化为回归：

- 预言家查验结果只给预言家。
- 女巫救人/毒人只给女巫。
- 狼队讨论、狼队唤醒/投票/闭眼提示只给狼队。
- 刀口结算只给狼队和女巫，不给村民、守卫、预言家。
- `VOTE_INTENTION_SNAPSHOT` 和 `BELIEF_SNAPSHOT` 写入复盘但不进入任何玩家 observation。
- 丘比特、魔术师、狼美人、梦魇狼、渡鸦、守墓人等私有技能事件只给行动者本人。

### 5.3 赛后 Bad Case 证据

PostGame pipeline 新增 `PromptBadCaseChecker` 报告入口，当前先检测“公开事实无支撑”类问题，例如玩家凭空跳出未公开身份、未公开技能结果或无来源的场上事实。它不替代人工复盘，但会把明显 prompt 幻觉写成结构化赛后产物，方便后续做 prompt 迭代和 A/B 对比。

### 5.4 本轮验证

已通过的组合测试：

```powershell
uv run pytest --no-cov tests/game_runtime/test_roles.py tests/game_runtime/test_night_scheduler.py tests/game_runtime/test_event_visibility.py tests/game_runtime/test_action_processor.py tests/game_runtime/test_information_isolation.py tests/game_runtime/test_night_skill_flow.py tests/evaluation/test_bad_case_report.py tests/agent_team/test_working_memory_compression.py
```

结果：`108 passed`。

致命 lint 与语法检查也已通过：

```powershell
uv run ruff check --select E9,F821 ...
py_compile
```

## 6. 建议后续补强

短期不需要改当前链路。若要继续冲满分，建议优先补三类证据：

1. 真实对局 POV 对比报告：同一局分别导出 god view、村民 view、狼人 view、女巫 view，证明私密事件没有串视角。
2. `PlayerObservation.model_dump()` 不得进入 Agent prompt 的守护测试，防止未来绕过 `format_for_prompt()`。
3. 单次 `collect_speech()` 入口的上下文契约测试，确保非圆桌发言也不会漏掉 observation / WorkingMemory / 信息边界提醒。
