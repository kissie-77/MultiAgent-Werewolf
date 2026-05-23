# Game Correctness Evaluation Design

## 1. 背景

当前项目已经具备狼人杀游戏主循环、异步阶段执行、角色系统、事件日志、玩家观察构建和基础状态序列化能力。README 中的“评测与复盘体系”仍处于未实现状态。最近手动运行发现，控制台 demo 可以完整跑完，但 16 人默认配置下 `AlphaWolf.get_private_notes` 会触发 `TypeError: super(type, obj): obj must be an instance or subtype of type`，TUI 后台 worker 也会因此退出。

本设计先聚焦游戏系统正确性评测，不评测模型强弱，不建设 Web 复盘页面。目标是建立一个离线、可复现、可批量运行的评测框架，用来发现角色技能、信息隔离、胜负判定和异步流程中的 bug。

## 2. 目标

- 批量运行离线评测局，默认使用 demo 或 scripted agent，避免 API 成本和模型随机性影响规则验证。
- 捕获每局的事件、状态快照、异常和阶段流转信息，保留可复盘证据。
- 计算系统正确性指标，包括完成率、崩溃率、角色技能违规、信息泄露、胜负判定错误和阶段流转错误。
- 输出文件报告，第一版面向命令行和论文实验记录，后续可被 Web 复盘页面读取。
- 尽量复用现有 `GameEngine`、`EventLogger`、`ObservationBuilder` 和 `serialization`，减少对游戏核心逻辑的侵入。

## 3. 非目标

- 第一版不做真实模型排行榜。
- 第一版不做 Web 前端、数据库、任务队列或实验平台。
- 第一版不使用 LLM judge 评价发言质量。
- 第一版不重写游戏引擎，只补充评测所需的轻量钩子和结构化记录。

## 4. 总体架构

新增独立模块 `src/llm_werewolf/evaluation/`：

```text
src/llm_werewolf/evaluation/
  __init__.py
  runner.py
  scenarios.py
  recorder.py
  checkers.py
  metrics.py
  reporter.py
  models.py
```

各模块职责：

- `runner.py`：读取评测配置，按场景批量创建并运行游戏，控制随机种子、超时和并发。
- `scenarios.py`：定义可复现测试场景，包括玩家数量、角色列表、agent 类型、随机种子和预期规则。
- `recorder.py`：订阅 `GameEngine.on_event`，记录事件、状态快照、错误和运行元数据。
- `checkers.py`：实现正确性检查器，检测角色技能、信息隔离、胜负判定和阶段流转问题。
- `metrics.py`：把每局检查结果聚合成指标。
- `reporter.py`：生成 `summary.json`、`metrics.csv` 和 `report.md`。
- `models.py`：定义评测产物的数据模型，确保 JSON 结构稳定。

命令行入口可以在后续实现时加入：

```text
uv run werewolf-eval configs/eval/game_correctness.yaml
```

## 5. 数据流

1. `runner` 加载评测配置。
2. `runner` 从 `scenarios` 创建一个或多个 `EvaluationScenario`。
3. 每个场景构建 `GameEngine`、players 和 roles。
4. `recorder` 接管 `engine.on_event`，同时保留原始事件处理能力。
5. `runner` 使用 `asyncio.wait_for` 运行 `engine.play_game()`，为每局设置硬超时。
6. 每个事件到达时，`recorder` 写入 `events.jsonl`，并按配置保存状态快照到 `snapshots.jsonl`。
7. 游戏结束、崩溃或超时后，`checkers` 对事件、快照和异常进行检查。
8. `metrics` 聚合所有局的结果。
9. `reporter` 输出人类可读和机器可读报告。

输出目录：

```text
eval_runs/<timestamp>/
  manifest.json
  games/<game_id>/events.jsonl
  games/<game_id>/snapshots.jsonl
  games/<game_id>/errors.jsonl
  games/<game_id>/checks.json
  summary.json
  metrics.csv
  report.md
```

## 6. 场景设计

第一版提供三类场景：

- `smoke_6p_basic`：6 人基础局，覆盖狼人、村民、预言家、女巫等核心流程。
- `role_matrix`：按角色构造小型定向场景，用来触发特定技能，例如女巫救毒、守卫保护、猎人死亡技能。
- `regression_default_demo`：运行当前 `configs/demo.yaml` 等默认配置，用来发现真实默认路径中的崩溃和阶段问题。

场景必须支持固定随机种子。为了让角色和行动更可控，后续实现中应引入 `ScriptedAgent`，它按脚本返回目标或 yes/no 答案；demo agent 仍可用于随机 smoke test。

## 7. 检查器

### 7.1 RoleSkillChecker

职责：检查角色技能是否按规则生效。

第一批覆盖：

- 狼人夜杀目标必须是合法存活目标。
- 女巫救人后，对应目标不应因当晚狼人刀死亡。
- 女巫毒人后，目标应进入死亡处理流程。
- 守卫保护成功时，被保护目标不应被狼人刀杀。
- 预言家查验结果不得改变游戏状态，只能产生允许范围内的私有信息。
- 猎人或狼王死亡技能触发时，目标必须合法，且不能重复触发。

