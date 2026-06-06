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

| #                                                   | 标题                          | 状态     |
| --------------------------------------------------- | ----------------------------- | -------- |
| [0001](0001-mixin-engine.md)                        | 引擎用 Mixin 组合而非单类     | accepted |
| [0002](0002-protocols-over-abc.md)                  | 用 Protocol 而非 ABC 描述接口 | accepted |
| [0003](0003-async-engine.md)                        | 引擎全异步化                  | accepted |
| [0004](0004-offline-game-correctness-evaluation.md) | 离线游戏正确性评测独立成模块  | accepted |
