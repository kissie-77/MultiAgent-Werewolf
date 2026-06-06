---
skill_id: hunter_death_target_selection
prompt_role_key: hunter
status: active
source: initial_curated
camp: villager
quality_passed: True
weight: 1.0
win_count: 0
use_count: 0
when_to_use: 猎人死亡阶段（被刀或被投票出局），需要选择开枪目标时；信念矩阵触发：对单一目标狼信≥0.7且投票意向已收敛
belief_pattern: concentrated
belief_signals: b1_top_above_0_7,vote_intention_set
---

# 猎人死亡枪口选择

## 提取依据
[initial_curated] 猎人枪口应基于公开票型、发言矛盾与信念矩阵综合判断，避免情绪开枪。

## 公开行为
① 比较目标狼信、白天带队行为、发言逻辑矛盾三条证据；② 优先射击狼信最高且票型/站边异常的目标；③ 若多个目标接近，选发言回避关键问题最明显者。

## 避免
① 不要因情绪或私人恩怨开枪；② 不要在没有证据链时仓促开枪；③ 不要射击狼信很低、逻辑自洽的好人。

## 信念分布依据
死亡阶段·death_action；对单一目标狼信≥0.7；投票意向已收敛
- 分布模式：concentrated
- 触发信号：
  - 最高目标狼信≥0.7
  - 投票意向已锁定到单一座位
