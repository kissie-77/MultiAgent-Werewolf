# backfill_run_artifacts.py — 历史 Run 补全脚本

## 用途

扫描 `artifacts/runs/` 下的历史 run 目录，对缺失 `leaderboard_entry.json` 和 `experiment_meta.json` 的目录补生成，并输出一份分类报告。

## 用法

```bash
# dry-run（只分析不写入）
python scripts/backfill_run_artifacts.py --dry-run

# 正式执行
python scripts/backfill_run_artifacts.py

# 指定目录
python scripts/backfill_run_artifacts.py --runs-dir path/to/runs
```

## 分类标准

| 状态 | 含义 | 判定条件 |
|------|------|----------|
| `usable` | 可直接纳入版本链 | 所有关键产物齐全（benefit/intention/skills/camp） |
| `partial` | 只能部分利用 | 有 manifest 但缺部分产物，或 PostGame 分析失败 |
| `deprecated` | 建议废弃 | 缺 manifest 且无 events.jsonl，或关键产物缺失过多 |

## 补全产物

- `leaderboard_entry.json`：从 manifest + benefit/intention scores 构建，用于 leaderboard 聚合
- `experiment_meta.json`：版本元信息，自动推断 `previous_run_dir`（取同目录下最近的 run）

## 产出

- 每个 run 目录下写入 `leaderboard_entry.json` 和 `experiment_meta.json`
- `artifacts/runs/backfill_report.md`：汇总报告，标记每个 run 的状态和执行动作
