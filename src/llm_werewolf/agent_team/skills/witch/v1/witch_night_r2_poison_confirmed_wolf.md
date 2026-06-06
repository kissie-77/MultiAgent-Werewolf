---
skill_id: witch_night_r2_poison_confirmed_wolf
prompt_role_key: witch
status: active
source: initial_curated
camp: villager
quality_passed: True
weight: 1.0
win_count: 0
use_count: 0
when_to_use: 第2轮及以后夜间：解药已用或场上已形成较清晰狼坑，需用毒药收轮次时；信念矩阵触发：对单一目标狼信≥0.7且该目标与白天票型/验人信息一致时
belief_pattern: concentrated
belief_signals: b1_top_above_0_7,vote_intention_set
---

# 女巫毒药使用决策

## 提取依据
[initial_curated] 女巫毒药决策启发式，弥补批量提取中毒药素材质量参差（多局毒药未命中狼人而被跳过）。

## 公开行为
① 毒前核对公开验人、票型与发言逻辑是否指向同一狼坑；② 优先毒与预言家查杀一致或白天抗推失败的高威胁位；③ 用药后白天谨慎透露信息，避免立刻暴露女巫。

## 避免
无依据盲毒、毒已建立可信面的好人、用药后立即跳明女巫。

## 信念分布依据
对单一目标狼信≥0.7；投票意向已收敛到单一目标
- 分布模式：concentrated
- 触发信号：
  - 最高目标狼信≥0.7
  - 投票意向已锁定到单一座位
