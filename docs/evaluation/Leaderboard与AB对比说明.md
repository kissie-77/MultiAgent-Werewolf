# Leaderboard 与 A/B 对比说明

## 目标

这一套能力是把现有评测体系再往前推一步，不只是看单局复盘，还要能看版本演进效果。

它解决的是四件事：

- 让一次实验有稳定的版本标识
- 让多次实验能被聚合成榜单
- 让两个版本能直接做 A/B 对比
- 让 Coach 产出的 skill 变化能挂到版本链上

## 现在有哪些产物

### 单次实验产物

- `leaderboard_entry.json`
  作用：一条实验记录，给 leaderboard 和 A/B 对比用
- `experiment_meta.json`
  作用：保存该实验的版本元信息，以及上一版 skill 快照来源

### 聚合产物

- `leaderboards/leaderboard.json`
- `leaderboards/leaderboard.csv`
- `leaderboards/leaderboard.md`

作用：把多个 run 目录下的实验结果汇总成排行榜。

### 对比产物

- `ab_reports/ab_<A>_vs_<B>.json`
- `ab_reports/ab_<A>_vs_<B>.md`

作用：比较两个版本的核心指标，并给出简单推荐结论。

### Coach 闭环产物

- `coach_summary.json`
- `skill_snapshot.json`
- `skill_diff.json`

作用：记录本次技能快照，以及相对上一版的变化。

## experiment_meta.json 是干什么的

`experiment_meta.json` 是版本链的锚点。它主要保存：

- `version_id`
- `model`
- `prompt_version`
- `skill_version`
- `scenario`
- `notes`
- `previous_run_dir`
- `previous_skill_snapshot_path`

其中后两个字段用于给 Coach 自动找到“上一版 skill 快照”。

优先级规则：

1. 如果 `build_entry()` 传入的是明确参数，就以显式参数为准。
2. 如果传入的是默认值，就优先读取 `experiment_meta.json`。
3. 如果 meta 里也没有，再回退到原本逻辑。

## Coach 如何自动接上一版

现在 Coach 读取上一版快照的顺序是：

1. 先读当前 run 目录下的 `skill_snapshot.previous.json`
2. 如果没有，再读 `experiment_meta.json`
3. 如果 meta 里有 `previous_skill_snapshot_path`，直接用这个文件
4. 否则如果有 `previous_run_dir`，就读取 `<previous_run_dir>/skill_snapshot.json`
5. 如果这两个字段都没填，系统会尝试在同级目录里自动找最近一个有效 run

这样就不用再手工复制一份 `skill_snapshot.previous.json` 到当前目录了。

自动推断规则是保守的：

- 只在当前 run 的同级目录里找
- 只认包含 `skill_snapshot.json` 的目录，或者至少同时包含 `summary.json` 和 `manifest.json` 的目录
- 会排除当前 run 自己
- 候选里按最近修改时间取最新一个

如果你明确传了 `previous_run_dir` 或 `previous_skill_snapshot_path`，仍然以显式输入为准。

## 命令入口

### 生成单次实验 entry

```powershell
uv run python -m llm_werewolf.evaluation.leaderboard.cli entry eval_runs/run_xxx --version-id kimi_v2_baseline --model kimi --prompt-version v2 --skill-version baseline --scenario smoke_6p_basic --notes baseline memory-only
```

如果你要显式指定上一版 skill 来源，也可以这样：

```powershell
uv run python -m llm_werewolf.evaluation.leaderboard.cli entry eval_runs/run_xxx --version-id coach_v2 --model kimi --prompt-version v3 --skill-version coach_v2 --previous-run-dir ../run_prev
```

### 生成总榜单

```powershell
uv run python -m llm_werewolf.evaluation.leaderboard.cli build eval_runs
```

### 做 A/B 对比

```powershell
uv run python -m llm_werewolf.evaluation.leaderboard.cli compare eval_runs/run_a/leaderboard_entry.json eval_runs/run_b/leaderboard_entry.json
```

## 这套能力现在能证明什么

1. 评测系统已经不只是“跑完一局出复盘”，而是能形成版本级证据。
2. Coach 产出的 skill 变化已经能和实验版本挂钩。
3. Skill 版本、Prompt 版本、模型版本都可以进入统一比较链路。
4. 项目已经具备了 leaderboard 和 A/B 评估能力。

## 当前边界

现在这套闭环已经可用，但还保留一个现实边界：

- leaderboard 现在聚合的是已有评测指标，还没有再往上做更复杂的统计显著性分析

这不是结构缺口，而是后续可增强项。
