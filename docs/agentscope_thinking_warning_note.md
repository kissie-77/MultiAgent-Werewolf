# AgentScope thinking warning note

日期：2026-05-25

## 现象

运行 DeepSeek / AgentScope 对局并打开原始 Agent 输出时，例如：

```powershell
uv run python -m llm_werewolf.interface.cli --config configs/llm-12p-deepseek.yaml --show_agent_raw=True
```

终端中会同时出现两类内容：

```text
Player1(thinking): ...
Player1: {"seat": 0, "reason": "..."}
```

以及反复出现的 AgentScope 内部 warning：

```text
WARNING | _openai_formatter:_format:350 - Unsupported block type thinking in the message, skipped.
```

## 原因

这是两层输出，不是同一个问题：

- `PlayerX(thinking): ...` 是 AgentScope 原始控制台输出。打开 `--show_agent_raw=True` 后，它会显示每个 Agent 的 thinking、动作选择和发言内容。
- `Unsupported block type thinking ... skipped` 是 AgentScope 的 `_openai_formatter` 日志。DeepSeek 返回的消息里包含 `thinking` block；后续请求复用历史消息时，AgentScope 尝试把消息格式化成 OpenAI Chat 格式，但 OpenAI Chat 格式不支持 `thinking` block，因此记录 warning 并跳过该 block。

所以这个 warning 不表示游戏失败，也不表示 thinking 没显示。截图中如果已经能看到 `PlayerX(thinking): ...`，说明原始思考内容已经被输出。

## 当前影响

- 对局可以继续运行。
- Agent 原始输出仍然可见。
- warning 会污染终端观测体验，尤其是在 LLM 间对战和人机后台观察时刷屏。

## 后续建议

保留 `--show_agent_raw=True` 的原始 Agent 输出，同时增加一个日志过滤：

- 只屏蔽 `_openai_formatter` 中 `Unsupported block type thinking in the message, skipped.` 这一类 warning。
- 不关闭 AgentScope console output。
- 不屏蔽 `PlayerX(thinking): ...`、`PlayerX: [[5]]`、结构化 JSON 动作、公开发言等原始数据。

预期效果：

```text
Player1(thinking): ...
Player1: {"seat": 0, "reason": "..."}
```

不再反复刷：

```text
WARNING | _openai_formatter:_format:350 - Unsupported block type thinking in the message, skipped.
```
