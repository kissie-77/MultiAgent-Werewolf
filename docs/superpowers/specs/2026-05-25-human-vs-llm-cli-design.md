# CLI 人类玩家 vs LLM 重构设计

日期：2026-05-25

## 背景

本项目当前存在 `HumanAgent`，但它只是把一整段 LLM prompt 打印到 shell 后调用 `input()`。这使人类玩家必须理解 `[[数字]]`、结构化输出和 prompt 约定，也会在圆桌发言、投票、夜间技能等流程里被当成 LLM 文本解析。

诊断报告和 DeepSeek 运行观察显示，当前方案还有三个核心问题：

- 圆桌发言依赖 AgentScope 参与者，`HumanAgent` 没有 `agentscope_agent` 时容易被排除。
- CLI 默认上帝视角展示事件，真人模式会泄露身份、夜间行动和狼队信息。
- 技能/投票仍走 LLM 解析和 fallback 随机逻辑，真人输错时可能被系统随机代打。

本设计只覆盖 CLI/shell 中的单名人类玩家 vs 多个 LLM 玩家。

## 目标

- 人类玩家技能、投票、二选一决策只输入数字。
- 人类玩家发言只输入纯文字。
- 人类玩家不需要输入 `[[...]]`、JSON、工具调用格式或 prompt 标记。
- LLM 玩家继续使用现有 AgentScope / `WerewolfAdapterBridge` 流程。
- 人类玩家在 shell 中只看到自己可见的信息。
- 人类输入非法时重试，不随机代打。
- 人类发言必须进入事件日志，并广播给 LLM 记忆。

## 非目标

- 不实现 TUI、Web、多真人同局或远程多人输入。
- 不重写整个 AgentScope 后端。
- 不在本轮解决 DeepSeek 结构化输出错配问题，但保留现有 LLM 流程。
- 不改变狼人杀核心规则和胜负判定。

## 推荐方案

采用“新增真人输入层”的中等重构方案。

不继续扩展 `HumanAgent.get_response()`，而是新增 `HumanInputProvider` 抽象和 `ShellHumanInputProvider` 实现。`PhaseInteraction` 根据 actor 是否为 human，把真人决策转给 provider，把 LLM 决策继续转给 `WerewolfAdapterBridge`。

这样可以把人类 shell 输入、LLM prompt、AgentScope 记忆、游戏规则四类职责拆开。

## 组件设计

### HumanAgent

`HumanAgent` 只表示该座位由真人控制。它不再直接负责 `input()` 和 prompt 展示。

保留 `model="human"` 作为识别方式，并保留 `AgentProtocol` 所需的最小方法，避免破坏玩家创建和配置流程。

### HumanInputProvider

新增 interface 层输入协议，建议文件为：

`src/llm_werewolf/interface/human_input.py`

核心方法：

- `choose_seat(...) -> PlayerProtocol | None`
- `choose_yes_no(...) -> bool`
- `choose_witch_action(...) -> WitchNightDecision`
- `choose_multi_targets(...) -> list[PlayerProtocol] | None`
- `speak(...) -> SpeechDecision`

provider 接收已经过滤好的上下文、动作说明和候选玩家列表，负责把它们转成 shell 菜单，并负责输入校验和重试。

### ShellHumanInputProvider

Shell 实现只支持阻塞式终端输入，供 CLI 模式使用。

输入规则：

- 技能目标和投票目标：输入目标座位号。
- 允许跳过时显示 `0. 跳过/弃票`；不允许跳过时 `0` 无效。
- 二选一决策：显示 `1. 是`、`2. 否`。
- 女巫：先选行动编号，再按需输入毒药目标座位号。
- 多目标技能：分步输入，每次一个座位号。
- 发言：输入一行非空纯文字，不做 `[[...]]` 解析。

### PhaseInteraction

`PhaseInteraction` 增加可选 `human_input_provider`，并提供设置方法，便于 CLI 和测试注入。

每个交互入口先判断 actor 的 agent：

- `model == "human"`：调用 `HumanInputProvider`。
- 其他模型：调用现有 `InformationHub` / `WerewolfAdapterBridge` 流程。

真人分支不使用 `fallback_random`。当输入非法时由 provider 重试；当缺少 provider 时抛出明确错误。

### InformationHub

`run_roundtable()` 的真实发言循环必须独立于 AgentScope 参与者。

新的行为：

- 即使没有 `react_agents`，也要遍历 speakers 并收集发言。
- LLM speaker 仍通过 `WerewolfAdapterBridge.request_speech()` 生成发言。
- human speaker 通过 `PhaseInteraction` 或 provider 生成 `SpeechDecision`。
- 若存在 LLM audience，则把公开发言通过 MsgHub 广播给这些 LLM。
- `on_speech` 必须对 human speaker 同样触发，以写入 `PLAYER_SPEECH` / 狼聊事件。

