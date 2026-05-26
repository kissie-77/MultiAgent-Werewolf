# Game Correctness Evaluation

离线评测游戏系统正确性（角色技能、信息隔离、胜负、阶段流程）。默认 `DemoAgent`，无需 API key。

## 运行

```powershell
uv run werewolf-eval --scenario smoke_6p_basic --games 3 --timeout_seconds 20 --output_dir eval_runs/manual-smoke
```

```powershell
uv run werewolf-eval --scenario regression_default_demo --games 1 --timeout_seconds 20 --output_dir eval_runs/manual-regression
```

## 场景

| Scenario | 用途 |
| --- | --- |
| `smoke_6p_basic` | 6 人基础局 |
| `regression_default_demo` | 16 人默认配置回归 |

## 产物

```text
eval_runs/<run-name>/
  manifest.json
  summary.json
  metrics.csv
  report.md
  games/<game_id>/
    events.jsonl
    snapshots.jsonl
    checks.json
    errors.jsonl
```

## Checkers

| Checker | 检查内容 |
| --- | --- |
| `RoleSkillChecker` | 技能/动作事件结构化字段 |
| `InformationIsolationChecker` | 私有事件是否泄露到他人 observation |
| `VictoryCheckerEvaluator` | `game_ended` 与终局 winner |
| `AsyncFlowChecker` | 阶段流转白名单 |
| `DecisionConsistencyChecker` | 决策目标与事件一致 |
| `PromptBadCaseChecker` | Prompt 调优 bad case（多为 INFO） |
| `RuntimeErrorEventChecker` | 引擎 `EventType.ERROR` |

赛后分析见 [`../post_game/README.md`](../post_game/README.md)。
