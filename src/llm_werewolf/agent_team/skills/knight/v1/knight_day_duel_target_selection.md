---
skill_id: knight_day_duel_target_selection
prompt_role_key: knight
status: active
source: initial_curated
camp: villager
quality_passed: True
weight: 1.0
win_count: 0
use_count: 0
when_to_use: 骑士白天决斗行动阶段（整局仅一次），需选择决斗目标时；信念矩阵触发：对单一目标狼信≥0.7且证据链充分
belief_pattern: concentrated
belief_signals: b1_top_above_0_7,vote_intention_set
---

# 骑士白天决斗目标选择

## 提取依据
[initial_curated] 骑士决斗一次机会：目标是狼则其死，否则骑士死。须在证据充分时使用。

## 公开行为
① 优先决斗狼信最高、且发言/票型矛盾最明显的目标；② 决斗前核对三条证据——发言前后矛盾、投票与站边不一致、回避关键问题；③ 若证据不足，宁可不用也不要赌平民。

## 避免
① 不要因情绪决斗；② 不要在狼信分散、证据不足时仓促决斗；③ 不要决斗逻辑自洽的低狼信好人。

## 信念分布依据
白天行动·day_action；对单一目标狼信≥0.7；证据链充分
- 分布模式：concentrated
- 触发信号：
  - 最高目标狼信≥0.7
  - 投票意向已锁定到单一座位
