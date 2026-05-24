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
