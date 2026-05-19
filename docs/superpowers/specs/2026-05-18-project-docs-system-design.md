# 项目文档系统设计

- **日期**: 2026-05-18
- **状态**: approved
- **范围**: MultiAgent-Werewolf 仓库
- **设计风格**: vibecoding 极简

## 目标

为 2–3 人活跃协作的 LLM 狼人杀项目建立轻量级文档体系，覆盖四类痛点：

1. **设计决策追溯** — 未来回顾"为什么这么做"有据可查
2. **进度与任务可见** — 谁在做什么、下一步是什么清晰可见
3. **变更可追溯** — 每次改动改了什么有完整记录
4. **新人/协作上手** — 新成员能按固定路径快速理解项目

## 不做什么 (Non-goals)

- **不部署 mkdocs 站点**：保留现有 `mkdocs.yml` 配置不动，文档仅在 GitHub 上读
- **不引入 CI 自动化**：CHANGELOG 手动运行 `git cliff`，PR 模板不加 lint 检查
- **不强制 Design Spec**：跨模块大功能直接写 ADR 草稿（状态 `proposed`），不预先写长设计文档
- **不替换现有 `rule.md` / README**：rule.md 保留为游戏规则实现对照，README 仅添加"约定"小节
- **不重写历史 commit**：现有提交保持原样，git-cliff 从当前 commit 起开始归类

## 背景

### 现状

- `mkdocs.yml`：完整 mkdocs-material + mkdocstrings 配置，但 `docs/` 目录不存在
- `.github/cliff.toml`：git-cliff 配置已就绪
- `.github/ISSUE_TEMPLATE/`：BUG/FEATURE/DOCUMENTATION/EXPERIMENT 四种 issue 模板已存在
- 提交记录已遵循 Conventional Commits（`feat:` `fix:` `refactor:` `chore(deps):`）
- 真正的"开发过程文档"为零：无 CHANGELOG、无 ADR、无 ROADMAP、无 CONTRIBUTING

### 已有基础设施可复用

- Conventional Commits 提交习惯
- `.github/cliff.toml`（git-cliff 配置）
- `.github/ISSUE_TEMPLATE/`（不动）

## 设计

### 目录结构

```
MultiAgent-Werewolf/
├── README.md                        ← 已有，末尾加"约定"小节
├── README.zh-CN.md                  ← 已有，不动
├── README.zh-TW.md                  ← 已有，不动
├── CHANGELOG.md                     ← 新增，git-cliff 生成
├── rule.md                          ← 已有，不动
│
├── docs/                            ← 新增目录
│   ├── arch.md                      ← 简短架构说明（1–2 屏）
│   ├── workflow.md                  ← 使用教程（文档系统怎么用 + commit 约定）
│   ├── roadmap.md                   ← 阶段目标 + 任务清单
│   └── adr/                         ← 决策记录
│       ├── README.md                ← ADR 索引 + 模板
│       ├── 0001-mixin-engine.md
│       ├── 0002-protocols-over-abc.md
│       └── 0003-async-engine.md
│
└── .github/
    └── PULL_REQUEST_TEMPLATE.md     ← 新增
    (其他 .github/* 不动)
```

### 文件职责

| 文件 | 角色 | 维护频率 |
|---|---|---|
| `CHANGELOG.md` | 版本变更，按 Conventional Commit 类型自动归类 | 发版时手动 `git cliff` |
| `docs/arch.md` | 整体架构落成文（引擎/Agent/Action/隔离层/异步） | 重大架构变更时 |
| `docs/workflow.md` | 文档系统使用教程 + commit 规范 + ADR 触发条件 | 流程约定变化时 |
| `docs/roadmap.md` | 当前迭代 / 下个迭代 / 想做但没排期，checkbox 形式 | 每完成一项划掉 |
| `docs/adr/README.md` | ADR 索引表（编号、标题、状态）+ ADR 模板 | 新增 ADR 时 |
| `docs/adr/00xx-*.md` | 单调追加的决策记录，每篇 ≤ 100 字 | 大决策时新增（约 1–3 篇/月） |
| `.github/PULL_REQUEST_TEMPLATE.md` | PR 表单（GitHub 自动加载），两行填完 | 流程变化时 |

### 关键设计取舍

1. **`CHANGELOG.md` 放仓库根**：约定俗成，工具默认读根目录。
2. **ADR 用四位编号 `0001-xxx.md`**：未来过 100 也不慌。
3. **不用单独的 `docs/decisions/_template.md`**：模板放 `docs/adr/README.md` 顶部，索引和模板共享一个文件，减少文件数。
4. **`mkdocs.yml` / `scripts/gen_docs.py` 保留不动**：将来想上站点直接补 nav 就能用。
5. **目录命名简短**：`adr/` 而非 `decisions/`，`arch.md` 而非 `architecture.md`。vibecoding 风格。
6. **砍掉 `contributing.md` 与 `development.md`**：约定塞 README 末尾，运行说明 README 已有。
7. **砍掉独立的 `design-spec.md` 模板**：大功能用 ADR 草稿（`proposed` 状态）代替。

## 模板与初始内容

### ADR 模板（写在 `docs/adr/README.md`）

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

### PR 模板（`.github/PULL_REQUEST_TEMPLATE.md`）

```markdown
## 改了什么


<!-- 如果是大决策，新加一篇 ADR：docs/adr/00xx-xxx.md -->
<!-- 如果影响了路线图，更新 docs/roadmap.md -->
```

