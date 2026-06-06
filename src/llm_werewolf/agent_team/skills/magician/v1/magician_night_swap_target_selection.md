---
skill_id: magician_night_swap_target_selection
prompt_role_key: magician
status: active
source: initial_curated
camp: villager
quality_passed: True
weight: 1.0
win_count: 0
use_count: 0
when_to_use: 魔术师夜间交换行动阶段（整局仅一次），需选择交换两名玩家身份时；信念矩阵触发：场上狼信分散，需用交换打乱狼队刀口或保护神职
belief_pattern: dispersed
belief_signals: b1_multi_above_0_5,vote_watching
---

# 魔术师夜间交换身份选择

## 提取依据
[initial_curated] 魔术师整局可交换两名玩家身份一次；被交换者最初不察觉，可用于保护神职或迷惑狼队。

## 公开行为
① 优先交换「高狼信疑似狼」与「低威胁安全位」身份，打乱狼刀节奏；② 若神职已暴露，可将神职与低调好人交换身份以保护；③ 交换后白天勿主动暴露交换逻辑，除非有排坑收益。

## 避免
① 不要交换两个已知同阵营且无战术收益的玩家；② 不要交换已死亡玩家；③ 不要交换后立即裸跳魔术师。

## 信念分布依据
夜间行动·night_action；狼信分散；需打乱刀口或保护神职
- 分布模式：dispersed
- 触发信号：
  - 至少两个目标狼信>0.5
  - 投票意向未锁定到单一座位
