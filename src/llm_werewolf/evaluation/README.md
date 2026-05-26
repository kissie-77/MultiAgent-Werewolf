# Evaluation 模块

评测设计与队友对接：**[docs/吕祎晗-测评模块设计.md](../../../docs/吕祎晗-测评模块设计.md)**

| 子包 | 路径 | CLI / 触发 |
| --- | --- | --- |
| **正确性评测** | [`correctness/`](./correctness/README.md) | `werewolf-eval` |
| **赛后分析** | [`post_game/`](./post_game/README.md) | `finalize_run`；`werewolf-vote-swing` |

```text
evaluation/
  correctness/     # runner, checkers, recorder, metrics, scenarios
  post_game/       # pipeline, scoring, log_views, skills, MVP
```

```bash
uv run pytest tests/evaluation -q --no-cov
```
