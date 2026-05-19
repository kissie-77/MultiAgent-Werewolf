# 项目文档系统 落地实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 按已批准的 spec 落地 MultiAgent-Werewolf 项目的轻量级文档体系（ADR / ROADMAP / WORKFLOW / ARCH / PR 模板 / CHANGELOG）。

**Architecture:** 纯 markdown 文件，不部署站点；文档分布在 `docs/`（开发者文档）、`.github/`（PR 模板）、仓库根（CHANGELOG）。CHANGELOG 由现有 `.github/cliff.toml` 配合 git-cliff 工具自动生成。

**Tech Stack:** Markdown · git-cliff（Conventional Commits → CHANGELOG）· 现有 `.github/cliff.toml`

**Spec 引用:** `docs/superpowers/specs/2026-05-18-project-docs-system-design.md`

---

## 文件清单

**新增：**
- `docs/adr/README.md` — ADR 索引 + 模板
- `docs/adr/0001-mixin-engine.md`
- `docs/adr/0002-protocols-over-abc.md`
- `docs/adr/0003-async-engine.md`
- `docs/roadmap.md`
- `docs/workflow.md`
- `docs/arch.md`
- `.github/PULL_REQUEST_TEMPLATE.md`
- `CHANGELOG.md`（git-cliff 生成）

**修改（末尾追加"约定"/"Conventions"小节）：**
- `README.md`
- `README.zh-CN.md`
- `README.zh-TW.md`

**保留不动：**
- `mkdocs.yml`、`scripts/gen_docs.py`（将来上站点时再用）
- `.github/cliff.toml`（已配置好，本次激活）
- `.github/ISSUE_TEMPLATE/*`、其他 `.github/*` 文件
- `rule.md`

---

## Task 1: 创建 docs/adr/ 目录与索引模板

**Files:**
- Create: `docs/adr/README.md`

- [ ] **Step 1: 创建 docs/adr/README.md**

写入以下内容（注意：模板示例用 4-backtick 外层 fence 包住 3-backtick 内层 fence）：

````markdown
# Architecture Decisions

记录"我们当时为什么这么做"。新 ADR 复制下面这个模板。

---

## 模板

```markdown
# ADR-NNNN: <标题>

**日期**: YYYY-MM-DD · **状态**: accepted

## 问题
<1-2 句>

## 决定
<1-2 句>

## 取舍
<付了什么代价 / 放弃了什么备选>
```

控制在 100 字以内，5 分钟写完。

---

## Index

| # | 标题 | 状态 |
|---|---|---|
| [0001](0001-mixin-engine.md) | 引擎用 Mixin 组合而非单类 | accepted |
| [0002](0002-protocols-over-abc.md) | 用 Protocol 而非 ABC 描述接口 | accepted |
| [0003](0003-async-engine.md) | 引擎全异步化 | accepted |
````

- [ ] **Step 2: 验证文件存在**

Run: `ls docs/adr/README.md`
Expected: 文件存在，路径正确

- [ ] **Step 3: Commit**

```bash
git add docs/adr/README.md
git commit -m "docs(adr): bootstrap ADR index and template"
```

---

## Task 2: 写 ADR-0001（Mixin engine）

**Files:**
- Create: `docs/adr/0001-mixin-engine.md`

- [ ] **Step 1: 创建 ADR-0001**

写入：

```markdown
# ADR-0001: 引擎用 Mixin 组合而非单类

**日期**: 2026-05-18 · **状态**: accepted

## 问题
GameEngine 要管夜晚/警长/白天/投票/死亡/动作分发 6 个阶段
+ 事件日志、胜负判定等多个职责。塞一个类会让单文件膨胀到难维护。

## 决定
按阶段拆 7 个 Mixin（NightPhase/SheriffElection/DayPhase/Voting/DeathHandler
/ActionProcessor/Base），`GameEngine` 主类只做多重继承组装、不写代码。

## 取舍
- 付：Mixin 之间隐式共享 `game_state` 等属性，每个 Mixin 顶部需要写类型注解
  声明（不写会被 lint 报）。
- 弃：State Pattern 那种更"标准"的写法；理由是会引入额外抽象层，初学者难读。
```

- [ ] **Step 2: 验证内容**

