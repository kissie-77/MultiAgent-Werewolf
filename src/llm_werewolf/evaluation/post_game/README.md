# Post-Game Analysis

对局结束后的复盘流水线：投票摇摆、阵营说服、日志多视角、意向/收益打分、Prompt 提案 JSON、Skill 草案（不写入运行时 v2 Prompt）。

## 触发

- 真实 LLM 对局：`interface/cli.py` → `finalize_run` → `run_post_game_pipeline`
- 仅生成摇摆报告：`werewolf-vote-swing <run_dir>`
- 批量正确性评测内可选调用：`correctness/runner.py`（`skip_llm=True`）

## 流水线顺序

1. `vote_swing_analysis` — 说服摇摆报告
2. `camp_persuasion` — 阵营匹配标注
3. `log_views` — god / player POV / digest（供人读；**不**默认喂复盘 LLM）
4. `intention_scores` — 投票意向分
5. `score_contexts` — **分维度隔离上下文**（persuasion / wolf_night / strategy / outcome）
6. `benefit_scores.json` — 收益分 v2（**先于 MVP**）
7. `mvp_scores.json` — 规则层 MVP（含 benefit 维度 + 金句）
8. `eval_agent` — LLM 复盘：仅读 MVP 分 + 各维度 `views/score_contexts/*.md`
9. `game_quality_report` — 人读总览 + 步骤表
10. `prompt_proposals` — MVP 金句 + `llm_suggestion` + bad case
11. `role_skills` — v2 卡片（背景/场景/引用）

真 API 对局验收见 [`docs/真实对局测试清单.md`](../../../docs/真实对局测试清单.md)。

### 分维度上下文（评分与复盘）

| 维度 | 材料范围 |
| --- | --- |
| `persuasion` | 白天公开发言、`channel=public` 投票意向 |
| `wolf_night` | `channel=wolf_team` 狼队讨论 + 当晚刀口 |
| `strategy` | 验人/用药/守护/票型等行为事件（无发言正文） |
| `outcome` | 投票、出局、死亡、胜负（无发言/意向） |

规则计分 **只** 读取对应维度；复盘 Agent **禁止** 使用 `god_timeline` 或全量 `events.jsonl`。

## 典型产物（`runs/<timestamp>/` 或 eval 子目录）

```text
game_quality_report.md      # 人读：MVP、金句、排名、流水线状态
game_quality_report.json
mvp_scores.json             # 规则层 MVP（可败方）
post_game_steps.json        # 每步 ok/failed/skipped
vote_swing_report.md
camp_persuasion_report.md
views/score_contexts/       # 分维度材料（复盘 LLM 用）
intention_scores.json
benefit_scores.json
prompt_proposals.json
role_skills.json
post_game_manifest.json
```

正确性批量评测见 [`../correctness/README.md`](../correctness/README.md)。
