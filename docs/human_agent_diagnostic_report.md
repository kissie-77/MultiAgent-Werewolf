# HumanAgent 设计诊断报告

诊断日期：2026-05-25
诊断范围：`HumanAgent`、真人技能输入、真人发言、`InformationHub` 圆桌流程、CLI/TUI 事件展示与可见性过滤。

## 总结论

当前 `HumanAgent` 设计不合理。它不是完整的真人玩家后端，而是一个挂在 `AgentProtocol` 上的 `input()` 占位符。

更严厉地说：项目配置层声称支持 `model="human"`，但运行时并没有把真人当作一等玩家处理。技能输入只是通用 prompt 文本输入；发言路径在主要圆桌流程中对真人甚至会断路；展示层默认上帝视角，还可能把私密事件展示给真人。

## 现状判断

| 能力 | 当前实现 | 诊断 |
| --- | --- | --- |
| 真人技能 | 通过 `HumanAgent.get_response()` 裸输入字符串 | 有入口，无真人专用接口 |
| 真人发言 | 理论上可走 `request_speech()` 文本解析 | 主圆桌流程中不可靠，全真人局直接不调用 |
| 输入校验 | 依赖 `Bridge` 从字符串里提数字或解析文本 | 缺少重试和明确错误提示 |
| UI/TUI 输入 | 无专门输入通道 | TUI 后台跑游戏时与 `input()` 设计冲突 |
| 信息隔离 | 事件模型有 `visible_to` | CLI/TUI 默认上帝视角，真人模式会泄密 |
| 测试 | 只检查继承关系 | 没覆盖真人玩法主路径 |

## 关键问题

### P0：真人发言主流程断路

证据：

- `src/llm_werewolf/agent_team/base.py:86` 的 `HumanAgent` 只实现 `get_response()`，内部直接 `input()`。
- `src/llm_werewolf/agent_team/information_hub.py:84` 将圆桌受众过滤为拥有 `agentscope_agent` 的玩家。
- `src/llm_werewolf/agent_team/information_hub.py:290` 如果没有 ReAct agent，`run_roundtable()` 直接返回空列表。
- 白天讨论、狼人讨论、PK 发言、警长发言都依赖 `run_roundtable()`。

复现结果：

在 6 个 `HumanAgent` 的最小局中，将 `input()` 替换成固定返回 `[[我发言了]]`，执行白天讨论阶段：

```text
input_calls=0
PLAYER_SPEECH=0
```

结论：全真人或全 demo 圆桌阶段不会询问真人输入，也不会产生玩家发言事件。

### P0：真人视角会看到不该看到的信息

证据：

- `src/llm_werewolf/game_runtime/event_visibility.py` 定义了 `visible_to` 规则，例如女巫刀口、预言家查验、狼人讨论等。
- `src/llm_werewolf/interface/cli.py:51` 直接把 `engine.on_event` 绑定到 `presenter.present_event`。
- `src/llm_werewolf/ui/console_presenter.py:153` 的 `viewer_id=None` 表示上帝视角，不过滤事件。
- `src/llm_werewolf/ui/tui_app.py:153` 直接把事件送进 `ChatPanel.add_event()`。
- `src/llm_werewolf/ui/components/chat_panel.py:156` 虽支持 `viewer_id`，但 TUI 入口没有传入真人玩家视角。

结论：只要真人玩家通过当前 CLI/TUI 观察游戏，就可能看到女巫、预言家、狼人频道等私密信息。这对狼人杀是致命问题。

### P1：技能输入没有真人专用接口

当前技能调用大致会经过：

- `PhaseInteraction.request_seat_choice()`
- `InformationHub.request_private_seat_choice()`
- `WerewolfAdapterBridge.request_seat_choice()`
- `agent.get_response(prompt)`

对 `HumanAgent` 来说，最后一步就是打印一整段 prompt，然后要求用户手动输入 `[[数字]]`。

问题：

- 没有候选项菜单。
- 没有按角色定制的输入流程，例如女巫救/毒/不行动、守卫守人、预言家查验。
- 没有输入重试。
- 没有超时、取消、确认。
- 没有把“选择动作”和“自然语言发言”区分成不同接口。

所以技能不是没法触发，而是没有被设计成人能舒服、可靠、不会误操作地使用。

### P1：发言接口名义存在，实际不成体系

`WerewolfAdapterBridge.request_speech()` 可以调用普通 agent 的 `get_response()` 并解析为 `SpeechDecision`，所以从局部函数看，真人发言不是完全没代码。

但问题在于主流程不直接使用这个能力，而是通过 `InformationHub.run_roundtable()`。该流程把有无 `agentscope_agent` 当成参与条件，导致真人在圆桌发言中被排除。

结论：发言接口属于“局部有解析，系统级没有打通”。

### P1：输入失败后会被随机或默认代打

证据：