Run: `head -5 docs/adr/0001-mixin-engine.md`
Expected: 看到 ADR 标题与日期/状态行

- [ ] **Step 3: Commit**

```bash
git add docs/adr/0001-mixin-engine.md
git commit -m "docs(adr): record Mixin engine decision (ADR-0001)"
```

---

## Task 3: 写 ADR-0002（Protocols over ABC）

**Files:**
- Create: `docs/adr/0002-protocols-over-abc.md`

- [ ] **Step 1: 创建 ADR-0002**

写入：

```markdown
# ADR-0002: 用 Protocol 而非 ABC 描述接口

**日期**: 2026-05-18 · **状态**: accepted

## 问题
Player / Role / Action / GameState 互相引用，ABC 写法会形成循环 import。
另外要接入 AgentScope 等外部代理对象，强制继承很别扭。

## 决定
所有接口用 `typing.Protocol(runtime_checkable=True)`，集中在
`core/types/protocols.py`。第三方对象只要"长得像"就能用，不需要继承。

## 取舍
- 付：没有 `@abstractmethod` 的"忘写就崩"保护，只能靠类型检查器（ty/mypy）发现。
- 弃：ABC 体系下的隐式签名校验。
```

- [ ] **Step 2: 验证内容**

Run: `head -5 docs/adr/0002-protocols-over-abc.md`
Expected: 看到 ADR 标题与日期/状态行

- [ ] **Step 3: Commit**

```bash
git add docs/adr/0002-protocols-over-abc.md
git commit -m "docs(adr): record Protocols-over-ABC decision (ADR-0002)"
```

---

## Task 4: 写 ADR-0003（async engine）

**Files:**
- Create: `docs/adr/0003-async-engine.md`

- [ ] **Step 1: 创建 ADR-0003**

写入：

```markdown
# ADR-0003: 引擎全异步化

**日期**: 2026-05-18 · **状态**: accepted

## 问题
LLM 调用是 IO 密集型，每个角色独立请求。同步串行调用会让一局游戏跑几分钟到
几十分钟，调试和评测体验差。

## 决定
所有阶段方法用 `async/await`，LLMAgent 走 `AsyncOpenAI`。无 IO 的方法
（事件日志、状态读取）保持同步。

## 取舍
- 付：所有 Mixin 方法签名变 async；测试需要 `pytest-asyncio`；调试栈更长。
- 弃：完全同步实现的简单性。
- 仍未做：同一夜不同角色的 LLM 调用并发化（当前是 for 循环顺序 await，TODO）。
```

- [ ] **Step 2: 验证内容**

Run: `head -5 docs/adr/0003-async-engine.md`
Expected: 看到 ADR 标题与日期/状态行

- [ ] **Step 3: Commit**

```bash
git add docs/adr/0003-async-engine.md
git commit -m "docs(adr): record async engine decision (ADR-0003)"
```

---

## Task 5: 写 docs/roadmap.md

**Files:**
- Create: `docs/roadmap.md`

- [ ] **Step 1: 创建 roadmap.md**

写入：

```markdown
# Roadmap

## 当前迭代
- [x] 游戏引擎核心流程（异步化完成 → ADR-0003）
- [x] 多模型支持（OpenAI/Anthropic/DeepSeek/Ollama via AsyncOpenAI）
- [x] 20+ 角色系统
- [x] YAML 配置 + 自动按人数配角色
- [x] Demo 模式验证（DemoAgent 无 API 跑通）
- [ ] **修复 AlphaWolf super() chain bug**（阻塞 9 人以上 Demo）
- [ ] AgentScope 接入 → 待写 ADR
- [ ] 信息隔离层（ObservationBuilder 完整化）

## 下个迭代
- [ ] 结构化日志（JSON 事件流，供 Web 端订阅）
- [ ] Web 观战 UI（FastAPI + WebSocket）→ 待写 ADR
- [ ] 同一夜多角色 LLM 调用并发化（ADR-0003 留的 TODO）

## 想做但还没排期
- 评测与复盘体系（一局录像 + 复盘报告）
- 多策略对照实验（同模型不同 prompt）
- 模型胜率统计 dashboard
```

- [ ] **Step 2: 验证内容**

Run: `head -10 docs/roadmap.md`
Expected: 看到 "Roadmap" 标题、当前迭代条目

