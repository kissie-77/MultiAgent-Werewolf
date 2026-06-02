# Evolution 产物说明文档

> **状态**：deprecated
> **替代文档**：[DESIGN.md](../../evaluation/DESIGN.md) §9、§12
> **说明**：结论已合并进 DESIGN；本文仅备查，请勿再更新。

---

本文档梳理 evolution 闭环中所有产物的**生成时机、内容结构、下游消费方**。

---

## 产物总览

```
run_dir/
├── post_game_manifest.json     ← PostGame 流水线索引
├── post_game_analysis.json     ← LLM 复盘结果
├── post_game_report.md         ← 人类可读复盘报告
├── events.jsonl                ← 原始事件日志
├── vote_intentions.jsonl       ← 投票意图序列
│
├── camp_persuasion_summary.json ← 阵营说服力分析
├── benefit_scores.json         ← 收益评分
├── intention_scores.json       ← 意图评分
│
├── role_skills.json            ← 提取的 Skill 候选列表
├── skills/                     ← 写入 Skill MD 文件
│   └── <role>/<skill_id>.md
│
├── prompt_proposals.json       ← Prompt 改进建议
│
├── coach_summary.json          ← Coach 层汇总
├── skill_snapshot.json         ← 当前 Skill 快照
├── skill_diff.json             ← 与上一版 Skill 的 diff
│
├── leaderboard_entry.json      ← Leaderboard 条目
├── experiment_meta.json        ← 实验版本元信息
│
└── views/                      ← 可视化视图
    ├── god_timeline.md
    ├── player_*.md
    └── ...
```

---

## 一、基础产物

### `post_game_manifest.json`

| 字段 | 说明 |
|------|------|
| 生成时机 | PostGame 流水线启动时写入 |
| 内容 | 流水线索引：run_dir、prompt_version、winner_camp、roster、各步骤状态 |
| 消费方 | leaderboard_entry 构建、backfill 脚本、前端回放页 |
| 生成器 | `post_game/pipeline.py` |

### `events.jsonl`

| 字段 | 说明 |
|------|------|
| 生成时机 | 对局过程中由 EventLogger 实时写入 |
| 内容 | 每行一个 JSON Event（event_type、phase、round_number、message、data、visible_to） |
| 消费方 | PostGame 分析、回放前端、views 生成、skill 提取 |
| 生成器 | `game_runtime/events/events.py` |

### `post_game_analysis.json`

| 字段 | 说明 |
|------|------|
| 生成时机 | PostGame 流水线 LLM 复盘步骤完成后 |
| 内容 | mode（success/failed）、summary_zh、prompt_suggestions、risks |
| 消费方 | post_game_report.md 生成、prompt_proposals |
| 生成器 | `post_game/eval_agent.py` |

---

## 二、评分产物

### `benefit_scores.json`

| 字段 | 说明 |
|------|------|
| 生成时机 | PostGame 评分步骤 |
| 内容 | 每个玩家的收益评分（total_score、分项得分） |
| 消费方 | leaderboard_entry 构建、MVP 计算 |
| 生成器 | `scoring/benefit.py` |

### `intention_scores.json`

| 字段 | 说明 |
|------|------|
| 生成时机 | PostGame 评分步骤 |
| 内容 | 每个玩家的意图一致性评分（avg_score） |
| 消费方 | leaderboard_entry 构建 |
| 生成器 | `scoring/intention.py` |

### `camp_persuasion_summary.json`

| 字段 | 说明 |
|------|------|
| 生成时机 | PostGame 阵营分析步骤 |
| 内容 | 各阵营的说服力分析（speech influence、vote swing） |
| 消费方 | skill 提取（判断获胜阵营的发言策略） |
| 生成器 | `post_game/camp_persuasion.py` |

---

## 三、Skill 产物

### `role_skills.json`

| 字段 | 说明 |
|------|------|
| 生成时机 | PostGame skill 提取步骤 |
| 内容 | 提取的 Skill 候选列表（skill_id、camp、status、weight、skill_card、evidence） |
| 消费方 | skill MD 写入、coach 分析、leaderboard |
| 生成器 | `post_game/skill_generation/skill_extractor.py` |

### `skills/<role>/<skill_version>/<skill_id>.md`

| 字段 | 说明 |
|------|------|
| 生成时机 | skill 提取后，通过质量门控的候选写入 |
| 内容 | YAML frontmatter（skill_id、status、weight、when_to_use）+ Markdown 正文 |
| 消费方 | runtime agent prompt 注入（`skill_loader.py`）、semantic memory |
| 生成器 | `skill_generation/skill_md.py` + `skill_extractor.py` |

