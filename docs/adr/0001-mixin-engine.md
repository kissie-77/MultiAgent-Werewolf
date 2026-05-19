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
