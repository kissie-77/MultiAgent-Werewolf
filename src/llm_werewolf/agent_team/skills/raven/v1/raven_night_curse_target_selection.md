---
skill_id: raven_night_curse_target_selection
prompt_role_key: raven
status: active
source: initial_curated
camp: villager
quality_passed: True
weight: 1.0
win_count: 0
use_count: 0
when_to_use: 渡鸦夜间诅咒行动阶段，需选择次日额外吃票的目标时；信念矩阵触发：对单一目标狼信≥0.7且投票意向已收敛
belief_pattern: concentrated
belief_signals: b1_top_above_0_7,vote_intention_set
---

# 渡鸦夜间诅咒目标选择

## 提取依据
[initial_curated] 渡鸦诅咒在次日投票生效（被诅咒者额外获得一票反对）；应诅咒高狼信目标以放大白天归票收益。

## 公开行为
① 夜间优先诅咒白天狼信最高、且发言/票型最像狼的玩家；② 诅咒后次日白天用公开逻辑引导归票，不必跳渡鸦身份；③ 若狼信分散，诅咒带节奏最凶或投票最异常的玩家。

## 避免
① 不要诅咒狼信很低、逻辑自洽的好人；② 不要把诅咒当成白天技能（诅咒仅在夜间生效）；③ 不要第一天无依据诅咒。

## 信念分布依据
夜间行动·night_action；对单一目标狼信≥0.7；投票意向已收敛
- 分布模式：concentrated
- 触发信号：
  - 最高目标狼信≥0.7
  - 投票意向已锁定到单一座位