- [ ] **Step 3: Commit**

```bash
git add docs/roadmap.md
git commit -m "docs: add roadmap with current iteration status"
```

---

## Task 6: 写 docs/workflow.md（使用教程）

**Files:**
- Create: `docs/workflow.md`

- [ ] **Step 1: 创建 workflow.md**

写入（外层 4-backtick fence 包内层 3-backtick fence）：

`````markdown
# Workflow

这套文档系统怎么用——3 分钟读完。

## 三类常见动作

| 你在做什么 | 要做什么文档动作 |
|---|---|
| 写代码、修 bug | commit 规范 + PR 模板 |
| 做了一个跨多模块/接口的决定 | 加一篇 ADR |
| 完成一个阶段目标 | 划掉 `roadmap.md` 里的 checkbox |

## Commit 规范（Conventional Commits）

格式：`<type>(<scope>): <一句话>`

| 类型 | 用在哪 |
|---|---|
| `feat` | 新功能 |
| `fix` | bug 修复 |
| `refactor` | 重构（不改外部行为） |
| `docs` | 改文档 |
| `test` | 加/改测试 |
| `chore` | 杂活（依赖升级、配置） |
| `feat!` 或 `fix!` | **破坏性变更**（自动归到 CHANGELOG 顶层） |

例：
- `feat(engine): add sheriff badge transfer on death`
- `fix(roles): correct AlphaWolf super() chain`
- `refactor(actions): extract priority into ActionProcessorMixin`

## 什么时候写 ADR

写：
- 引入/换掉核心依赖
- 跨多个模块的接口变更
- 性能/安全的关键取舍
- 重大架构变更

不写：
- bug 修复、重命名、文档改进
- 依赖小版本升级（除非 breaking）

判断口径：**未来三个月有人会问"为什么当初这么做"——就写**。

## 写新 ADR

1. 复制 `docs/adr/README.md` 里的模板
2. 新建 `docs/adr/NNNN-标题.md`，编号顺延
3. 控制在 100 字内，5 分钟搞定
4. 在 `docs/adr/README.md` 索引里加一行
5. 状态从 `proposed` → `accepted`（讨论完）→ `superseded by ADR-XXXX`（被替代）

## 生成 CHANGELOG

发版前跑：

```bash
git cliff --config .github/cliff.toml -o CHANGELOG.md
git add CHANGELOG.md
git commit -m "chore: update CHANGELOG for vX.Y.Z"
git tag vX.Y.Z
```

CHANGELOG 内容由 commit message 决定，不需要手写。

## 提 PR

GitHub 自动加载 `.github/PULL_REQUEST_TEMPLATE.md`，两行填完：

```
## 改了什么
<一句话>
```

如果是大决策，关联对应 ADR；如果影响路线图，更新 `roadmap.md`。

## 五个场景速查

**加新功能** → 先写 ADR（如果跨模块）→ 写代码 → PR 同时带 ADR + 代码 → 划 roadmap

**修 bug** → 写代码 → commit 用 `fix:` → PR → 不需要 ADR

**重构** → commit 用 `refactor:` → 跨模块就要 ADR

**升级依赖** → commit 用 `chore(deps):` → 不需要 ADR

**发版** → 跑 `git cliff` → tag → push tag
`````

- [ ] **Step 2: 验证内容**

Run: `head -20 docs/workflow.md`
Expected: 看到 "Workflow" 标题、"三类常见动作"表格

- [ ] **Step 3: Commit**

```bash
git add docs/workflow.md
git commit -m "docs: add workflow guide"
```

---

## Task 7: 写 docs/arch.md（架构说明）

**Files:**
- Create: `docs/arch.md`

- [ ] **Step 1: 创建 arch.md**

写入：