这会修复人类在白天讨论、狼人夜聊、PK 发言、警上发言中不产生发言的问题。

### CLI 入口

CLI 增加 `participation="human_mixed"` 模式，建议默认映射：

- `human_mixed / badge_flow` -> `configs/human-mixed-deepseek.yaml`

该配置包含 1 个 `model: human` 玩家和其余 DeepSeek LLM 玩家。配置文件只引用 `DEEPSEEK_API_KEY` 环境变量，不写入真实 key。

CLI 在 `setup_game()` 后定位唯一 human player：

- 若 `human_mixed` 下没有 human player，报错。
- 若超过 1 个 human player，报错。
- 创建 `ShellHumanInputProvider` 并注入 `engine.phase_interaction`。
- 设置 `engine.on_event` 时传入该 human player 的 `player_id` 作为 viewer。

### ConsolePresenter

人类视角下必须区分两件事：

- 不展示上帝视角夜间行动汇总。
- 仍展示本人可见的私密结果，例如预言家查验、女巫刀口、自己的投票、自己的守护结果。

因此 `viewer_id` 不为 `None` 时，`present_event()` 先按 `event.is_visible_to(viewer_id)` 过滤，然后对可见私密事件使用简洁文本输出，不再无条件吞掉所有夜间行动事件。

## 数据流

### 技能 / 投票

1. 角色 planner 或投票阶段调用 `PhaseInteraction.request_seat_choice()`。
2. `PhaseInteraction` 判断 actor 是否 human。
3. human 分支调用 `ShellHumanInputProvider.choose_seat()`。
4. provider 显示当前动作和候选座位，读取数字并校验。
5. 返回 `PlayerProtocol | None` 给原有 action 构造逻辑。

### 女巫

1. `plan_witch_actions()` 调用 `request_witch_night_choice()`。
2. human 分支显示药水状态和刀口信息。
3. 用户输入行动编号。
4. 若选毒，再输入毒药目标座位号。
5. 返回 `WitchNightDecision`，后续仍由现有 action 结算。

### 发言

1. 白天讨论、狼聊、PK、警上发言调用 roundtable。
2. human speaker 调用 `ShellHumanInputProvider.speak()`。
3. provider 读取纯文字，构造 `SpeechDecision(public_speech=文本, private_thought=None)`。
4. `on_speech` 写入事件日志。
5. 若听众中有 LLM，则公开发言广播进 MsgHub。

## 错误处理

- 非数字输入：提示“请输入数字”，继续重试。
- 数字不在候选座位：展示有效座位并重试。
- 不允许跳过时输入 0：提示该动作必须选择目标。
- 发言为空：提示重新输入。
- human 模式未注入 provider：抛出 `RuntimeError`，提示 CLI 注入缺失。
- human_mixed 配置中 human 数量不是 1：启动时报错。

## 测试计划

新增或调整测试：

- `ShellHumanInputProvider.choose_seat()` 非法输入后重试，并返回正确玩家。
- `ShellHumanInputProvider.speak()` 接收纯文字，返回 `SpeechDecision`。
- 女巫 action 菜单返回 `save`、`poison`、`none` 的正确结构。
- 丘比特多目标分步输入返回两个不同玩家。
- `PhaseInteraction` 对 human actor 走 provider，对 LLM actor 保持现有 hub/bridge。
- `InformationHub.run_roundtable()` 在 human speaker 场景触发 `on_speech`。
- `ConsolePresenter` 在 human viewer 下过滤不可见事件，但展示本人可见私密结果。
- `resolve_config_path(participation="human_mixed", rules="badge_flow")` 返回新配置。

## 验收标准

- 启动 human_mixed CLI 后，人类玩家技能和投票只需输入数字。
- 人类发言只需输入纯文字，LLM 后续能引用这段发言。
- 人类看不到不可见身份、其他玩家夜间私密行动、非己方狼聊。
- 人类输错数字会重试，不会随机代打。
- 现有 all_agent 配置和测试不因该重构退化。

## 实施顺序建议

1. 新增 provider 接口、shell 实现和单元测试。
2. 给 `PhaseInteraction` 增加 human provider 分支。
3. 调整 `InformationHub.run_roundtable()` 支持 human speaker。
4. 调整 CLI human_mixed 模式和 viewer 过滤。
5. 修正 `ConsolePresenter` human viewer 的私密事件展示。
6. 新增 human-mixed DeepSeek 配置和模式测试。
7. 运行聚焦测试，再做一次 CLI smoke 验证。
