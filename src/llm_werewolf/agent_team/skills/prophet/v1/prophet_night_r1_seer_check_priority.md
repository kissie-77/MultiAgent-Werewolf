---
skill_id: prophet_night_r1_seer_check_priority
prompt_role_key: prophet
status: active
source: initial_curated
camp: villager
quality_passed: True
weight: 1.0
win_count: 0
use_count: 0
when_to_use: 第1轮夜间：首夜信息空窗，需在一验定方向的高收益目标中做选择；信念矩阵触发：场上无公开验人信息，优先验高置位、首日带节奏或票型摇摆的玩家
---

# 首夜查验目标选择

## 提取依据
[initial_curated] 首夜查验启发式，综合 15 局 night_action 规则提取共性（多局验出狼人且质量门通过）。

## 公开行为
① 优先验高置位、首日带节奏或投票摇摆的玩家；② 避免连续两晚验同一人；③ 记录 target 与 result，白天再择机报验（查杀须优先披露身份）。

## 避免
首夜盲验已建立可信好人面的玩家；为低信息位浪费查验；查到狼后不预留白天叙事直接暴露。

## 本局决策
- 事件：seer_checked
- 查验/结果：优先选择高置位或带节奏玩家，结果用于白天报验