### 三篇初始 ADR

**ADR-0001 (`docs/adr/0001-mixin-engine.md`)**

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

**ADR-0002 (`docs/adr/0002-protocols-over-abc.md`)**

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

**ADR-0003 (`docs/adr/0003-async-engine.md`)**

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

### 初始 ROADMAP（`docs/roadmap.md`）

从 README 的"当前进度"checklist 迁移并细化：

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

### `docs/workflow.md` — 使用教程

````markdown
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
````

### `docs/arch.md` — 架构说明骨架

写时按以下骨架，每节 1–3 段：

1. **整体分层**：CLI/TUI → Engine（Mixin）→ Actions/Roles/Agent → State/Events
2. **引擎**：7 个 Mixin + `play_game` 主循环 → 链接 ADR-0001
3. **角色系统**：20+ 角色三大类（狼/民/中立），统一 `Role` 抽象基类
4. **Action 系统**：Command 模式，按 `ActionPriority` 排序执行
5. **Agent**：DemoAgent / HumanAgent / LLMAgent，统一 `AgentProtocol` → 链接 ADR-0002
6. **信息隔离**：`Event.visible_to` + `ObservationBuilder` + `Role.get_private_notes`
7. **异步**：全链路 async → 链接 ADR-0003
8. **配置**：YAML → `PlayersConfig` → 按人数自动配 `GameConfig`
9. **本地化**：`Locale` 类（en-US / zh-TW / zh-CN）

### README 末尾追加"约定"小节

```markdown
## 约定

- **Commit**：用 [Conventional Commits](https://www.conventionalcommits.org/zh-hans/) 格式。详见 [docs/workflow.md](docs/workflow.md)。
- **ADR**：跨模块/接口/性能取舍的决策写一篇 5 分钟 ADR。详见 [docs/adr/](docs/adr/)。
- **CHANGELOG**：由 git-cliff 自动生成，不手写。
- **Roadmap**：见 [docs/roadmap.md](docs/roadmap.md)。
```

## 落地步骤

按以下顺序创建文件，每一步可单独提交：

1. 创建 `docs/` 目录骨架（空文件占位也行）
2. 写 `docs/adr/README.md`（索引 + 模板）
3. 写三篇初始 ADR（0001/0002/0003）
4. 写 `docs/roadmap.md`（从 README 迁移）
5. 写 `docs/workflow.md`（使用教程）
6. 写 `docs/arch.md`（按骨架，复用项目阅读笔记）
7. 写 `.github/PULL_REQUEST_TEMPLATE.md`
8. 在 README.md / README.zh-CN.md / README.zh-TW.md 末尾追加"约定"小节
9. 安装 git-cliff 并生成首版 `CHANGELOG.md`
   ```bash
   uv tool install git-cliff
   git cliff --config .github/cliff.toml -o CHANGELOG.md
   ```
10. Git commit：`docs: bootstrap project documentation system`

## 工作流（落地后日常）

```
设计阶段（可选）   写 ADR 草稿（状态 proposed）
                       │
                       │ 决策讨论定下
                       ▼
留档阶段              ADR 状态改为 accepted（docs/adr/00xx-*.md）
                       │
                       │ 落地代码时
                       ▼
实现阶段           规范 commit + PR 模板（每个 commit）
                       │
                       │ 合入 main
                       ▼
进度阶段           划掉 roadmap.md 中对应 checkbox
                       │
                       │ 发版时
                       ▼
发版阶段           手动跑 git cliff 生成 CHANGELOG.md → tag
```

**日常负担总量**：每 PR 30 秒填模板 + 每月 1–3 篇 5 分钟 ADR。

## 考虑过的替代方案

### 方案 A：最小版（仅 CONTRIBUTING + 几个模板）
- 一份 `CONTRIBUTING.md`
- 手写 `CHANGELOG.md`
- 一份带 checkbox 的 `ROADMAP.md`

**为什么不选**：模板光放不用，三个月后还是没 ADR、没真 CHANGELOG。3 人协作的痛点没解决。

### 方案 C：完整版 + 立即激活 mkdocs 站点 + CI
- 本方案 + GitHub Pages 部署 + markdown lint CI + mkdocstrings API 参考

**为什么不选**：与"现在只用 .md，以后再上站点"的决策冲突；初期负担过大。

### 早期方案 B（mkdocs 兼容结构）
最初方案目录设计为兼容 mkdocs 导航（如 `docs/development/`、`docs/architecture/` 子目录）。用户选择"纯 .md，不顾及 mkdocs 兼容"后简化为扁平结构。

## 风险与缓解

| 风险 | 缓解 |
|---|---|
| ADR 写一段时间后被遗忘 | `docs/workflow.md` 明确触发条件；README"约定"提示 |
| git-cliff 没人记得运行 | 把命令写进 workflow.md；未来想自动化时再上 CI |
| roadmap.md 与实际进度脱节 | PR 模板中提示更新 roadmap |
| Conventional Commits 不规范 | 已有 `.pre-commit-config.yaml`，可后续加 commitlint |

## 成功标准

- 实施一个月后 `docs/adr/` 至少有 4–6 篇 ADR（初始 3 篇 + 新决策）
- 实施一个月后 `roadmap.md` 至少更新过 2 次
- 新成员阅读 README → arch.md → adr/ 路径能在 1 小时内理解项目主结构
- `CHANGELOG.md` 与实际 commit 历史一致（每次发版后重新生成）
