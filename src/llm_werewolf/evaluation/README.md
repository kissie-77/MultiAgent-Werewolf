# Evaluation 模块

评测分为两个子包，职责与入口分离：

| 子包 | 路径 | CLI / 触发 |
| --- | --- | --- |
| **正确性评测** | [`correctness/`](./correctness/README.md) | `werewolf-eval` |
| **赛后分析** | [`post_game/`](./post_game/README.md) | `interface/finalize_run`（真实对局）；`werewolf-vote-swing`（仅摇摆报告） |

```text
evaluation/
  correctness/     # runner, checkers, recorder, metrics, scenarios
  post_game/         # pipeline, vote_swing, camp_persuasion, log_views, scoring, skills
```

运行全部评测测试：

```powershell
uv run --with "pytest>=8.2" pytest -o addopts='' tests/evaluation -q
```
