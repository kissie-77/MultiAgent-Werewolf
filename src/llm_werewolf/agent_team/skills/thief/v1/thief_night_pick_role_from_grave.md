---
skill_id: thief_night_pick_role_from_grave
prompt_role_key: thief
status: active
source: initial_curated
camp: neutral
quality_passed: True
weight: 1.0
win_count: 0
use_count: 0
when_to_use: 盗贼首夜选身份阶段，墓底有两张身份牌可选时；信念矩阵触发：首夜信息空窗，需按阵营收益选择身份
belief_pattern: dispersed
belief_signals: vote_watching
---

# 盗贼首夜身份选择

## 提取依据
[initial_curated] 盗贼首夜从两张未发身份中选择，选择后阵营与技能随之确定。

## 公开行为
① 墓底有预言家/女巫等强神职时，优先选神职获取夜间信息优势；② 若判断狼队偏强且墓底有狼，可选狼身份潜伏；③ 若两张均为弱身份，选后低调观察，择机跳身份。

## 避免
① 不要选狼后立刻倒向狼队（除非确定狼面极大）；② 不要选神职后首白天就裸跳；③ 不要忽视选定身份后的技能使用时机。

## 信念分布依据
首夜·night_action；信息空窗，按阵营收益选身份
- 分布模式：dispersed
- 触发信号：
  - 投票意向未锁定到单一座位
