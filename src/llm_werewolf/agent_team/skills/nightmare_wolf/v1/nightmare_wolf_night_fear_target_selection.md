---
skill_id: nightmare_wolf_night_fear_target_selection
prompt_role_key: nightmare_wolf
status: active
source: initial_curated
camp: werewolf
quality_passed: True
weight: 1.2
win_count: 0
use_count: 0
when_to_use: 梦魇狼夜间恐惧（封锁）行动阶段，需选择封锁目标时；狼队矩阵触发：W-G显示某座位神职威胁≥0.75，或该玩家当夜可能使用关键技能
belief_pattern: mixed
---

# 梦魇狼夜间封锁目标选择

## 提取依据
[initial_curated] 梦魇狼封锁使目标当夜无法使用技能；应封锁当夜最可能用药/查验/守护的神职。

## 公开行为
① 优先封锁 W-G 威胁分最高的疑似预言家或女巫；② 若当晚狼刀与毒口可能冲突，封锁女巫以防毒药；③ 残局封锁带队能力最强的存活好人。

## 避免
① 不要封锁划水平民（收益低）；② 不要封锁狼队友；③ 不要因情绪封锁无关目标。

## 信念分布依据
夜间行动·night_action；神职威胁高或当夜可能开技能
- 分布模式：mixed
- 触发信号：
  - W-G神职威胁≥0.75
  - 当夜技能冲突风险高
