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
