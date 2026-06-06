---
skill_id: prophet_r1_disclose_check_first
prompt_role_key: prophet
status: active
source: initial_curated
camp: villager
quality_passed: True
weight: 1.0
win_count: 0
use_count: 0
when_to_use: 第1轮白天首次发言阶段，已获得夜间查验结果（查杀/金水）时；信念矩阵触发：对单一目标狼信≥0.7且投票意向已收敛到单一目标，或自身被他人狼信≥0.8存在被扛推风险时
belief_pattern: concentrated
belief_signals: b1_target_certain,b1_top_above_0_7,vote_intention_set
---

# 首轮查验结果优先披露

## 提取依据
[initial_curated] 避免预言家因未及时披露身份查验信息被狼人反咬扛推，导致好人阵营前期崩盘。针对 bad_case `seer_silent_on_wolf`（15 局中 13 次）。来源：exp1 LLM 提炼（seed20260601-good-mem）。

## 公开行为
① 开口第一句先报明自己是预言家身份；② 立刻公开昨晚查验的玩家号码以及查验结果（金水/查杀）；③ 再基于查验结果分析其他玩家发言并给出归票建议。

## 避免
禁止先踩人、先分析其他内容，不报身份和查验结果。

## 信念分布依据
第1轮·after_speech；对单一目标狼信极高（1.00）；投票意向已收敛到单一目标
- 分布模式：concentrated
- 触发信号：
  - 存在目标狼信=1.0
  - 最高目标狼信≥0.7
  - 投票意向已锁定到单一座位
