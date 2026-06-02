# Agent Skill 卡片库

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

每次库更新（PostGame 写入或人工审核同步）会为该身份 **递增 skill_version 文件夹**，再写入新 MD；旧版本保留供回放与 A/B。

## 文件格式

每个 `.md` 含 YAML frontmatter + 正文：

```markdown
---
skill_id: wolf_r1_player_2_1
prompt_role_key: wolf
status: active
source_run: runs/doubao-9p-xxx
---

# 第1轮阵营正向说服

## 何时使用
...
```

- `status: draft` — PostGame 自动写入（本地库，默认**不**加载进 Prompt）
- `status: active` — 人工/参考集审核后可复用（`reference_skills.sync_agent_skill_library` 写入）
- `status: skipped` — 不会写入 MD 文件

## 运行时加载

`agent_team/skill_support/skill_loader.py` 在构建系统 Prompt 时读取 `skills/<role>/<skill_version>/`，按 `weight` 降序注入最多 5 张 **active** Skill 全文（「对局经验 Skill 卡片」段落）。

默认加载各身份目录下**最新** `skill_version` 文件夹；进化/评测 manifest 可 pin 指定版本。默认不加载 `draft`。

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

1. 写出 `runs/<id>/role_skills.json`（索引）
2. 写出 `runs/<id>/skills/*.md`（本局归档）
3. **自动双写** 通过质量门控且 `source_run` 可信的 Skill 到 `agent_team/skills/<role>/<next_version>/`（`status: draft`，供审核；pytest/tmp 路径会被拒绝）

## 记忆系统分工

- **Skill 库（本目录）**：开局全量注入 sys_prompt（active 卡片全文）
- **SemanticMemory（InMemory 后端）**：本局提炼的 ephemeral 经验 → `[经验]` 注入 WorkingMemory（与 Skill 库不重复）

改 Prompt 策略卡走 `strategy/prompts/roles/<role>/<prompt_version>/role.yaml` + `prompts/shared/agent_base.md`；Skill 是 **行为模式补充**，不覆盖角色策略正文。
