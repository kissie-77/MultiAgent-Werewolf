# Game Correctness Evaluation

这个组件用于离线评测狼人杀游戏系统本身的正确性，优先检查角色技能、信息隔离、胜负判定和异步阶段流程。它默认使用 `DemoAgent`，不需要真实模型 API key。

对局结束后会自动跑 **PostGame**（`evaluation/post_game/`）：阵营匹配说服分析、**情景记忆 episode 导出**（`episodic_reports.json`，与 `agent_team.memory.EpisodicMemory` 同源）、Prompt 提案 JSON、**Skill 提取（MD + JSON）**、`coach_summary.json`（为 Skill 附加 POV episode 证据）。真实 LLM 对局由 `interface/finalize_run.py` 触发；批量 eval 默认 `skip_llm=True`。

## 运行方式

运行 6 人基础 smoke 评测：

```powershell
uv run werewolf-eval --scenario smoke_6p_basic --games 3 --timeout_seconds 20 --output_dir eval_runs/manual-smoke
```

运行默认 16 人回归评测：

```powershell
$env:PYTHONUTF8='1'
$env:PYTHONIOENCODING='utf-8'
uv run werewolf-eval --scenario regression_default_demo --games 1 --timeout_seconds 20 --output_dir eval_runs/manual-regression
```

运行组件测试：

```powershell
uv run --with "pytest>=8.2" pytest -o addopts='' tests/evaluation -q
```

## 内置场景

| Scenario                  | 用途                                                              |
| ------------------------- | ----------------------------------------------------------------- |
| `smoke_6p_basic`          | 6 人基础局，覆盖狼人、预言家、女巫、村民等核心流程。              |
| `regression_default_demo` | 16 人默认角色配置，用于捕获复杂配置中的阶段、角色和事件结构问题。 |

## 输出产物

每次评测会生成一个输出目录：

```text
eval_runs/<run-name>/
  manifest.json
  summary.json
  metrics.csv
  report.md
  games/<game_id>/events.jsonl
  games/<game_id>/snapshots.jsonl
  games/<game_id>/checks.json
  games/<game_id>/errors.jsonl
```

其中：

- `events.jsonl`：游戏事件流。
- `snapshots.jsonl`：关键状态快照。
- `checks.json`：每局 checker 结果。
- `errors.jsonl`：崩溃、超时或 observation 构建异常。
- `summary.json`：机器可读的汇总指标。
- `metrics.csv`：表格格式指标。
- `report.md`：人类可读报告。

## 当前 Checkers

| Checker                       | 检查内容                                                       |
| ----------------------------- | -------------------------------------------------------------- |
| `RoleSkillChecker`            | 角色动作事件是否具备必要结构化字段，如 `target_id`、`result`。 |
| `InformationIsolationChecker` | 私有事件是否泄露到无权限玩家的 observation。                   |
| `VictoryCheckerEvaluator`     | `GAME_ENDED` 事件里的 winner 是否和最终 game state 一致。      |
| `AsyncFlowChecker`            | 阶段流转是否符合 setup/night/day/voting/ended 的允许顺序。     |
| `RuntimeErrorEventChecker`    | 将游戏过程中记录的 `EventType.ERROR` 归入评测失败项。          |

## 当前 Metrics

| Metric                           | 含义                                                |
| -------------------------------- | --------------------------------------------------- |
| `total_games`                    | 总评测局数。                                        |
| `completed_games`                | 成功结束并产生 winner 的局数。                      |
| `completion_rate`                | 完成率。                                            |
| `crashed_games`                  | 抛出未处理异常的局数。                              |
| `crash_rate`                     | 崩溃率。                                            |
| `timeout_games`                  | 单局超过 `timeout_seconds` 的局数。                 |
| `timeout_rate`                   | 超时率。                                            |
| `avg_rounds_per_game`            | 平均游戏轮数。                                      |
| `role_skill_violation_count`     | 角色技能/动作事件结构违规数。                       |
| `information_leak_count`         | 信息隔离违规数。                                    |
| `victory_rule_violation_count`   | 胜负判定一致性违规数。                              |
| `phase_order_violation_count`    | 阶段流转违规数。                                    |
| `invalid_action_count`           | 预留的非法动作计数；当前第一版尚未由 checker 写入。 |
| `exception_count_by_role`        | 按角色聚合的运行时错误数。                          |
| `exception_count_by_phase`       | 按阶段聚合的运行时错误数。                          |
| `missing_structured_event_count` | 缺少结构化字段的事件数。                            |
| `top_errors`                     | 最高频错误或违规摘要。                              |

## 当前限制

- 第一版主要检查系统正确性，不评价模型强弱。
- `invalid_action_count` 目前只是指标字段，后续需要接入更细的 action validation checker。
- 角色技能语义检查仍依赖事件结构，现阶段重点先发现缺字段和流程违规。
- 评测输出目录 `eval_runs/` 已加入 `.gitignore`，默认不提交本地评测产物。