### `prompt_proposals.json`

| 字段 | 说明 |
|------|------|
| 生成时机 | PostGame prompt 提案步骤 |
| 内容 | suggested_patch 列表（section、action、text_zh）、apply_policy |
| 消费方 | 人工审核（当前为 json_only_no_runtime_replace，不自动回写） |
| 生成器 | `post_game/prompt_proposal.py` |

---

## 四、Coach 产物

### `coach_summary.json`

| 字段 | 说明 |
|------|------|
| 生成时机 | PostGame coach 步骤 |
| 内容 | coach_summary_v1 汇总：skill_snapshot、skill_diff、enrichment 数据 |
| 消费方 | 版本链追踪、前后对比 |
| 生成器 | `post_game/coach/coach.py` |

### `skill_snapshot.json`

| 字段 | 说明 |
|------|------|
| 生成时机 | coach 步骤中构建 |
| 内容 | skill_snapshot_v1：当前 run 的 skill 快照（skill_id → description、weight、status） |
| 消费方 | 下一版 run 的 skill_diff 对比、experiment_meta 的 previous_skill_snapshot_path |
| 生成器 | `post_game/coach/coach.py` |

### `skill_diff.json`

| 字段 | 说明 |
|------|------|
| 生成时机 | coach 步骤中构建 |
| 内容 | skill_diff_v1：与上一版快照的对比（added、removed、changed 列表） |
| 消费方 | 版本链分析、进化报告 |
| 生成器 | `post_game/coach/coach.py` |

---

## 五、Leaderboard 产物

### `leaderboard_entry.json`

| 字段 | 说明 |
|------|------|
| 生成时机 | PostGame 完成后由 entry_builder 构建（或 backfill 脚本补生成） |
| 内容 | leaderboard_entry_v1：version_id、model、prompt_version、skill_version、win_rate、avg_mvp_score、avg_benefit_score 等 |
| 消费方 | leaderboard 聚合、A/B 对比、版本链分析 |
| 生成器 | `leaderboard/entry_builder.py` |

### `experiment_meta.json`

| 字段 | 说明 |
|------|------|
| 生成时机 | 与 leaderboard_entry 一起生成 |
| 内容 | experiment_meta_v1：version_id、model、prompt_version、skill_version、previous_run_dir、previous_skill_snapshot_path |
| 消费方 | coach 的 skill_diff（找上一版快照）、版本链构建、A/B 对比 |
| 生成器 | `leaderboard/entry_builder.py` |

---

## 六、可视化产物

### `views/`

| 文件 | 说明 |
|------|------|
| `god_timeline.md` | 上帝视角全事件时间线 |
| `player_<id>_timeline.md` | 单玩家视角事件时间线 |
| `role_<role>_timeline.md` | 单角色视角事件时间线 |
| `public_digest.md` | 公开事件摘要 |
| `swing_digest.json` | 投票摆动摘要 |

| 字段 | 说明 |
|------|------|
| 生成时机 | PostGame 视图生成步骤 |
| 消费方 | 前端回放页、人工复盘 |
| 生成器 | `log_views/builder.py` |

---

## 产物生命周期（谁生成 → 谁消费）

```
对局引擎
  │
  ├──→ events.jsonl ──→ PostGame 流水线
  │                         │
  │                         ├──→ camp_persuasion_summary.json
  │                         ├──→ benefit_scores.json
  │                         ├──→ intention_scores.json
  │                         ├──→ role_skills.json ──→ skills/*.md ──→ agent_team/skills/<role>/<version>/
  │                         ├──→ prompt_proposals.json ──→ (人工审核)
  │                         ├──→ post_game_analysis.json
  │                         ├──→ coach_summary.json
  │                         │      ├── skill_snapshot.json ──→ 下一版 diff
  │                         │      └── skill_diff.json
  │                         └──→ views/
  │
  └──→ leaderboard_entry.json ──→ leaderboard 聚合
         experiment_meta.json ──→ 版本链 / A-B 对比
```

---

## 当前还缺什么

| 缺口 | 说明 |
|------|------|
| 自动回写 | prompt_proposals 只写 JSON，不回写 prompt YAML |
| 版本回滚 | experiment_meta 只记录 previous，没有 rollback 命令 |
| 趋势追踪 | leaderboard 只有单次排名，没有跨版本胜率趋势图 |
| 统计显著性 | A/B 对比只有阈值判断，没有 p-value |
