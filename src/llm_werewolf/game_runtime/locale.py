"""游戏消息的本地化支持。"""

from typing import ClassVar


class Locale:
    """管理本地化游戏消息。"""

    # 各语言区域的消息模板
    MESSAGES: ClassVar[dict[str, dict[str, str]]] = {
        "en-US": {
            # 阶段切换
            "night_begins": "Night {round_number} begins",
            "day_begins": "Day {round_number} begins",
            "voting_phase": "Voting Phase",
            "game_started": "Game started with {player_count} players",
            "game_ended": "Game ended. {winner} wins! {reason}",
            "game_over": "\nGame Over! {winner} camp wins!",
            # 阶段分隔线
            "phase_separator": "=" * 60,
            "night_separator": "🌙 " + "=" * 56 + " 🌙",
            "day_separator": "☀️  " + "=" * 56 + " ☀️",
            # 玩家状态
            "alive_players": "\nAlive Players:",
            "dead_players": "\nDead Players:",
            "player_role_info": "- {name} ({role})",
            # 死亡
            "player_died": "{player} died",
            "killed_by_werewolves": "{player} was killed by werewolves",
            "voted_out": "{player} was voted out",
            "player_eliminated": "{player} was eliminated by vote. They were a {role}.",
            "player_eliminated_hidden": "{player} was eliminated by vote.",
            "werewolf_vote_tie_break": "Wolf pack tied on kill target; {breaker} breaks the tie.",
            "died_of_heartbreak": "{player} died of heartbreak (lover)!",
            "died_from_charm": "{player} died from Wolf Beauty's charm (Wolf Beauty {wolf_beauty} was eliminated)!",
            # 投票
            "vote_cast": "🗳️ {voter} votes for {target}",
            "vote_summary": "\n📊 Vote Summary:",
            "vote_count": "  {target}: {count} vote(s) - {voters}",
            "vote_tied": "Vote tied. No one is eliminated.",
            "no_votes": "No votes cast.",
            # 主持人播报
            "narrator_night_falls": "🌙 Night falls, everyone close your eyes...",
            "narrator_werewolves_wake": "🐺 Werewolves, please open your eyes and discuss...",
            "narrator_werewolves_vote": "🐺 Werewolves, please vote for your target...",
            "narrator_werewolves_sleep": "🐺 Werewolves, close your eyes...",
            "narrator_daybreak": "☀️ The sun rises, everyone open your eyes...",
            # 角色行动
            "role_acting": "🎬 {role} ({player}) is acting...",
            "player_speech": "{player}: {speech}",
            "werewolf_discussion": "🐺 {player} (Werewolf): {speech}",
            "werewolf_voting": "🐺 Werewolves are discussing their target...",
            "werewolf_target": "🐺 Werewolves targeted {target}",
            "werewolf_vote_tally": "🐺 Wolf team votes resolved (target: {target})",
            "seer_checked_public": "🔮 Seer checked {target}",
            "witch_saved": "💊 Witch saved {target}",
            "witch_poisoned": "☠️ Witch poisoned {target}",
            "guard_protected": "🛡️ Guard protected {target}",
            "seer_checked": "🔮 Seer checked {target}: {result}",
            "hunter_shoots": "🏹 Hunter {hunter} shoots {target}",
            "alpha_wolf_shoots": "🐺👑 Alpha Wolf {alpha} shoots {target}",
            "white_wolf_shoots": "🐺⚪ White Wolf {white_wolf} takes {target}",
            "white_wolf_self_explodes": "🐺⚪ White Wolf {player} self-destructs",
            "lovers_linked": "💕 Lovers linked: {player1} and {player2}",
            "white_wolf_kills": "🐺⚪ White Wolf kills {target}",
            "wolf_beauty_charms": "🐺💋 Wolf Beauty charms {target}",
            "cupid_links": "💘 Cupid links {player1} and {player2} as lovers",
            # 特殊情况
            "idiot_revealed": "{player} reveals they are the Idiot and survives!",
            "elder_executed": "The Elder was executed by the village! All villagers lose their special abilities as punishment!",
            "elder_attacked": "{player} was attacked but survived (Elder)!",
            "protected_by_guard": "{player} was protected by the guard!",
            "saved_by_witch": "{player} was saved by the witch!",
            "poisoned_no_ability": "{player} was poisoned by the Witch and cannot use their death ability.",
            "death_ability_active": "{player} ({role}) can shoot before dying!",
            # 警长选举
            "sheriff_campaign_started": "Sheriff election begins. Players may volunteer to campaign for sheriff.",
            "no_candidates": "No one volunteered to campaign for sheriff. There will be no sheriff this game.",
            "player_volunteers": "{player} volunteers to campaign for sheriff.",
            "sheriff_single_candidate": "Only {player} is running for sheriff. No vote is needed.",
            "campaign_speeches_start": "{count} candidates will now give their campaign speeches.",
            "candidate_speech": "{candidate}'s speech: {speech}",
            "no_voters": "No non-candidate players available to vote. All players are candidates.",
            "sheriff_voting_start": "{count} non-candidate player(s) will now vote for sheriff.",
            "sheriff_vote_cast": "{voter} voted for {candidate}.",
            "sheriff_vote_abstained": "{voter} abstained from voting.",
            "sheriff_vote_result": "{candidate} received {votes} vote(s).",
            "sheriff_tie": "Tie between {candidates}. No sheriff this game.",
            "sheriff_elected": "{player} has been elected sheriff!",
            # 警徽移交
            "sheriff_died_transfer": "Sheriff {sheriff} has died. They may transfer the badge or tear it.",
            "sheriff_badge_torn": "{sheriff} tore the sheriff badge. There is no sheriff anymore.",
            "sheriff_badge_transferred": "{sheriff} transferred the sheriff badge to {target}.",
            # 其他技能
            "elder_penalty": "All villager abilities disabled due to Elder execution",
            "nightmare_blocked": "{player} ({role}) was blocked by Nightmare Wolf",
            "witch_uses_poison": "🧪 Witch used poison on {target}",
            "witch_poisoned_target": "{target} was poisoned by witch",
            # 错误消息
            "speech_failed": "{player}: [Speech failed - {error}]",
            "discussion_failed": "{player}: [Discussion failed - {error}]",
            "night_action_failed": "{role} ({player}): [Night action failed - {error}]",
            "action_failed": "{role} ({player}): [Action failed - {error}]",
            "action_rejected": "{role} ({player}): [Action rejected - {action}]",
            "vote_failed": "{player}: [Vote failed - {error}]",
            "guardian_wolf_protected": "🐺🛡️ Guardian Wolf protected {target}",
            "raven_marks": "🐦‍⬛ Raven marked {target}",
            "graveyard_keeper_checked": "⚰️ Graveyard Keeper checked {target}: {role} ({camp})",
            "blood_moon_transformed": "🌑 Blood Moon Apostle {player} has transformed and joined the wolf pack.",
            "werewolf_no_votes": "🐺 狼人未投票，第 {round_number} 轮无刀口",
            "werewolf_wake_opening": "狼人请睁眼。可选刀口目标：{targets}。请与队友讨论今晚击杀目标。",
            "death_skill_context": "你（{player}）已死亡，可以带走一名玩家。",
            "sheriff_transfer_note": "你可以选择将警徽移交给任意存活玩家，或选择撕毁警徽。",
            "sheriff_transfer_targets": "可选移交目标：{targets}",
            # 骑士决斗
            "knight_duel_begin": "⚔️ 骑士 {knight} 发动决斗！",
            "knight_duel_wolf": "⚔️ 骑士 {knight} 与 {target} 决斗，{target} 是狼人，{target} 死亡！",
            "knight_duel_good": "⚔️ 骑士 {knight} 与 {target} 决斗，{target} 不是狼人，{knight} 死亡！",
            "knight_duel_failed": "⚔️ 骑士 {knight} 对 {target} 的决斗无效",
            "vote_instruction": "请仔细分析局势，投出你认为最可疑的玩家。",
            "vote_prompt": "请投票选择你想淘汰的玩家",
            "vote_tie_pk_announce": "投票出现平票，{candidates} 得票相同。进入 PK 发言环节。",
            "vote_tie_no_elimination": "投票再次平票，{candidates} 得票相同。本轮无人淘汰。",
            "pk_speech_begin": "进入 PK 发言环节，请 {candidates} 依次发言。",
            "pk_speech_opening": "请 {candidates} 依次发表 PK 发言。",
            "pk_speech_instruction": "Please give a brief PK speech to win other players' support.",
            "voting_phase_separator": "Entering voting phase.",
            "night_death_announce": "{player} died last night.",
            "peaceful_night": "It was a peaceful night. No one died.",
            "discussion_phase_separator": "Day discussion phase.",
            "day_discussion_instruction": "Please analyze the current situation and share your thoughts.",
            "daybreak_announcement": "Day breaks. {death_lines}. Please share your thoughts.",
            "peaceful_night_announcement": "Day breaks, it was a peaceful night. Please share your thoughts.",
            "night_death_line": "{player} died last night",
            "sheriff_ask_run": "Would you like to run for sheriff?",
            "sheriff_campaign_note": "Running for sheriff requires the trust of most players. Consider your role and strategy.",
            "sheriff_speech_instruction": "Please give your campaign speech to win players' votes.",
            "sheriff_other_candidates": "Other candidates: {others}",
            "sheriff_vote_action": "Please vote for the sheriff candidate you support",
            "sheriff_vote_note": "Please carefully consider each candidate's speech and performance.",
            "sheriff_tie_pk": "Sheriff election tied, {candidates} have the same votes. Entering PK speech phase.",
            "sheriff_tie_fallback": "Not enough PK candidates. Sheriff election ends.",
            "sheriff_badge_lost": "Sheriff election tied again, {candidates} have the same votes. Badge is lost, no sheriff this game.",
            "pk_speeches_start": "{count} candidates will give PK speeches.",
            "pk_opponents": "Your PK opponents: {opponents}",
            # 配置
            "config_loaded": "Loaded configuration: {config_path}",
            "player_count_info": "Number of players: {num_players}",
            "interface_mode": "Interface mode: Console (auto-execute)",
        },
        "zh-TW": {
            # 阶段切换
            "night_begins": "第 {round_number} 輪黑夜開始",
            "day_begins": "第 {round_number} 輪白天開始",
            "voting_phase": "投票階段",
            "game_started": "遊戲開始，共有 {player_count} 位玩家",
            "game_ended": "遊戲結束。{winner} 獲勝!{reason}",
            "game_over": "\n遊戲結束!{winner} 陣營獲勝!",
            # 阶段分隔线
            "phase_separator": "=" * 60,
            "night_separator": "🌙 " + "=" * 56 + " 🌙",
            "day_separator": "☀️  " + "=" * 56 + " ☀️",
            # 玩家状态
            "alive_players": "\n存活玩家: ",
            "dead_players": "\n淘汰玩家: ",
            "player_role_info": "- {name}({role})",
            # 死亡
            "player_died": "{player} 死亡",
            "killed_by_werewolves": "{player} 被狼人殺害",
            "voted_out": "{player} 被投票淘汰",
            "player_eliminated": "{player} 被投票淘汰，身分是 {role}。",
            "player_eliminated_hidden": "{player} 被投票淘汰。",
            "werewolf_vote_tie_break": "狼刀平票，由 {breaker} 裁定最终刀口。",
            "died_of_heartbreak": "{player} 因愛而死(戀人)!",
            "died_from_charm": "{player} 被狼美人魅惑而死(狼美人 {wolf_beauty} 被淘汰)!",
            # 投票
            "vote_cast": "🗳️ {voter} 投票給 {target}",
            "vote_summary": "\n📊 投票統計: ",
            "vote_count": "  {target}: {count} 票 - {voters}",
            "vote_tied": "投票平手，無人被淘汰。",
            "no_votes": "無人投票。",
            # 主持人播报
            "narrator_night_falls": "🌙 天黑請閉眼...",
            "narrator_werewolves_wake": "🐺 狼人請睜眼，請討論並選擇目標...",
            "narrator_werewolves_vote": "🐺 狼人請投票...",
            "narrator_werewolves_sleep": "🐺 狼人請閉眼...",
            "narrator_daybreak": "☀️ 天亮了，所有人請睜眼...",
            # 角色行动
            "role_acting": "🎬 {role}({player})正在行動...",
            "player_speech": "{player}: {speech}",
            "werewolf_discussion": "🐺 {player}(狼人): {speech}",
            "werewolf_voting": "🐺 狼人正在討論目標...",
            "werewolf_target": "🐺 狼人選擇了 {target}",
            "werewolf_vote_tally": "🐺 狼隊票型已統計（刀口：{target}）",
            "seer_checked_public": "🔮 預言家查驗了 {target}",
            "witch_saved": "💊 女巫救了 {target}",
            "witch_poisoned": "☠️ 女巫毒殺了 {target}",
            "guard_protected": "🛡️ 守衛保護了 {target}",
            "seer_checked": "🔮 預言家查驗了 {target}: {result}",
            "hunter_shoots": "🏹 獵人 {hunter} 射殺了 {target}",
            "alpha_wolf_shoots": "🐺👑 狼王 {alpha} 帶走了 {target}",
            "white_wolf_shoots": "🐺⚪ 白狼王 {white_wolf} 帶走了 {target}",
            "white_wolf_self_explodes": "🐺⚪ 白狼王 {player} 自爆",
            "lovers_linked": "💕 戀人連結: {player1} 和 {player2}",
            "white_wolf_kills": "🐺⚪ 白狼王殺了 {target}",
            "wolf_beauty_charms": "🐺💋 狼美人魅惑了 {target}",
            "cupid_links": "💘 丘比特將 {player1} 和 {player2} 連結為戀人",
            # 特殊情况
            "idiot_revealed": "{player} 揭示自己是白癡，倖免於難!",
            "elder_executed": "長老被村民處決了!所有村民失去特殊能力作為懲罰!",
            "elder_attacked": "{player} 被攻擊但倖存(長老)!",
            "protected_by_guard": "{player} 被守衛保護了!",
            "saved_by_witch": "{player} 被女巫救了!",
            "poisoned_no_ability": "{player} 被女巫毒殺，無法使用死亡技能。",
            "death_ability_active": "{player}({role})可以在死前射殺一人!",
            # 警长选举
            "sheriff_campaign_started": "警長選舉開始，玩家可以自願競選警長。",
            "no_candidates": "沒有人自願競選警長，本局沒有警長。",
            "player_volunteers": "{player} 自願競選警長。",
            "sheriff_single_candidate": "僅有 {player} 競選警長，無需投票。",
            "campaign_speeches_start": "{count} 位候選人將發表競選演說。",
            "candidate_speech": "{candidate} 的演說: {speech}",
            "no_voters": "沒有非候選人可以投票，所有玩家都是候選人。",
            "sheriff_voting_start": "{count} 位非候選人將投票選舉警長。",
            "sheriff_vote_cast": "{voter} 投票給 {candidate}。",
            "sheriff_vote_abstained": "{voter} 棄權。",
            "sheriff_vote_result": "{candidate} 得到 {votes} 票。",
            "sheriff_tie": "{candidates} 平手，本局沒有警長。",
            "sheriff_elected": "{player} 當選警長!",
            # 警徽移交
            "sheriff_died_transfer": "警長 {sheriff} 已死亡，可以選擇移交或撕毀警徽。",
            "sheriff_badge_torn": "{sheriff} 撕毀了警徽，不再有警長。",
            "sheriff_badge_transferred": "{sheriff} 將警徽移交給 {target}。",
            # 其他技能
            "elder_penalty": "長老被處決，所有村民失去特殊能力",
            "nightmare_blocked": "{player}({role})被夢魘狼封印",
            "witch_uses_poison": "🧪 女巫對 {target} 使用毒藥",
            "witch_poisoned_target": "{target} 被女巫毒殺",
            # 错误消息
            "speech_failed": "{player}: [發言失敗 - {error}]",
            "discussion_failed": "{player}: [討論失敗 - {error}]",
            "night_action_failed": "{role}({player}): [夜間行動失敗 - {error}]",
            "action_failed": "{role}({player}): [行動失敗 - {error}]",
            "action_rejected": "{role}({player}): [行動未通過校驗 - {action}]",
            "vote_failed": "{player}: [投票失敗 - {error}]",
            "guardian_wolf_protected": "🐺🛡️ 守墓狼保護了 {target}",
            "raven_marks": "🐦‍⬛ 烏鴉標記了 {target}",
            "graveyard_keeper_checked": "⚰️ 守墓人查驗 {target}：{role}（{camp}）",
            "blood_moon_transformed": "🌑 血月使徒 {player} 已變身為狼人，加入狼隊。",
            "werewolf_no_votes": "🐺 狼人未投票，第 {round_number} 輪無刀口",
            "werewolf_wake_opening": "狼人請睜眼。可選刀口目標：{targets}。請與隊友討論今晚擊殺目標。",
            "death_skill_context": "你（{player}）已死亡，可以帶走一名玩家。",
            "sheriff_transfer_note": "你可以選擇將警徽移交給任意存活玩家，或選擇撕毀警徽。",
            "sheriff_transfer_targets": "可選移交目標：{targets}",
            # 騎士決鬥
            "knight_duel_begin": "⚔️ 騎士 {knight} 發動決鬥！",
            "knight_duel_wolf": "⚔️ 騎士 {knight} 與 {target} 決鬥，{target} 是狼人，{target} 死亡！",
            "knight_duel_good": "⚔️ 騎士 {knight} 與 {target} 決鬥，{target} 不是狼人，{knight} 死亡！",
            "knight_duel_failed": "⚔️ 騎士 {knight} 對 {target} 的決鬥無效",
            "vote_instruction": "請仔細分析局勢，投出你認為最可疑的玩家。",
            "vote_prompt": "請投票選擇你想淘汰的玩家",
            "vote_tie_pk_announce": "投票出現平票，{candidates} 得票相同。進入 PK 發言環節。",
            "vote_tie_no_elimination": "投票再次平票，{candidates} 得票相同。本輪無人淘汰。",
            "pk_speech_begin": "進入 PK 發言環節，請 {candidates} 依次發言。",
            "pk_speech_opening": "請 {candidates} 依次發表 PK 發言。",
            "pk_speech_instruction": "請進行簡短的 PK 發言，爭取其他玩家對你的支持。",
            "voting_phase_separator": "進入投票階段。",
            "night_death_announce": "{player} 在昨夜死亡。",
            "peaceful_night": "昨夜平安夜。",
            "discussion_phase_separator": "白天討論階段。",
            "day_discussion_instruction": "請仔細分析當前局勢，發表你的觀點。",
            "daybreak_announcement": "天亮了。{death_lines}。請依次發表白天討論發言。",
            "peaceful_night_announcement": "天亮了，昨夜平安夜。請依次發表白天討論發言。",
            "night_death_line": "{player} 在昨夜死亡",
            "sheriff_ask_run": "你是否願意競選警長？",
            "sheriff_campaign_note": "競選警長需要獲得多數玩家的信任。請考慮你的角色和策略。",
            "sheriff_speech_instruction": "請發表競選演說，爭取玩家的投票。",
            "sheriff_other_candidates": "其他候選人：{others}",
            "sheriff_vote_action": "請投票選擇你想支持的警長候選人",
            "sheriff_vote_note": "請仔細考慮每位候選人的發言和表現。",
            "sheriff_tie_pk": "警長選舉出現平票，{candidates} 得票相同。進入 PK 發言環節。",
            "sheriff_tie_fallback": "PK 環節候選人不足，警長選舉結束。",
            "sheriff_badge_lost": "警長選舉再次平票，{candidates} 得票相同。警徽流失，本局沒有警長。",
            "pk_speeches_start": "{count} 位候選人將發表 PK 發言。",
            "pk_opponents": "你的 PK 對手：{opponents}",
            # 配置
            "config_loaded": "已載入設定檔: {config_path}",
            "player_count_info": "玩家人數: {num_players}",
            "interface_mode": "介面模式: Console(自動執行)",
        },
        "zh-CN": {
            # 阶段切换
            "night_begins": "第 {round_number} 轮黑夜开始",
            "day_begins": "第 {round_number} 轮白天开始",
            "voting_phase": "投票阶段",
            "game_started": "游戏开始，共有 {player_count} 位玩家",
            "game_ended": "游戏结束。{winner} 获胜!{reason}",
            "game_over": "\n游戏结束!{winner} 阵营获胜!",
            # 阶段分隔线
            "phase_separator": "=" * 60,
            "night_separator": "🌙 " + "=" * 56 + " 🌙",
            "day_separator": "☀️  " + "=" * 56 + " ☀️",
            # 玩家状态
            "alive_players": "\n存活玩家: ",
            "dead_players": "\n淘汰玩家: ",
            "player_role_info": "- {name}({role})",
            # 死亡
            "player_died": "{player} 死亡",
            "killed_by_werewolves": "{player} 被狼人杀害",
            "voted_out": "{player} 被投票淘汰",
            "player_eliminated": "{player} 被投票淘汰，身份是 {role}。",
            "player_eliminated_hidden": "{player} 被投票淘汰。",
            "werewolf_vote_tie_break": "狼刀平票，由 {breaker} 裁定最终刀口。",
            "died_of_heartbreak": "{player} 因爱而死(恋人)!",
            "died_from_charm": "{player} 被狼美人魅惑而死(狼美人 {wolf_beauty} 被淘汰)!",
            # 投票
            "vote_cast": "🗳️ {voter} 投票给 {target}",
            "vote_summary": "\n📊 投票统计: ",
            "vote_count": "  {target}: {count} 票 - {voters}",
            "vote_tied": "投票平手，无人被淘汰。",
            "no_votes": "无人投票。",
            # 主持人播报
            "narrator_night_falls": "🌙 天黑请闭眼...",
            "narrator_werewolves_wake": "🐺 狼人请睁眼，请讨论并选择目标...",
            "narrator_werewolves_vote": "🐺 狼人请投票...",
            "narrator_werewolves_sleep": "🐺 狼人请闭眼...",
            "narrator_daybreak": "☀️ 天亮了，所有人请睁眼...",
            # 角色行动
            "role_acting": "🎬 {role}({player})正在行动...",
            "player_speech": "{player}: {speech}",
            "werewolf_discussion": "🐺 {player}(狼人): {speech}",
            "werewolf_voting": "🐺 狼人正在讨论目标...",
            "werewolf_target": "🐺 狼人选择了 {target}",
            "werewolf_vote_tally": "🐺 狼队票型已统计（刀口：{target}）",
            "seer_checked_public": "🔮 预言家查验了 {target}",
            "witch_saved": "💊 女巫救了 {target}",
            "witch_poisoned": "☠️ 女巫毒杀了 {target}",
            "guard_protected": "🛡️ 守卫保护了 {target}",
            "seer_checked": "🔮 预言家查验了 {target}: {result}",
            "hunter_shoots": "🏹 猎人 {hunter} 射杀了 {target}",
            "alpha_wolf_shoots": "🐺👑 狼王 {alpha} 带走了 {target}",
            "white_wolf_shoots": "🐺⚪ 白狼王 {white_wolf} 带走了 {target}",
            "white_wolf_self_explodes": "🐺⚪ 白狼王 {player} 自爆",
            "lovers_linked": "💕 恋人连结: {player1} 和 {player2}",
            "white_wolf_kills": "🐺⚪ 白狼王杀了 {target}",
            "wolf_beauty_charms": "🐺💋 狼美人魅惑了 {target}",
            "cupid_links": "💘 丘比特将 {player1} 和 {player2} 连结为恋人",
            # 特殊情况
            "idiot_revealed": "{player} 揭示自己是白痴，幸免于难!",
            "elder_executed": "长老被村民处决了!所有村民失去特殊能力作为惩罚!",
            "elder_attacked": "{player} 被攻击但幸存(长老)!",
            "protected_by_guard": "{player} 被守卫保护了!",
            "saved_by_witch": "{player} 被女巫救了!",
            "poisoned_no_ability": "{player} 被女巫毒杀，无法使用死亡技能。",
            "death_ability_active": "{player}({role})可以在死前射杀一人!",
            # 警长选举
            "sheriff_campaign_started": "警长选举开始，玩家可以自愿竞选警长。",
            "no_candidates": "没有人自愿竞选警长，本局没有警长。",
            "player_volunteers": "{player} 自愿竞选警长。",
            "sheriff_single_candidate": "仅有 {player} 竞选警长，无需投票。",
            "campaign_speeches_start": "{count} 位候选人将发表竞选演说。",
            "candidate_speech": "{candidate} 的演说: {speech}",
            "no_voters": "没有非候选人可以投票，所有玩家都是候选人。",
            "sheriff_voting_start": "{count} 位非候选人将投票选举警长。",
            "sheriff_vote_cast": "{voter} 投票给 {candidate}。",
            "sheriff_vote_abstained": "{voter} 弃权。",
            "sheriff_vote_result": "{candidate} 得到 {votes} 票。",
            "sheriff_tie": "{candidates} 平手，本局没有警长。",
            "sheriff_elected": "{player} 当选警长!",
            # 警徽移交
            "sheriff_died_transfer": "警长 {sheriff} 已死亡，可以选择移交或撕毁警徽。",
            "sheriff_badge_torn": "{sheriff} 撕毁了警徽，不再有警长。",
            "sheriff_badge_transferred": "{sheriff} 将警徽移交给 {target}。",
            # 其他技能
            "elder_penalty": "长老被处决，所有村民失去特殊能力",
            "nightmare_blocked": "{player}({role})被梦魇狼封印",
            "witch_uses_poison": "🧪 女巫对 {target} 使用毒药",
            "witch_poisoned_target": "{target} 被女巫毒杀",
            # 错误消息
            "speech_failed": "{player}: [发言失败 - {error}]",
            "discussion_failed": "{player}: [讨论失败 - {error}]",
            "night_action_failed": "{role}({player}): [夜间行动失败 - {error}]",
            "action_failed": "{role}({player}): [行动失败 - {error}]",
            "action_rejected": "{role}({player}): [行动校验未通过 - {action}]",
            "vote_failed": "{player}: [投票失败 - {error}]",
            "guardian_wolf_protected": "🐺🛡️ 守墓狼保护了 {target}",
            "raven_marks": "🐦‍⬛ 乌鸦标记了 {target}",
            "graveyard_keeper_checked": "⚰️ 守墓人查验 {target}：{role}（{camp}）",
            "blood_moon_transformed": "🌑 血月使徒 {player} 已变身为狼人，加入狼队。",
            "werewolf_no_votes": "🐺 狼人未投票，第 {round_number} 轮无刀口",
            "werewolf_wake_opening": "狼人请睁眼。可选刀口目标：{targets}。请与队友讨论今晚击杀目标。",
            "death_skill_context": "你（{player}）已死亡，可以带走一名玩家。",
            "sheriff_transfer_note": "你可以选择将警徽移交给任意存活玩家，或选择撕毁警徽。",
            "sheriff_transfer_targets": "可选移交目标：{targets}",
            # 骑士决斗
            "knight_duel_begin": "⚔️ 骑士 {knight} 发动决斗！",
            "knight_duel_wolf": "⚔️ 骑士 {knight} 与 {target} 决斗，{target} 是狼人，{target} 死亡！",
            "knight_duel_good": "⚔️ 骑士 {knight} 与 {target} 决斗，{target} 不是狼人，{knight} 死亡！",
            "knight_duel_failed": "⚔️ 骑士 {knight} 对 {target} 的决斗无效",
            "vote_instruction": "请仔细分析局势，投出你认为最可疑的玩家。",
            "vote_prompt": "请投票选择你想淘汰的玩家",
            "vote_tie_pk_announce": "投票出现平票，{candidates} 得票相同。进入 PK 发言环节。",
            "vote_tie_no_elimination": "投票再次平票，{candidates} 得票相同。本轮无人淘汰。",
            "pk_speech_begin": "进入 PK 发言环节，请 {candidates} 依次发言。",
            "pk_speech_opening": "请 {candidates} 依次发表 PK 发言。",
            "pk_speech_instruction": "请进行简短的 PK 发言，争取其他玩家对你的支持。",
            "voting_phase_separator": "进入投票阶段。",
            "night_death_announce": "{player} 在昨夜死亡。",
            "peaceful_night": "昨夜平安夜。",
            "discussion_phase_separator": "白天讨论阶段。",
            "day_discussion_instruction": "请仔细分析当前局势，发表你的观点。",
            "daybreak_announcement": "天亮了。{death_lines}。请依次发表白天讨论发言。",
            "peaceful_night_announcement": "天亮了，昨夜平安夜。请依次发表白天讨论发言。",
            "night_death_line": "{player} 在昨夜死亡",
            "sheriff_ask_run": "你是否愿意竞选警长？",
            "sheriff_campaign_note": "竞选警长需要获得多数玩家的信任。请考虑你的角色和策略。",
            "sheriff_speech_instruction": "请发表竞选演说，争取玩家的投票。",
            "sheriff_other_candidates": "其他候选人：{others}",
            "sheriff_vote_action": "请投票选择你想支持的警长候选人",
            "sheriff_vote_note": "请仔细考虑每位候选人的发言和表现。",
            "sheriff_tie_pk": "警长选举出现平票，{candidates} 得票相同。进入 PK 发言环节。",
            "sheriff_tie_fallback": "PK 环节候选人不足，警长选举结束。",
            "sheriff_badge_lost": "警长选举再次平票，{candidates} 得票相同。警徽流失，本局没有警长。",
            "pk_speeches_start": "{count} 位候选人将发表 PK 发言。",
            "pk_opponents": "你的 PK 对手：{opponents}",
            # 配置
            "config_loaded": "已加载配置文件: {config_path}",
            "player_count_info": "玩家人数: {num_players}",
            "interface_mode": "界面模式: Console(自动执行)",
        },
    }

    def __init__(self, language: str = "en-US") -> None:
        """使用指定语言初始化本地化。

        Args:
            language: 语言代码（en-US、zh-TW、zh-CN）。
        """
        if language not in self.MESSAGES:
            # 不支持的语言时回退到英语
            language = "en-US"
        self.language = language
        self.messages = self.MESSAGES[language]

    def get(self, key: str, **kwargs: str | int) -> str:
        """获取本地化消息，可选格式化。

        Args:
            key: 消息键。
            **kwargs: 消息的格式化参数。

        Returns:
            str: 格式化后的本地化消息。
        """
        template = self.messages.get(key, key)
        if kwargs:
            try:
                return template.format(**kwargs)
            except KeyError:
                # 格式化失败时原样返回模板
                return template
        return template

    def set_language(self, language: str) -> None:
        """切换当前语言。

        Args:
            language: 语言代码（en-US、zh-TW、zh-CN）。
        """
        if language in self.MESSAGES:
            self.language = language
            self.messages = self.MESSAGES[language]