```markdown
# Architecture

LLM 狼人杀项目的整体架构。

## 整体分层

项目分四层：

1. **入口层** — `cli.py`（自动 Console 模式）/ `tui.py`（Textual TUI）
2. **引擎层** — `core/engine/` 下 `GameEngine` 通过 7 个 Mixin 拼装
3. **领域层** — `core/actions/` / `core/roles/` / `core/agent.py` 三套接口实现
4. **状态层** — `core/game_state.py`（`GameState`）+ `core/events.py`（`EventLogger`）

各层只依赖下层接口（通过 `core/types/protocols.py` 中的 Protocol 声明），不耦合具体实现。

## 引擎：Mixin 组合

`GameEngine` 主类不写代码，只多继承 7 个 Mixin：

- `NightPhaseMixin` — 夜晚阶段（含狼人讨论）
- `SheriffElectionMixin` — 警长竞选（仅第一晚后）
- `DayPhaseMixin` — 白天发言
- `VotingPhaseMixin` — 白天投票
- `DeathHandlerMixin` — 死亡处理（狼刀/毒/恋人殉情/猎枪/警徽转移）
- `ActionProcessorMixin` — 行动优先级排序与执行
- `GameEngineBase` — 初始化与 `play_game` 主循环

`play_game()` 主循环按 `SETUP → NIGHT → [SHERIFF_ELECTION] → DAY_DISCUSSION → DAY_VOTING → ...` 推进阶段，每个阶段后检查胜负。

选择 Mixin 而非单一类的理由：见 [ADR-0001](adr/0001-mixin-engine.md)。

## 角色系统

20+ 角色分三大阵营，全部继承 `core/roles/base.py` 的 `Role` 抽象基类，实现 `get_config()` 与 `async get_night_actions()`：

- **狼人阵营**（`core/roles/werewolf.py`）：Werewolf / AlphaWolf / WhiteWolf / WolfBeauty / GuardianWolf / HiddenWolf / NightmareWolf / BloodMoonApostle
- **村民阵营**（`core/roles/villager.py`）：Villager / Seer / Witch / Hunter / Guard / Idiot / Elder / Knight / Magician / Cupid / Raven / GraveyardKeeper
- **中立**（`core/roles/neutral.py`）：Thief / Lover / WhiteLoverWolf

角色注册由 `core/role_registry.py` 维护名字到类的映射。

## Action 系统：Command 模式

每个夜间行动是一个 Action 子类（`VoteAction` / `WerewolfVoteAction` / `SeerCheckAction` 等），实现 `validate()` 与 `execute()`。`ActionProcessorMixin` 按 `ActionPriority` 降序执行：

| 优先级 | 角色 |
|---|---|
| 100 | Cupid（首夜连恋）|
| 98 | Nightmare Wolf（封禁）|
| 95 | Thief |
| 90 | Guard / Guardian Wolf |
| 80 | Werewolf（投票杀人）|
| 75 | White Wolf（额外杀同伴）|
| 70 | Witch（解药/毒药）|
| 60 | Seer |
| 50 | Graveyard Keeper |
| 40 | Raven |

被 Nightmare Wolf 封禁的演员行动直接跳过。

## Agent 抽象

Agent 通过结构化协议 `AgentProtocol` 解耦：只要有 `name`、`model`、`async get_response()` 即可接入。

- `DemoAgent` — 用正则识别题型返回随机响应（无 API 调试）
- `HumanAgent` — 接终端 `input()`
- `LLMAgent` — 包装 `AsyncOpenAI` 客户端，含 3 次重试 + 30s 超时
- `AgentScopeWerewolfAgent`（`adapter/agent.py`）— AgentScope 集成（进行中）

用 Protocol 而非 ABC 的理由：见 [ADR-0002](adr/0002-protocols-over-abc.md)。

## 信息隔离

两层防御保证玩家只能看到允许看到的信息：

1. **`Event.visible_to`** — 事件自带可见性列表（`None` 表示全员可见，列表表示仅特定玩家）。`EventLogger.get_events_for_player(pid)` 自动过滤。
2. **`Role.get_private_notes(game_state)`** — 每个角色实现自己的"私密笔记"方法：
   - Werewolf → 队友名单
   - Seer → 历史查验结果
   - Witch → 今晚狼刀目标 + 药剂剩余
   - Guard → 上一夜保护的人

`ObservationBuilder`（`core/observation.py`）把公共状态 + 可见事件 + 私密笔记拼成单玩家提示词。

## 异步

所有阶段方法（`play_game` / `run_night_phase` / `run_day_phase` 等）都是 `async`；`LLMAgent` 用 `AsyncOpenAI` 并发友好。无 IO 的方法（`_log_event`、状态读取）保持同步。

理由：见 [ADR-0003](adr/0003-async-engine.md)。

## 配置

`configs/*.yaml` 通过 `PlayersConfig`（Pydantic）反序列化，含玩家名、模型、API 设置。

`GameConfig` 由 `create_game_config_from_player_count(n)` 按人数自动生成：

- 6–8 人：2 狼 + Seer/Witch + Villager
- 9–11 人：+AlphaWolf + Guard + Hunter
- 11+：+Cupid
- 12–14 人：+WhiteWolf
- 13+：+Idiot
- 15+ 人：+WolfBeauty + Elder
- 17+：+Knight
- 19+：+Raven

剩余位补 Villager。

## 本地化

`core/locale.py` 中 `Locale.MESSAGES` 字典维护三语模板（en-US / zh-TW / zh-CN）。`Locale.get(key, **kwargs)` 返回格式化后的字符串。引擎在生成事件消息时统一走 Locale，UI 层不做翻译。

## 序列化

`core/serialization.py` 将 `GameState` 通过 `GameStateSnapshot`（Pydantic）扁平化为 JSON。逐角色提取私有状态（Witch 药剂、Guard `last_protected`、Cupid `has_linked` 等）。Agent 不序列化，恢复时通过 `agent_factory: dict[player_id, agent]` 重注入。
```

- [ ] **Step 2: 验证内容**

Run: `head -20 docs/arch.md`
Expected: 看到 "Architecture" 标题与分层说明

- [ ] **Step 3: Commit**

```bash
git add docs/arch.md
git commit -m "docs: add architecture overview"
```

---

## Task 8: 写 .github/PULL_REQUEST_TEMPLATE.md

**Files:**
- Create: `.github/PULL_REQUEST_TEMPLATE.md`

- [ ] **Step 1: 创建 PR 模板**

写入：

```markdown
## 改了什么


<!-- 如果是大决策，新加一篇 ADR：docs/adr/00xx-xxx.md -->
<!-- 如果影响了路线图，更新 docs/roadmap.md -->
```

- [ ] **Step 2: 验证内容**

Run: `cat .github/PULL_REQUEST_TEMPLATE.md`
Expected: 4 行（标题、空行、两条注释）

- [ ] **Step 3: Commit**

```bash
git add .github/PULL_REQUEST_TEMPLATE.md
git commit -m "docs: add PR template"
```

---

## Task 9: 给三个 README 末尾追加"约定"小节

**Files:**
- Modify: `README.md`（末尾追加，英文版）
- Modify: `README.zh-CN.md`（末尾追加，简中版）
- Modify: `README.zh-TW.md`（末尾追加，繁中版）

- [ ] **Step 1: 检查三个 README 当前末尾内容**

Run:
```bash
tail -10 README.md
echo "---"
tail -10 README.zh-CN.md
echo "---"
tail -10 README.zh-TW.md
```
Expected: 看到当前的结尾段落（应有 License 或最后一节）

- [ ] **Step 2: 在 README.md 末尾追加 Conventions 小节**

在 `README.md` 文件末尾追加以下内容（确保前面有一个空行分隔）：

```markdown

## Conventions

- **Commit**: Use [Conventional Commits](https://www.conventionalcommits.org/) format. See [docs/workflow.md](docs/workflow.md).
- **ADR**: For cross-module/interface/performance decisions, write a 5-minute ADR. See [docs/adr/](docs/adr/).
- **CHANGELOG**: Auto-generated by git-cliff. Do not hand-edit.
- **Roadmap**: See [docs/roadmap.md](docs/roadmap.md).
```

- [ ] **Step 3: 在 README.zh-CN.md 末尾追加"约定"小节**

在 `README.zh-CN.md` 文件末尾追加以下内容（确保前面有一个空行分隔）：

```markdown

## 约定

- **Commit**：用 [Conventional Commits](https://www.conventionalcommits.org/zh-hans/) 格式。详见 [docs/workflow.md](docs/workflow.md)。
- **ADR**：跨模块/接口/性能取舍的决策写一篇 5 分钟 ADR。详见 [docs/adr/](docs/adr/)。
- **CHANGELOG**：由 git-cliff 自动生成，不手写。
- **Roadmap**：见 [docs/roadmap.md](docs/roadmap.md)。
```

- [ ] **Step 4: 在 README.zh-TW.md 末尾追加"約定"小節**

在 `README.zh-TW.md` 文件末尾追加以下内容（确保前面有一个空行分隔）：

```markdown

## 約定

- **Commit**：使用 [Conventional Commits](https://www.conventionalcommits.org/zh-hant/) 格式。詳見 [docs/workflow.md](docs/workflow.md)。
- **ADR**：跨模組/介面/效能取捨的決策寫一篇 5 分鐘 ADR。詳見 [docs/adr/](docs/adr/)。
- **CHANGELOG**：由 git-cliff 自動產生，不手寫。
- **Roadmap**：見 [docs/roadmap.md](docs/roadmap.md)。
```

- [ ] **Step 5: 验证三个文件都加了对应小节**

Run:
```bash
grep -c "Conventions" README.md
grep -c "约定" README.zh-CN.md
grep -c "約定" README.zh-TW.md
```
Expected: 每个命令至少返回 1（表示对应小节存在）

- [ ] **Step 6: Commit（三个 README 一起提交）**

```bash
git add README.md README.zh-CN.md README.zh-TW.md
git commit -m "docs: add Conventions section pointing to docs/"
```

---

## Task 10: 安装 git-cliff 并生成首版 CHANGELOG.md

**Files:**
- Create: `CHANGELOG.md`（由 git-cliff 生成）

- [ ] **Step 1: 安装 git-cliff**

Run: `uv tool install git-cliff`
Expected: 安装成功，类似 "Installed package git-cliff vX.Y.Z"

如果已安装，输出会是 "git-cliff is already installed"，也算成功。

- [ ] **Step 2: 验证 git-cliff 可用**

Run: `git cliff --version`
Expected: 输出版本号，如 `git-cliff 2.x.x`

- [ ] **Step 3: 生成 CHANGELOG.md**

Run:
```bash
git cliff --config .github/cliff.toml -o CHANGELOG.md
```
Expected: 生成 CHANGELOG.md，输出类似 "Generated CHANGELOG.md"

- [ ] **Step 4: 验证 CHANGELOG.md 内容合理**

Run: `head -30 CHANGELOG.md`
Expected: 看到按版本/日期分段的变更记录，分类有 Features / Bug Fixes / Refactor 等，从你之前所有 `feat:` `fix:` `refactor:` 等 commit 归类而来

注意：如果 CHANGELOG 看起来不对（比如空、或者格式异常），先检查 `.github/cliff.toml` 是否完整，并确认提交历史中有 Conventional Commits 风格的 commit。

- [ ] **Step 5: Commit**

```bash
git add CHANGELOG.md
git commit -m "chore: bootstrap CHANGELOG via git-cliff"
```

---

## 完成验证

实施完所有 Task 后，最终目录结构应为：

```
MultiAgent-Werewolf/
├── README.md                                ← 末尾加 Conventions 小节
├── README.zh-CN.md                          ← 末尾加 约定 小节
├── README.zh-TW.md                          ← 末尾加 約定 小節
├── CHANGELOG.md                             ← 新增
├── rule.md                                  ← 未动
├── mkdocs.yml                               ← 未动
│
├── docs/
│   ├── arch.md                              ← 新增
│   ├── workflow.md                          ← 新增
│   ├── roadmap.md                           ← 新增
│   ├── adr/
│   │   ├── README.md                        ← 新增
│   │   ├── 0001-mixin-engine.md             ← 新增
│   │   ├── 0002-protocols-over-abc.md       ← 新增
│   │   └── 0003-async-engine.md             ← 新增
│   └── superpowers/                         ← 已存在（设计 spec 和本计划）
│
└── .github/
    ├── PULL_REQUEST_TEMPLATE.md             ← 新增
    └── (其余文件未动)
```

最终验证：

```bash
ls docs/adr/
ls docs/*.md
ls .github/PULL_REQUEST_TEMPLATE.md
ls CHANGELOG.md
git log --oneline -15
```

Expected:
- `docs/adr/` 含 4 个 `.md` 文件
- `docs/` 顶层含 `arch.md` / `workflow.md` / `roadmap.md`
- PR 模板存在
- CHANGELOG.md 存在
- `git log` 看到本计划产出的所有 commit（约 10 个 docs/chore 提交）
