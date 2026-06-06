---
skill_id: guardian_wolf_night_protect_wolf_teammate
prompt_role_key: guardian_wolf
status: active
source: initial_curated
camp: werewolf
quality_passed: True
weight: 1.2
win_count: 0
use_count: 0
when_to_use: 守卫狼夜间守护行动阶段，需选择守护目标时；狼队矩阵触发：W-E暴露雷达显示某狼队友综合暴露≥0.60，或白狼王隔夜刀狼风险升高
belief_pattern: mixed
---

# 守卫狼夜间守护狼队友

## 提取依据
[initial_curated] 守卫狼仅能守护狼队友（防白狼隔夜刀狼等）；应保护高暴露、仍有关键扛推价值的队友。

## 公开行为
① 优先守护 W-E 综合暴露≥0.60 的狼队友；② 若预判白狼王当夜可能刀狼，守护白天最被怀疑的队友；③ 若无高暴露队友，守护带节奏能力最强、不宜过早损失的狼队友。

## 避免
① 不要守护好人（技能仅对狼队友生效）；② 不要守护暴露极低、可牺牲的队友；③ 不要连续两夜守护同一人（若规则禁止连守）。

## 信念分布依据
夜间行动·night_action；队友暴露偏高需保护
- 分布模式：mixed
- 触发信号：
  - 队友暴露≥0.60
  - 白狼刀狼风险升高
