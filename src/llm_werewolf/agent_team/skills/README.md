# Agent Skill 卡片库

> **最后更新**：2026-05-23

PostGame 评测从对局中提取的 **Skill** 以 Markdown 存放于此，按 **prompt_role_key / skill_version** 分目录。

## 目录结构

```text
skills/
  wolf/
    v1/           # 初始版本
    v2/           # 库写入 bump 后新版本
  prophet/
    v1/
  villager/
    v1/
  ...
```

**稀疏 bump**：仅当本局该身份出现**全新** Skill（使用场景与库内已有 card 不匹配）时，才 `vN → vN+1` 并 copy 旧版；若只是合并进已有 card，则在**当前版本目录原地更新**，不 bump。旧版本目录保留供回放与 A/B。

## 文件格式

每个 `.md` 含 YAML frontmatter + 正文：

```markdown
---
skill_id: wolf_r1_player_2_1
prompt_role_key: wolf
status: active
source_run: runs/doubao-9p-xxx
belief_pattern: concentrated
belief_signals: vote_intention_set,b1_top_above_0_7
---

# 第1轮阵营正向说服

## 何时使用
...
```

- `status: draft` — PostGame 自动写入（本地库，默认**不**加载进 Prompt）
- `status: active` — 人工/参考集审核后可复用（`reference_skills.sync_agent_skill_library` 写入）
- `status: skipped` — 不会写入 MD 文件
- `belief_pattern` — 生成时刻 B1/B2 分布模式（`concentrated` / `dispersed` / `mixed` / …），无 `belief_signals` 时用于 fallback 匹配
- `belief_signals` — PostGame 从 `beliefs.jsonl` **自动生成**的触发信号 ID（逗号分隔），运行时按子集匹配注入

## 运行时加载与注入

`agent_team/skill_support/skill_loader.py` 读取 `skills/<role>/<skill_version>/` 下 **active** Skill（默认不加载 `draft`）。

Skill **不在开局灌入 system prompt 全文**，而是每次发言/决策前按当前信念矩阵匹配后注入 decision context：

1. **匹配时机**：`InformationHub` 在 `run_roundtable` / `collect_speech` 中，对当前发言人先 `refresh_player_belief_skills()`，再组装 decision context。
2. **匹配规则**（`select_skills_for_belief`）：
   - 若 frontmatter 有 `belief_signals`：Skill 所需信号必须是当前活跃信号的**子集**（PostGame 自动生成，少人工标注）。
   - 否则 fallback：比较 `belief_pattern` 与当前分布模式，并结合正文/when_to_use 关键词。
3. **注入块**：`RuntimeMemoryManager.get_context_for_decision()` 追加 `【信念匹配的对局经验 · 仅供参考】`（含触发信号、模式摘要、公开行为/避免）。
4. **配置**：`MemoryConfig.skill_belief_top_k`（默认 3）、`skill_belief_pool_size`（默认 12）。

默认加载各身份目录下**最新** `skill_version` 文件夹；进化/评测 manifest 可 pin 指定版本。

## 信念信号 ID（自动生成）

PostGame 写 MD 时由 `skill_card_builder` / `belief_format.detect_belief_signals_from_snapshot` 从对应 `beliefs.jsonl` 快照推导，写入 `belief_signals` 与正文「触发信号」说明。

| 信号 ID | 含义 |
|---------|------|
| `b1_target_certain` | 存在目标狼信 = 1.0 |
| `b1_two_above_0_8` | 至少两个目标狼信 > 0.8 |
| `b1_multi_above_0_5` | 至少两个目标狼信 > 0.5 |
| `b1_top_above_0_7` | 最高目标狼信 ≥ 0.7 |
| `b1_self_wolf_certain` | 自问狼信 = 1.0 |
| `b2_observer_certain_on_me` | 存在他人对你判狼 = 1.0 |
| `b2_multi_above_0_5_on_me` | 不止一人对你狼信 > 0.5 |
| `b2_top_above_0_8_on_me` | 最高他人疑狼 > 0.8 |
| `vote_intention_set` | 投票意向已锁定到单一座位 |
| `vote_watching` | 意向观望且狼信未收敛 |

## 参考 Skill 同步（联调 / API 不可用时）

```bash
.venv/bin/python -c "
from llm_werewolf.evaluation.post_game.skill_generation.reference_skills import sync_agent_skill_library
sync_agent_skill_library()  # 默认用 runs/ 下最佳本地对局
"
```

会从 `events.jsonl` 提取真实夜间决策，并补全狼队协商、白天归票等策略卡片；同步前会**删除**该身份当前版本目录下旧的重复 MD，写入 `status: active`。

## 生成来源

对局结束后 `evaluation/post_game/skill_extractor.py` 会：

1. 写出 `runs/<id>/role_skills.json`（索引，含 `library_action` / `merge_policy`）
2. 写出 `runs/<id>/skills/*.md`（本局候选归档，无论是否合并进库）
3. **写共享库**（`write_agent_library=True`，默认开启）：通过质量门控且 `source_run` 可信的 Skill 进入 `agent_team/skills/<role>/<version>/`

### 合并 vs 新建（2026-06-04）

写库前按 **`when_to_use` 使用场景** 与当前版本目录内已有 MD 比对（`SequenceMatcher`，阈值 **0.78**，与 `SemanticMemory.find_similar_card` 一致）：

| 结果 | 共享库行为 | 版本 |
|------|------------|------|
| 场景一致 | **不新建** skill 文件；合并正文（公开行为 / 避免 / 提取依据），**weight += 0.15**，`use_count += 1` | 不 bump，原地更新 |
| 场景不一致 | 新建 `{skill_id}.md` | bump 到 `vN+1`（copy 旧版后追加） |
| 同局既有合并又有新建 | 合并与新建均落在**同一** `vN+1` | 只 bump 一次 |

`role_skills.json` 字段：

- `apply_policy`: `merge_when_to_use_then_sparse_bump`
- `merge_policy`: `{ match_field, similarity_threshold: 0.78, weight_delta_on_merge: 0.15 }`
- 每条 skill：`library_action` = `merged` | `created`；合并时另有 `merged_into_skill_id`

pytest / tmp / `artifacts/runs/` 等不可信 `source_run` 不会写共享库。

## 记忆系统分工

- **Skill 库（本目录）**：按信念矩阵动态匹配，注入 decision context（发言前 refresh）
- **SemanticMemory（InMemory 后端）**：本局提炼的 ephemeral 经验 → `[经验]` 注入 WorkingMemory（与 Skill 库不重复）

改 Prompt 策略卡走 `strategy/prompts/roles/<role>/<prompt_version>/role.yaml` + `prompts/shared/agent_base.md`；Skill 是 **行为模式补充**，不覆盖角色策略正文。

## 验证

- 单元/集成：`tests/agent_team/test_skill_markdown.py`（含真实对局 `12p-doubao-20260531-203127` 回匹配测试）
- 报告：`docs/agent_team/memory/DESIGN.md` §6.1
