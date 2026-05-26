# Agent Skill 卡片库

PostGame 评测从对局中提取的 **Skill** 以 Markdown 存放于此，按 **prompt_role_key** 分子目录。

## 目录结构

```text
skills/
  wolf/           # 狼人身份 Skill
  prophet/        # 预言家
  witch/
  villager/
  guard/
  hunter/
  wolf_king/
```

## 文件格式

每个 `.md` 含 YAML frontmatter + 正文：

```markdown
---
skill_id: wolf_r1_player_2_1
prompt_role_key: wolf
status: draft
source_run: runs/doubao-9p-xxx
---

# 第1轮阵营正向说服

## 何时使用
...
```

- `status: draft` — PostGame 自动写入，Agent 默认会加载参考
- `status: active` — 人工审核后可改，表示可长期复用
- `status: skipped` — 不会写入 MD 文件

## 生成来源

对局结束后 `evaluation/post_game/skill_extractor.py` 会：

1. 写出 `runs/<id>/role_skills.json`（索引）
2. 写出 `runs/<id>/skills/*.md`（本局归档）
3. **同步写入** `agent_team/skills/<role>/*.md`（供下局 Agent 加载）

## 运行时加载

`agent_team/skill_loader.py` 在构建系统 Prompt 时读取对应身份目录，追加「对局经验 Skill 卡片」段落。

改 Prompt 策略卡仍走 `strategy/prompts/v2/`；Skill 是 **行为模式补充**，不覆盖角色策略正文。
