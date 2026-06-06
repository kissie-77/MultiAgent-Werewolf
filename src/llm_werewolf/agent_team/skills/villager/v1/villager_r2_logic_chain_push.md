---
skill_id: villager_r2_logic_chain_push
prompt_role_key: villager
status: active
source: initial_curated
camp: villager
quality_passed: True
weight: 1.0
win_count: 0
use_count: 0
when_to_use: 白天讨论进入归票阶段，场上出现发言与投票不一致、或某玩家站边与票型矛盾时；信念矩阵触发：场上狼信分散（Top狼信≤0.5）且投票意向尚未收敛，适合平民用公开信息带节奏收束票型
belief_pattern: dispersed
---

# 平民逻辑链归票

## 提取依据
[initial_curated] 平民白天逻辑链归票范例，弥补 15 局批量提取中村民说服素材不足（仅 5 条 skill，多局 persuasion 未过门）。

## 公开行为
① 用公开信息串联矛盾点（发言前后不一致、投票与站边冲突、回避关键问题）；② 给出单一归票目标与一句可跟票理由，避免多目标分散；③ 不跳神、不伪造夜间信息，只基于已公开发言与票型推理。

## 避免
空泛划水、只跟票不带逻辑、为站边强行改口导致自身逻辑崩盘。

## 信念分布依据
场上狼信分散（Top狼信≤0.5）；投票意向未收敛；适合平民主动带节奏、收束票型
- 分布模式：dispersed
- 触发信号：
  - 最高目标狼信≤0.5
  - 投票意向未锁定到单一座位

## 本局发言摘录
> 我梳理一下：某玩家前两轮站边A，投票却跟到B，前后不一致。今天先把该玩家放上票型，看他怎么解释。
