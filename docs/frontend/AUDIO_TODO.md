# 音效待补清单（还需生成）

> **模块**：frontend / audio
> **状态**：todo（仅剩 BGM）
> **最后更新**：2026-06-09
> **关联**：完整规格见 [AUDIO_SPEC.md](./AUDIO_SPEC.md)
> **进度**：40 项中**已齐 35**、待补 **5（全是 BGM）**。另含 1 个备选 `event_victory_good_alt`。

---

## 文件现状

- **位置**：仓库外暂存 `D:\AI_werewolf\werewolf_6_8\audio`（共 36 个 `.mp3`，含 1 个 alt）
- **命名规约**：`<层>_<id>.mp3` —— `skill_*`(14) / `event_*`(13含alt) / `ui_*`(9)
- **待办**：① 生成 5 段 BGM（`bgm_*`）；② 归位到 `frontend/public/audio/{skill,event,bgm,ui}/`（脚本另出）

---

## ✅ 已完成（35 项）

- **技能 14/14**：`skill_bite/inspect/heal/poison/shoot/guard/charm/mark/link/duel/swap/corpse/fear/vote`
- **事件 12/12**：`event_game_start/death_reveal/execution/shield_break/victory_good/victory_evil/lover_death/vote_tie/nightfall/dawn/vote_tally/sheriff_elected`
- **UI/座位 9/9**：`ui_click/hover/panel_open/panel_close/error/submit/your_turn/tick/timeout`
- **胜利决策**：`victory_good` = 宏伟合唱（`event_victory_good.mp3`）；空灵合唱留作备选（`event_victory_good_alt.mp3`）

---

## ⬜ 待补：BGM 模式（5 段，30–60s 无缝循环，D 小调）

> 模式=`BGM`；响度归一化=开；生成后做无缝循环点。

| 目标文件名 | Prompt |
|---|---|
| `bgm_lobby.mp3` | Dark gothic occult lobby loop, D minor ~60 BPM: slow harp arpeggios over a warm dark pad with distant bells, mysterious anticipation. Seamless loop. |
| `bgm_amb_day.mp3` | Dark gothic daytime bed loop, D minor ~66 BPM: low-tension sustained strings with faint parchment rustle, watchful unease, no melody, no drums. Seamless loop. |
| `bgm_amb_night.mp3` | Dark gothic night bed loop: deep ominous drone with night insects and a slow heartbeat pulse, lurking predation, sparse, no melody. Seamless loop. |
| `bgm_tension.mp3` | Dark gothic tension loop, D minor ~72 BPM: building strings crescendo with rolling timpani and rising dread. Loopable. |
| `bgm_settlement.mp3` | Dark gothic settlement loop: solemn slow strings and pipe organ closing theme, dignified, sits under stingers. Seamless loop. |

---

## Checklist

- [x] `skill_vote` 投票裁决钟声（3s）
- [x] `ui_tick` 倒计时滴答（0.5s）
- [x] `event_vote_tally` 计票定槌声（2s）
- [x] `event_sheriff_elected` 警长当选号角（2s）
- [x] `event_nightfall` 入夜转场（3s）
- [x] `event_dawn` 天亮转场（3s）
- [x] `event_victory_evil` 狼人胜利-阴暗（4s）
- [x] 选定 `victory_good` = 宏伟合唱
- [ ] `bgm_lobby` 大厅循环（BGM）
- [ ] `bgm_amb_day` 白天氛围床（BGM）
- [ ] `bgm_amb_night` 黑夜氛围床（BGM）
- [ ] `bgm_tension` 竞选紧张层（BGM）
- [ ] `bgm_settlement` 结算循环（BGM）
- [ ] 归位脚本：`audio/` → `frontend/public/audio/{skill,event,bgm,ui}/`