- `src/llm_werewolf/game_runtime/engine/voting_phase.py:91` 投票阶段传入 `fallback_random=True`。
- `src/llm_werewolf/agent_team/bridge.py:644` 解析失败后可能随机选择目标。
- `src/llm_werewolf/agent_team/bridge.py:683` 是/否解析失败会默认 `False`。
- `src/llm_werewolf/agent_team/bridge.py:417` 女巫夜间决策失败默认 `none`。

对 LLM 来说，兜底也许是为了让自动局继续跑；对真人玩家来说，这是严重的产品错误。真人输错应该提示并重试，而不是系统偷偷替他随机投票或默认不行动。

### P1：`input()` 与异步/TUI 架构冲突

证据：

- `HumanAgent.get_response()` 是 `async` 方法，但内部调用阻塞式 `input()`。
- TUI 在 `src/llm_werewolf/ui/tui_app.py:118` 使用后台 worker 自动跑游戏。

问题：

- 阻塞事件循环。
- TUI 没有输入框/消息队列/玩家选择控件。
- 无法支持远程玩家、多人真人、超时或取消。

结论：真人输入不应该藏在 Agent 层的 `input()` 里，应由 interface/ui 层提供输入通道。

### P2：产品入口没有真正的 human 模式

证据：

- `src/llm_werewolf/game_runtime/config/player_config.py` 允许 `model="human"`。
- `src/llm_werewolf/agent_team/base.py:103` 会创建 `HumanAgent`。
- 但 `src/llm_werewolf/interface/modes.py` 只列出 `all_agent` 模式。
- `tests/interface/test_modes.py:21` 明确验证 `human_mixed` 是不支持模式。

结论：配置和工厂保留了 human 字样，但入口层没有把它作为可用玩法维护。

### P2：测试覆盖严重不足

当前 `tests/agent_team/test_base.py` 只检查：

```python
assert issubclass(HumanAgent, BaseAgent)
```

缺少以下关键测试：

- HumanAgent 白天讨论会被调用。
- HumanAgent 狼队讨论会被调用。
- HumanAgent 技能选择输错后会重试。
- HumanAgent 投票输错不会随机代打。
- CLI/TUI 在真人视角下不会展示不可见事件。
- TUI 不会因 `input()` 阻塞后台游戏 worker。

## 根因分析

当前架构把三件不同的事混在一起了：

1. 玩家决策协议：座位选择、是否选择、女巫动作、发言。
2. LLM 后端传输：AgentScope ReAct、结构化输出、MsgHub 记忆。
3. 真人输入交互：CLI/TUI 输入、候选项展示、校验、重试。

`HumanAgent` 被强行塞进 LLM agent 抽象里，但它既没有 AgentScope 记忆，也不该由 MsgHub 控制输入。结果就是：

- Hub 用 `agentscope_agent` 判断谁能进圆桌。
- 真人发言被过滤掉。
- 真人输入只能假装成 LLM 文本输出。
- 展示层不知道当前真人视角是谁。

## 建议整改方案

### 方案一：最低限度止血

目标：让现有 human 配置至少不会断路和泄密。

1. `InformationHub.run_roundtable()` 不应在 `react_agents` 为空时直接返回。真实发言循环应独立于 MsgHub 广播。
2. 真人发言应直接调用 `WerewolfAdapterBridge.request_speech()`，并照常触发 `on_speech`。
3. `ConsolePresenter` / `ChatPanel` 在 human 模式必须传入当前真人 `viewer_id`。
4. 对 `model="human"` 的玩家关闭随机兜底，解析失败要求重新输入。
5. 补测试：全 HumanAgent 白天讨论应产生 N 条 `PLAYER_SPEECH`。

### 方案二：正确设计

目标：把真人玩家做成一等输入后端。

建议新增抽象：

```text
HumanInputProvider
├── choose_seat(...)
├── choose_yes_no(...)
├── choose_witch_action(...)
├── choose_multi_targets(...)
└── speak(...)
```

CLI 实现可以用终端 prompt；TUI 实现应使用输入框、按钮或队列。`HumanAgent` 不再直接 `input()`，而是持有或引用 `HumanInputProvider`。

同时拆开两层概念：

- 真实受众：由游戏规则决定，包含 human/demo/LLM。
- MsgHub 参与者：仅 AgentScope ReAct agent，用于 LLM 记忆同步。

圆桌流程应该先产生真实发言事件，再只把需要进入 AgentScope 记忆的消息广播给 ReAct agent。

## 建议验收标准

修复后至少应满足：

- 6 个 HumanAgent 运行白天讨论，触发 6 次输入并产生 6 条 `PLAYER_SPEECH`。
- 混合 human + LLM 局中，真人发言能被 LLM 后续观察到。
- 真人玩家看不到 `visible_to` 不包含自己的事件。
- 真人技能选择输错时不会随机代打，会提示重试。
- TUI 下不使用阻塞式 `input()`。
- `human_mixed` 入口模式有明确配置和测试。

## 最终判定

当前 `HumanAgent` 不建议继续在现状上扩功能。应先修复两个 P0：

1. 真人发言圆桌断路。
2. 真人视角信息泄露。

否则 human 模式不是“体验差”，而是玩法规则和运行流程都不成立。
