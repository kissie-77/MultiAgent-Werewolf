# change-logger

一个项目本地的 Claude Code skill，做两件事：

1. **自动记录每次代码修改** —— 通过 PostToolUse hook，每次 `Edit` / `Write` / `MultiEdit` 都往 `docs/changes/<任务名>.md` 追加一行（时间、文件、行号范围、工具）。
2. **生成 handoff.md** —— 一键导出当前任务的目标、进度、变更文件清单、git 状态、blocker、下一步，让下一个 AI（Codex / Claude Code / 别人）能在几分钟内接手。

**作用域**：仅本项目（`MultiAgent-Werewolf-kissie77-20260524`）。装在 `.claude/skills/`，不会影响别的项目。

---

## 设计原则

| 信息类型 | 谁负责 | 为什么 |
|----------|--------|--------|
| 机械信息（时间 / 文件 / 行号 / 工具） | **Hook**（确定性脚本） | 不会忘、零成本，AI 不需要思考 |
| 语义信息（修改原因 / 任务目标 / 下一步） | **Claude**（通过 skill 指引） | 这些需要理解上下文，脚本推不出来 |

所以你会在 changes 文件里看到 `_PENDING_` 占位符 —— 那是 hook 占好的位置，等你（或 Claude）用一句话总结原因后填进去。

---

## 安装内容

```
.claude/
├── settings.local.json              # hook 配置
├── skills/change-logger/
│   ├── SKILL.md                     # Claude 看的 workflow 文档
│   ├── README.md                    # 本文件
│   ├── scripts/
│   │   ├── start_task.py            # 设置任务名
│   │   ├── log_change.py            # hook 入口
│   │   ├── add_reason.py            # 回填 _PENDING_
│   │   └── generate_handoff.py      # 生成 handoff 骨架
│   └── references/hook-setup.md     # hook schema 与重装说明
└── commands/                        # slash 命令包装
    ├── start-task.md
    ├── log-why.md
    └── handoff.md
```

**依赖**：Python 3.8+（用了标准库 `pathlib` / `argparse` / `json` / `subprocess`，没有第三方依赖）。

---

## 日常使用：三个 slash 命令

### 1. `/start-task <任务名>`

开始一段聚焦的工作时调。任务名随便写（中文也行），脚本会自动 slugify 成英文小写横杠形式。

```
你: /start-task 修复警长投票权重
脚本: created docs/changes/修复警长投票权重.md  (slug: 修复警长投票权重)
```

会做的事：
- 写入 `.claude/current-task`（hook 靠它判断该追加到哪个文件）
- 创建 `docs/changes/<slug>.md` 带表头
- 同名任务存在时附加一个 `## Session N` 块（不会覆盖历史）

### 2. `/log-why "<一句话原因>"`

做完一组逻辑相关的修改后调（**Claude 应该主动做，不需要你提醒**）。把表里末尾的连续 `_PENDING_` 行全部填上你给的原因。

```
你: /log-why "警长票按 1.5x 加权，对齐产品文档 v2.3"
脚本: filled 4 row(s) in docs/changes/修复警长投票权重.md
```

如果想只填指定数量、不全填，加 `--count`：

```bash
python .claude/skills/change-logger/scripts/add_reason.py "explorative refactor" --count 3
```

### 3. `/handoff`

要交接给下一个 AI 时调。先跑脚本生成骨架，然后 Claude 会自己读 `handoff.md` 把 5 个 `<!-- FILL: ... -->` 占位符填满：

- **TASK_GOAL** — 任务目标（一段）
- **PROGRESS** — 完成/未完成
- **KEY_LOCATIONS** — 3-7 个关键 `file:line`
- **BLOCKERS** — 卡在哪里
- **NEXT_STEPS** — 下一步有序列表

骨架里**已经填好的机械部分**：当前任务名、git 分支、变更文件清单（从 changes log 提取）、`git status`、最近 15 个 commit。

---

## 直接调脚本（不通过 slash 命令）

slash 命令只是 Python 脚本的薄包装，你也可以直接跑：

```bash
python .claude/skills/change-logger/scripts/start_task.py "<任务名>"
python .claude/skills/change-logger/scripts/add_reason.py "<原因>" [--count N] [--task <slug>]
python .claude/skills/change-logger/scripts/generate_handoff.py
```

---

## 输出格式

### `docs/changes/<slug>.md`

```markdown
# Changes: 修复警长投票权重

> Task name: 修复警长投票权重
> Started: 2026-05-24 18:23:00
> Tracked via `.claude/skills/change-logger`

## Session 1 — 2026-05-24 18:23:00

| Time     | Tool      | File                       | Lines      | Why                                    |
|----------|-----------|----------------------------|------------|----------------------------------------|
| 18:23:11 | Edit      | `src/core/sheriff.py`      | L120-L138  | 警长票 1.5x 权重，对齐 v2.3 文档        |
| 18:24:02 | Edit      | `tests/test_sheriff.py`    | L45-L70    | 警长票 1.5x 权重，对齐 v2.3 文档        |
| 18:25:55 | Write     | `docs/sheriff-weight.md`   | L1-L42     | _PENDING_                              |
```

