# 给小米 mimo 的任务单

> 你先别碰自进化主编排逻辑，也别改 skill 采纳规则本身。你主要接**测试、文档、历史数据整理和展示产物**这几块。

---

## 1. 补 skill 状态流转测试

**目标：** 补齐 `draft / active / deprecated` 这条线的测试覆盖。

**要做：**
- 测试 winning skill 会从 `draft` 升到 `active`
- 测试 `deprecated` skill 不会被 runtime 默认加载
- 测试 `load_role_skills(include_draft=False)` 只吃 `active`
- 测试 `include_draft=True` 时 `deprecated` 仍然被排除

**交付：**
- 补到 `tests/evaluation/test_skill_extractor.py`
- 如果更合适，也可以拆一点到 `tests/agent_team/`

---

## 2. 写历史 run 整理脚本

**目标：** 把旧 run 尽量补成现在版本链可用的格式。

**要做：**
- 扫描本地历史 run 目录
- 对缺 `leaderboard_entry.json` 的目录补生成
- 对缺 `experiment_meta.json` 的目录补生成
- 尽量自动推断 `previous_run_dir`
- 输出一份清单，标记：
  - 可直接纳入版本链
  - 只能部分利用
  - 建议废弃

**交付：**
- 一个脚本，放 `scripts/` 或合适位置
- 一份运行说明文档

---

## 3. 补 evolution 产物说明文档

**目标：** 把现在已有的闭环产物讲清楚，方便后面继续接主 runner。

**要做：** 整理这些产物的作用和关系：
- `experiment_meta.json`
- `leaderboard_entry.json`
- `skill_snapshot.json`
- `skill_diff.json`
- `coach_summary.json`
- `best_summary.json`
- `model/prompt/skill leaderboard`
- `ab_reports`

**交付：**
- `docs/evaluation/` 下新增或更新一份文档
- 写清"谁生成、什么时候生成、后面谁会消费"

---

## 4. 增强 leaderboard / 汇总展示页

**目标：** 把现有评测结果更适合直接看和汇报。

**要做：**
- 补"当前 active skill 清单"视图或摘要
- 补"每轮版本摘要页"
- 如果方便，补一个 evolution overview md
- **不要改核心聚合逻辑**，只做产物增强

**交付：**
- `leaderboards/` 相关新增 md/json 产物生成逻辑
- 对应测试

---

## 5. 补多轮 evolution 的 fixture 和测试数据

**目标：** 给后面主编排器接入准备测试基础。

**要做：**
- 设计 2~3 轮伪版本 fixture
- 每轮包含：
  - `summary`
  - `manifest`
  - `skill_snapshot`
  - `skill_diff`
  - `experiment_meta`
- 方便后面直接测 version chain / leaderboard / A-B

**交付：**
- 测试夹具
- 不要写主 runner 逻辑
- 重点保证测试数据结构完整、可复用

---

## 明确不要碰的部分

这些先别动：
- 自进化主 runner / orchestrator
- skill 采纳阈值规则本身
- 版本回滚机制设计
- 初始版 vs 终局版评测口径
- runtime 默认策略集的核心定义

## 做事原则

- 只做上面分给你的范围
- 优先补测试、文档、数据整理脚本、展示产物
- 不要顺手重构主逻辑
- 不确定边界先停，不要自作主张扩改
