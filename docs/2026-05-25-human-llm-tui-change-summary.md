# 2026-05-25 人机/LLM 对局与 TUI 改动记录

本文记录本轮围绕「人与 LLM 对战」「纯 LLM 对战」「开局配置」「TUI 交互」做的主要改动、运行方式和后续注意事项。文档中只写环境变量名，不记录任何真实 API Key。

## 背景问题

此前项目虽然有 `HumanAgent`，但人类玩家链路不完整：

- CLI 里部分阶段可以 `input()`，但技能、投票、发言缺少稳定的数字/文字交互约束。
- AgentScope 迁移后，公共圆桌发言阶段曾按 `agentscope_agent` 过滤参与者，导致没有 AgentScope backend 的真人玩家被跳过。
- 输入解析失败时存在随机兜底，用户体感像系统替真人玩家操作。
- TUI 只能展示游戏进程，没有真正可用的真人输入控件。
- 开局人数、是否启用警徽流、是否显示 Agent 原始输出都需要更直接的入口。

本轮目标是让人机对战和纯 LLM 对战都能稳定运行，并让 CLI/TUI 都具备可操作的开局与真人输入体验。

## 主要改动

### 1. 人数配置改为模板化 roster

新增/调整了 `player_roster` 配置模式，用一个模板生成多个 LLM 玩家，避免在 YAML 中重复写 12 个几乎一样的玩家配置。

相关位置：

- `src/llm_werewolf/game_runtime/config/player_config.py`
- `src/llm_werewolf/interface/player_roster.py`
- `src/llm_werewolf/interface/bootstrap.py`
- `configs/example.yaml`
- `configs/llm-12p-deepseek.yaml`
- `configs/human-mixed-deepseek.yaml`

效果：

- `--num_players` 可以在启动时覆盖对局人数。
- `human_mixed` 会保留一个真人玩家，其余玩家按模板生成。
- 旧式固定 `players:` 配置仍可用，但不支持优雅的人数覆盖。

### 2. CLI 支持开局人数、警徽流和原始输出

CLI 新增启动参数：

- `--num_players`
- `--enable_sheriff`
- `--show_agent_raw`

相关位置：

- `src/llm_werewolf/interface/cli.py`
- `src/llm_werewolf/interface/bootstrap.py`
- `src/llm_werewolf/interface/modes.py`

效果：

- 纯 LLM 对局和人机对局都可以在命令行开局前决定人数。
- 可以显式开启/关闭警徽流。
- 后台运行时可以显示 Agent 动作、发言、思考等原始数据。

### 3. 真人输入改为数字选择 + 纯文字发言

人类玩家交互目标：

- 技能选择：输入数字。
- 技能目标：输入数字。
- 投票目标：输入数字。
- 发言内容：输入纯文字。

相关位置：

- `src/llm_werewolf/interface/human_input.py`
- `src/llm_werewolf/game_runtime/phase_interaction.py`
- `src/llm_werewolf/agent_team/information_hub.py`

效果：

- 真人玩家不会在公共发言阶段因为没有 `agentscope_agent` 被跳过。
- 技能/投票输入有校验和重试提示。
- 发言接受普通文本，不要求 JSON 或特殊格式。

### 4. TUI 默认进入设置页

TUI 不再一启动就直接进入游戏，而是默认进入设置页。命令行参数只作为默认值填入设置项，不绕过用户确认。

相关位置：

- `src/llm_werewolf/interface/tui.py`
- `src/llm_werewolf/interface/tui_runtime.py`
- `src/llm_werewolf/ui/tui_app.py`

设置页支持：

- 对局模式：纯 LLM / 人机混合。
- 对局人数。
- 是否启用警徽流。
- 是否显示 Agent 原始输出。

### 5. TUI 增加真人输入栏

TUI 游戏页底部新增真人输入区。人机对战时，人类玩家不再回到 shell 输入，而是在 TUI 底部输入框操作。

相关位置：

- `src/llm_werewolf/ui/tui_app.py`
- `src/llm_werewolf/ui/tui_human_input.py`

输入方式：

- 数字模式：用于技能、目标、投票、是否确认。
- 文本模式：用于白天发言。

后续又针对女巫阶段做了 UI 修正：

- 之前底部提示栏太矮，女巫选项可能被上下文挤出可见区域。
- 现在关键选项会放在第一行，例如：`女巫行动：1=使用解药，2=使用毒药，3=不行动`。
- 目标选择也会第一行显示可输入编号，例如：`输入目标编号：2=Bot2, 3=Bot3`。

### 6. TUI 事件显示按真人视角过滤

TUI 人机模式会识别唯一真人玩家，并用该玩家的 `viewer_id` 过滤聊天/事件展示，避免真人看到不该看到的私有事件。

相关位置：

- `src/llm_werewolf/ui/tui_app.py`
- `src/llm_werewolf/ui/components/chat_panel.py`