### `handoff.md`（项目根目录）

骨架结构（生成时）：

```markdown
# Handoff — 修复警长投票权重

> Generated: 2026-05-24 19:01:33
> Branch: `main`
> Change log: docs/changes/修复警长投票权重.md

## Task goal & progress
<!-- FILL: TASK_GOAL ... -->
**Status:**
<!-- FILL: PROGRESS ... -->

## Files changed this task
- `src/core/sheriff.py`
- `tests/test_sheriff.py`
- `docs/sheriff-weight.md`

## Key code locations
<!-- FILL: KEY_LOCATIONS ... -->

## Git status        ← 自动填
## Recent commits    ← 自动填

## Blockers / known issues
<!-- FILL: BLOCKERS ... -->

## Next steps
<!-- FILL: NEXT_STEPS ... -->
```

`<!-- FILL: ... -->` 这些占位符必须由 Claude（或你）补完，handoff.md 才真正可用。

---

## Hook 工作原理

`.claude/settings.local.json` 配置：

```json
{
  "hooks": {
    "PostToolUse": [
      {
        "matcher": "Edit|Write|MultiEdit",
        "hooks": [
          { "type": "command", "command": "python .claude/skills/change-logger/scripts/log_change.py" }
        ]
      }
    ]
  }
}
```

Claude Code 每次完成 Edit/Write/MultiEdit 后，会把工具的 input JSON 通过 stdin 喂给 `log_change.py`，脚本：

1. 读 `.claude/current-task` 拿到 slug（没有就 fallback 到 `untracked`）
2. 跳过自己的目录（`.claude/`、`docs/changes/`、`handoff.md`）防止递归
3. 计算被修改的行号范围（在修改后的文件里找 `new_string`）
4. 追加一行到 `docs/changes/<slug>.md`，Why 列写 `_PENDING_`
5. 出错写 `.claude/change-logger.err`，但 exit 0（不卡 session）

⚠ **Hook 只在 Claude Code 启动时加载**。第一次装好后需要**重启一次** Claude Code 才生效。重启后才会自动追加。

---

## 常见问题

### 改了代码但 `docs/changes/` 里没东西

按下面顺序排查：

1. 当前 session 是 hook 配好**之后**启动的吗？没有的话重启 Claude Code。
2. `.claude/change-logger.err` 里有报错吗？
3. `python --version` 在你的 shell 里能跑通吗？如果你用的是 `py` / `python3` / venv 内的 python，把 `settings.local.json` 里的 `command` 改成对应的命令。
4. 改的是 `.claude/` 或 `docs/changes/` 下的文件吗？这些路径被有意排除了。

### 行号显示 `?`

`log_change.py` 找不到 `new_string` 在修改后的文件里的位置时会写 `?`。常见原因：
- Edit 的 `new_string` 是空字符串（纯删除）
- `new_string` 在文件里出现多次（罕见，Edit 工具本身就要求唯一）
- 文件不能被读（权限 / 编码问题）

不影响后续记录，只是这一行没精确行号。

### 想暂时关掉 hook

把 `.claude/settings.local.json` 里 `hooks` 块删掉，或整个文件改成 `{}`。skill 本身（3 个 slash 命令）继续可用。

### 跨任务忘了 `/start-task`

之前的修改会进 `docs/changes/untracked.md`。补一个 `/start-task <真实任务名>` 后，可以手动 `cp docs/changes/untracked.md docs/changes/<真实任务名>.md` 然后清空 untracked，或者就把它当历史噪声留着。

### 任务名想用英文

直接 `/start-task fix-sheriff-vote-weight`，slugify 后是 `fix-sheriff-vote-weight`。中文 / 英文随意，但文件名会跟 slug 一致 —— 用中文的话 git 在某些 Windows 终端里可能显示编码问题，介意的话推荐英文。

---

## 集成到 `CLAUDE.md`

如果项目根有 `CLAUDE.md`，建议加一行让下一个 AI 第一时间看到 handoff：

```markdown
## Handoff

If `handoff.md` exists in the project root, read it first — it contains the
previous AI session's notes on the current task. See
`.claude/skills/change-logger/` for the workflow.
```

---

## 怎么改进 / 卸载

**改进**：直接编辑 `scripts/*.py` 或 `SKILL.md`。改完最好跑个 smoke test：

```bash
python .claude/skills/change-logger/scripts/start_task.py "smoke"
echo '{"tool_name":"Write","tool_input":{"file_path":"README.md","content":"x\ny"},"cwd":"."}' \
  | python .claude/skills/change-logger/scripts/log_change.py
cat docs/changes/smoke.md
# 清理
rm docs/changes/smoke.md .claude/current-task
```

**卸载**：删 `.claude/skills/change-logger/`、`.claude/commands/{start-task,log-why,handoff}.md`、`.claude/settings.local.json` 里的 hooks 块。`docs/changes/` 和 `handoff.md` 是产物，看你要不要保留。
