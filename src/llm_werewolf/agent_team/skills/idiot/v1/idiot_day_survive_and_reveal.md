---
skill_id: idiot_day_survive_and_reveal
prompt_role_key: idiot
status: active
source: initial_curated
camp: villager
quality_passed: True
weight: 1.0
win_count: 0
use_count: 0
when_to_use: 白痴被投票出局、触发翻牌存活时；信念矩阵触发：自身被他人狼信≥0.8存在被扛推风险
belief_pattern: self_exposed
belief_signals: b2_top_above_0_8_on_me
---

# 白痴翻牌存活后发言带队

## 提取依据
[initial_curated] 白痴翻牌后存活但失去投票权；应通过发言归票弥补无法投票的劣势。

## 公开行为
① 翻牌后第一句亮明白痴身份，说明自己不会被投票出局；② 利用免死金牌大胆点出高狼信目标，给出清晰归票建议；③ 呼吁在场好人跟票，自己虽不能投票但仍可提供逻辑链。

## 避免
① 翻牌后不要继续划水；② 不要伪造夜间信息（白痴无夜间信息）；③ 不要误以为翻牌后仍能投票。

## 信念分布依据
投票出局·vote_out；自身被高怀疑（B2≥0.8）
- 分布模式：self_exposed
- 触发信号：
  - 最高他人疑狼≥0.8（指向自身）