纯 LLM 模式仍作为观战模式展示。

### 7. Agent 原始输出与 thinking warning 记录

运行中出现过类似警告：

```text
Unsupported block type thinking in the message, skipped.
```

该问题已单独记录在：

- `docs/agentscope_thinking_warning_note.md`

结论摘要：

- 这是上游/模型返回 `thinking` block，但当前 OpenAI formatter 不支持该 block 类型导致的 warning。
- 它不等于游戏必然中断。
- `--show_agent_raw=True` 仍用于显示 Agent 原始动作和发言，方便后台观察。

### 8. README 运行说明已更新

README 已补充：

- DeepSeek API Key 环境变量设置。
- 纯 LLM 对局运行方式。
- 人机对局运行方式。
- 人数和警徽流参数。
- TUI 默认设置页说明。
- TUI 真人输入栏说明。

相关位置：

- `README.md`

## 当前运行方式

### DeepSeek 纯 LLM 对局

```powershell
$env:DEEPSEEK_API_KEY="你的 DeepSeek API Key"
uv run python -m llm_werewolf.interface.cli --participation=all_agent --rules=badge_flow --num_players=12 --enable_sheriff=True --show_agent_raw=True
```

### DeepSeek 人机对战

```powershell
$env:DEEPSEEK_API_KEY="你的 DeepSeek API Key"
uv run python -m llm_werewolf.interface.cli --participation=human_mixed --rules=badge_flow --num_players=9 --enable_sheriff=True --show_agent_raw=True
```

### TUI 人机对战

```powershell
$env:DEEPSEEK_API_KEY="你的 DeepSeek API Key"
uv run python -m llm_werewolf.interface.tui --participation=human_mixed --num_players=9 --enable_sheriff=True --show_agent_raw=True
```

启动后会先进入设置页。确认设置后进入游戏；真人玩家在底部输入栏操作。

### 豆包 / 火山方舟配置

项目中已有豆包配置：

- `configs/llm-6p-doubao.yaml`
- `configs/llm-9p-doubao.yaml`

使用方式：

```powershell
$env:ARK_API_KEY="你的火山方舟 API Key"
uv run python -m llm_werewolf.interface.cli --config configs/llm-6p-doubao.yaml
```

或：

```powershell
$env:ARK_API_KEY="你的火山方舟 API Key"
uv run python -m llm_werewolf.interface.cli --config configs/llm-9p-doubao.yaml
```

注意：这两个豆包配置目前仍是旧式固定 `players:` 写法，不适合搭配 `--num_players` 动态改人数。若要让豆包也支持自由人数，建议后续迁移为 `player_roster` 模板配置。

## 测试与验证

本轮关键验证命令：

```powershell
uv run pytest --no-cov
```

最后一次全量结果：

```text
338 passed
```

生产代码 scoped ruff 检查：

```powershell
uv run ruff check src\llm_werewolf\ui\tui_human_input.py src\llm_werewolf\ui\tui_app.py
```

结果：通过。

Diff 空白检查：

```powershell
git diff --check
```

结果：通过，仅出现 Windows 下 Git 的 LF/CRLF 提示。

## 新增/重点测试

新增或扩展的测试覆盖：

- `tests/interface/test_player_roster.py`
- `tests/interface/test_tui_runtime.py`
- `tests/ui/test_tui_human_input.py`
- `tests/ui/test_tui_app_setup.py`
- `tests/interface/test_cli_human_mode.py`
- `tests/interface/test_bootstrap.py`

重点覆盖点：

- roster 模板能生成指定人数。
- 人机模式只保留一个真人玩家。
- 警徽流参数能覆盖配置。
- TUI 默认进入设置页。
- TUI 会把命令行参数作为设置页默认值。
- TUI 人机模式注入 `TextualHumanInputProvider`。
- TUI 事件展示使用真人 viewer 过滤。
- 女巫行动提示第一行展示可输入选项。
- 目标选择提示第一行展示可输入编号。

## 已知注意事项

1. 不要把真实 API Key 写入配置文件或文档。统一使用环境变量。
2. DeepSeek 配置使用 `DEEPSEEK_API_KEY`。
3. 豆包/火山方舟配置使用 `ARK_API_KEY`。
4. 旧式固定 `players:` 配置可以运行，但不支持优雅的 `--num_players` 动态人数。
5. TUI 目前已具备设置页和真人输入栏，但复杂终端尺寸下仍建议继续做真实视觉回归。
6. `thinking` block warning 已记录，不应和人类玩家链路问题混为一谈。

## 后续建议

1. 将豆包配置迁移为 `player_roster`，让豆包也支持自由人数。
2. 给 TUI 增加更完整的键盘快捷键和状态提示。
3. 针对 6/9/12 人不同人数补充一组实际 LLM smoke run 记录。
4. 对 Agent 原始输出增加可折叠/可过滤视图，避免 TUI 聊天区被长 thinking 内容淹没。
