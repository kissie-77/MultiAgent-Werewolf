# 本地专用：Agent 串行调用（勿 push）

> **约定**：以下改动仅用于本地压测 / 避免网关 429，**不要提交到远程仓库**。

## 涉及文件

| 文件 | 说明 |
|------|------|
| `src/llm_werewolf/adapter/serial_calls.py` | **整文件** 本地专用，已加入 `.gitignore` |
| `src/llm_werewolf/adapter/agent.py` | 仅 **串行/限流** 相关：`run_serial_agent_call`、`_call_agentscope_agent` 重试、`_extract_agentscope_text` |
| `.env.example` | `AGENT_SERIAL_DELAY_SECONDS` 一行（可选不提交） |
| `src/llm_werewolf/core/engine/night_phase.py` | 注释「concurrently → sequentially」 |
| `src/llm_werewolf/core/engine/voting_phase.py` | 同上 |
| `src/llm_werewolf/core/engine/sheriff_election.py` | 同上 |

**可正常 push 的**（与串行无关）：AgentScope 接入（`factory.py`、`setup.py`、`cli.py`、`core/agent.py` 的 `create_agent` 等）、`configs/llm-*-agentscope.yaml`、`pyproject.toml` 的 `agentscope` 依赖等。

## Push 前检查

```bash
# 1. 确认 serial_calls 未被跟踪
git check-ignore -v src/llm_werewolf/adapter/serial_calls.py

# 2. 若曾 git add 过，从暂存区移除
git restore --staged src/llm_werewolf/adapter/serial_calls.py 2>/dev/null || true

# 3. agent.py 若与 AgentScope 一起改，用交互式暂存，跳过串行 hunk
git add -p src/llm_werewolf/adapter/agent.py

# 4. 可选：不提交引擎注释与 .env.example 串行配置
git restore --staged .env.example src/llm_werewolf/core/engine/night_phase.py \
  src/llm_werewolf/core/engine/voting_phase.py \
  src/llm_werewolf/core/engine/sheriff_election.py 2>/dev/null || true
```

## 本地标记（可选）

```bash
./scripts/mark-serial-local-only.sh   # skip-worktree 注释类文件
./scripts/unmark-serial-local-only.sh   # 取消标记
```

## 环境变量（仅本地 .env）

```bash
AGENT_SERIAL_DELAY_SECONDS=1.0
```

---

*记录日期：2026-05-20*
