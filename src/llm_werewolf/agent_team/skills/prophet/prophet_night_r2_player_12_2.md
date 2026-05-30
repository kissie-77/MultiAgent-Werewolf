---
skill_id: prophet_night_r2_player_12_2
prompt_role_key: prophet
status: draft
source_run: runs\20260527-204513
source_player_id: player_12
camp: villager
quality_passed: True
weight: 1.0
win_count: 0
use_count: 0
created_at: 2026-05-27T12:45:38+00:00
updated_at: 2026-05-27T12:45:38+00:00
when_to_use: 第2轮夜间：中后局需验证站边摇摆者、跟票异常者或对跳位的情况下，使用该 skill
---

# 第2轮预言家查验决策

## 提取依据
[生成规则: night_action] 第2轮 seer_checked，目标 player_2，结果 villager。

## 何时使用
第2轮夜间：中后局需验证站边摇摆者、跟票异常者或对跳位。

## 公开行为
① 优先验高置位、首日带节奏或投票摇摆的玩家；② 避免连续两晚验同一人；③ 记录 target 与 result，白天再择机报验。 本局验 玩家2（player_2）（中局验人优先跟进站边异常者，验证投票链），结果 好人。

## 避免
① 首夜盲验已建立可信好人面的玩家；② 为「验谁都是好」的低信息位浪费查验；③ 查到狼后不预留白天叙事直接暴露。

## 本局决策
- 目标：player_2
- 查验/结果：好人
- 事件：seer_checked

## 评分
- intention: None
- benefit: None
