# DeepSeek 实跑观察记录（2026-05-25）

## 运行信息

- **运行配置**：`configs/llm-12p-deepseek.yaml`
- **模型配置**：DeepSeek OpenAI-compatible API，`deepseek-v4-flash`
- **日志文件**：
  - `runs/codex-deepseek-observe-20260525-114128/stdout.log`
  - `runs/codex-deepseek-observe-20260525-114128/stderr.log`
- **进程状态**：观察结束后已停止 `llm_werewolf` 游戏进程，避免继续消耗 API。

## 观察到的问题

### 1. Windows GBK 控制台启动崩溃

直接运行 12 人 DeepSeek 配置时，`ConsolePresenter` 打印游戏开始横幅中的 emoji，触发：

```text
UnicodeEncodeError: 'gbk' codec can't encode character
```

临时使用以下环境后可继续运行：

```powershell
chcp 65001
$env:PYTHONUTF8='1'
$env:PYTHONIOENCODING='utf-8'
```

### 2. shell/stdout 泄露模型私有思考

stdout 会打印模型的 `thinking` / private 内容，例如：

- 狼王发言前暴露“我是狼王，队友是 7、10、12”。
- 预言家暴露查验思路。
- 女巫暴露夜间用药推理。

这对真人参与、观战 UI、公开复盘日志都不安全。默认输出应只展示公开发言与公开事件，private/thinking 内容应进入受控 debug 日志。

### 3. 可见文本、结构化决策与最终结算不一致

本次实跑中出现多处不一致：

- Player11 守卫文本输出 `[[11]]`，且 thinking 表示“首夜自守”，但夜晚结果显示“守卫保护了 Player4”。
- Player4 女巫输出 `{"action": "save", ...}` 表示救 8 号，但结算仍显示 `Player8 被狼人杀害`。
- Player6 预言家输出 `{"seat":7,...}`，但夜晚结果显示“预言家查验了 Player8”。

这说明 stdout 中可见回复、AgentScope structured metadata、fallback 解析和最终 `Action` 结算之间可能不是同一份决策。

### 4. AgentScope formatter 持续警告

stderr 持续出现：

```text
Unsupported block type thinking in the message, skipped.
```

说明 DeepSeek 返回的 thinking block 被 OpenAI formatter 跳过，可能造成对话记忆缺块，也可能与结构化决策不一致相关。

## 建议排查顺序

1. 给每次 `request_*` 记录同一个 correlation id，串起 raw text、metadata、解析后的 decision、最终 action target。
2. 沿 `AgentScopeWerewolfAgent.get_structured_response()` → `structured_invoke.invoke_structured()` → `WerewolfAdapterBridge.request_*()` → `ActionProcessorMixin.process_actions()` 追踪一次完整夜间技能决策。
3. 在 `ConsolePresenter` 或 Agent 调用层区分 `public_speech` 与 `private_thought`，默认不要把 private/thinking 写入普通 stdout。
4. 为 DeepSeek structured output 增加最小回归用例：
   - 守卫选 11 必须结算保护 11。
   - 女巫 save 刀口必须阻止该目标死亡。
   - 预言家 `seat=7` 必须记录查验 7。
5. Windows CLI 输出统一设置 UTF-8，或移除/降级 emoji 横幅，避免首屏崩溃。

## 关联文件

- `src/llm_werewolf/agent_team/agentscope_agent.py`
- `src/llm_werewolf/agent_team/structured_invoke.py`
- `src/llm_werewolf/agent_team/bridge.py`
- `src/llm_werewolf/game_runtime/engine/action_processor.py`
- `src/llm_werewolf/ui/console_presenter.py`

## 状态

待处理。当前仅记录实跑问题，尚未修改运行时代码。