检查依据优先使用结构化事件字段；缺字段时使用快照差异兜底，并在报告中标记“事件结构不足”。

### 7.2 InformationIsolationChecker

职责：检查不该泄露的信息是否出现在玩家可见事件或 prompt 中。

第一批规则：

- `visible_to` 为私有列表的事件只能被列表内玩家看到。
- 狼人夜聊事件不得出现在好人玩家 observation 中。
- 玩家 observation 不得包含其他玩家的隐藏角色身份，除非规则允许。
- 预言家查验结果只能进入预言家本人可见信息。
- 女巫夜间救人信息不能公开给所有玩家，除非游戏规则明确公开。

该 checker 需要通过 `GameEngine.build_player_observation` 或未来的结构化 observation hook 收集每个玩家视角。

### 7.3 VictoryCheckerEvaluator

职责：检查胜负判定是否符合规则。

第一批规则：

- 狼人全灭时，好人胜。
- 狼人数量大于或等于非狼人存活人数时，狼人胜。
- 情侣胜利优先级按现有 `VictoryChecker` 的规则校验。
- 游戏结束后不得继续进入夜晚、白天讨论或投票阶段。
- `winner`、`GAME_ENDED` 事件和最终存活阵营必须一致。

### 7.4 AsyncFlowChecker

职责：检查异步流程和阶段推进是否正确。

第一批规则：

- 每局必须在配置超时内结束或被标记为 timeout。
- 阶段顺序必须符合 setup -> night -> optional sheriff -> day discussion -> day voting -> night。
- 同一阶段不得无原因重复执行。
- `play_game` 抛出的异常必须被记录到 `errors.jsonl`。
- 游戏结束后不得有新的行动事件。
- 后台 worker 或未 await 任务导致的异常必须算作流程错误。

## 8. 指标

第一版指标：

```text
total_games
completed_games
completion_rate
crashed_games
crash_rate
timeout_games
timeout_rate
avg_rounds_per_game
role_skill_violation_count
information_leak_count
victory_rule_violation_count
phase_order_violation_count
invalid_action_count
exception_count_by_role
exception_count_by_phase
missing_structured_event_count
```

这些指标足以回答四个问题：

- 游戏能不能稳定跑完。
- 哪些角色技能有规则 bug。
- 玩家是否看到了不该看的信息。
- 胜负和阶段推进是否可信。

## 9. 错误处理

- 单局失败不能中断整批评测；`runner` 必须继续执行后续场景。
- 崩溃、超时、checker 异常要分别记录，避免把评测器自身 bug 混入游戏 bug。
- 报告中保留异常类型、消息、角色、阶段、round、game_id 和最后若干事件。
- 如果事件结构不足导致无法严格判断，checker 输出 `inconclusive`，不伪装成通过。

## 10. 与现有代码的集成点

优先复用：

- `GameEngine.setup_game`
- `GameEngine.play_game`
- `GameEngine.get_events`
- `GameEngine.build_player_observation`
- `EventLogger`
- `serialize_game_state`
- `create_game_config_from_player_count`
- `create_roles`
- `DemoAgent`

可能需要补充：

- `ScriptedAgent`，用于可控行动。
- 更结构化的 action/result 事件字段，例如 `actor_id`、`target_id`、`action_type`、`success`、`reason`。
- 一个 CLI 入口 `werewolf-eval`。
- 每局运行前设置随机种子，保证可复现。

## 11. 测试策略

第一批测试：

- 单元测试 `RoleSkillChecker`，用手工事件和快照验证规则。
- 单元测试 `InformationIsolationChecker`，覆盖公开事件、私有事件、狼人私聊和角色泄露。
- 单元测试 `VictoryCheckerEvaluator`，构造固定存活阵营。
- 单元测试 `AsyncFlowChecker`，构造合法和非法阶段序列。
- 集成测试运行 1 局 6 人 demo 场景，验证产物目录和报告文件存在。
- 回归测试覆盖已发现的 `AlphaWolf.get_private_notes` 异常，确保它会被记录为角色相关崩溃。

## 12. 第一版验收标准

- 能通过一个命令运行至少 10 局离线评测。
- 每局都生成事件、快照、错误和检查结果文件。
- 总报告能展示完成率、崩溃率、违规统计和最高频错误。
- 默认 demo 配置中的 Alpha Wolf 异常能被稳定捕获并归因。
- 6 人基础场景能在无真实 API key 的环境下完成。
- 信息隔离 checker 至少能发现人工构造的私有事件泄露。
- 评测器自身异常不会导致整批评测提前终止。

## 13. 后续扩展

- 增加真实模型对战指标。
- 增加 Web 复盘页面读取 `eval_runs` 数据。
- 增加 LLM judge 做发言质量和推理质量评估。
- 增加成本、token、延迟统计。
- 增加 CI 中的轻量 smoke eval。
