---
skill_id: graveyard_keeper_night_reveal_priority
prompt_role_key: graveyard_keeper
status: active
source: initial_curated
camp: villager
quality_passed: True
weight: 1.0
win_count: 0
use_count: 0
when_to_use: 守墓人夜间查验行动阶段，需从已死亡玩家中选择查验目标时；信念矩阵触发：场上狼信分散，需用死者身份反推剩余狼坑
belief_pattern: dispersed
belief_signals: b1_multi_above_0_5,vote_watching
---

# 守墓人夜间查验死者身份

## 提取依据
[initial_curated] 守墓人仅能查验已死亡玩家的真实阵营；优先查验争议死亡位可快速收缩狼坑。

## 公开行为
① 优先查验昨夜死亡、且白天身份争议最大的玩家（被抗推/被刀/吃毒）；② 用查验结果反推：若死者为狼，复盘其站边与票型找队友；若死者为好人，审视谁从该死亡中获益；③ 白天谨慎透露查验结果，避免过早暴露守墓人。

## 避免
① 不要试图查验存活玩家（规则不允许）；② 不要查验信息量极低、对狼坑收缩帮助不大的死者；③ 不要在无收益时裸跳守墓人。

## 信念分布依据
夜间行动·night_action；场上狼信分散；需用死者身份反推狼坑
- 分布模式：dispersed
- 触发信号：
  - 至少两个目标狼信>0.5
  - 投票意向未锁定到单一座位
