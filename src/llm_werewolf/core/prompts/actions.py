"""Chinese action descriptions for engine and role action prompts."""


class ActionDescriptions:
    """Structured action text passed to ``ActionSelector`` / ``PromptManager``."""

    VOTE_KILL = "今晚投票击杀一名玩家"
    VOTE_KILL_ALPHA = "选择一名狼人队友击杀（或跳过）"
    VOTE_KILL_TRANSFORMED = "你已变为狼人，请选择今晚击杀目标"
    CHARM_PLAYER = "选择一名玩家魅惑"
    PROTECT_WOLF = "选择一名狼人队友保护"
    BLOCK_PLAYER = "选择一名玩家封锁其技能"
    CHECK_PLAYER = "今晚查验一名玩家的身份"
    USE_POISON = "选择一名玩家毒杀（或跳过）"
    PROTECT_PLAYER = "今晚守护一名玩家"
    LOVERS = "选择两名玩家结为情侣"
    CURSE_PLAYER = "选择一名玩家施加诅咒"
    CHECK_DEAD = "选择一名已死亡玩家查验身份"
    VOTE_ELIMINATE = "投票放逐一名玩家"
    VOTE_SHERIFF = "投票选举警长"
    TRANSFER_BADGE = "选择继承警徽的玩家（或撕毁警徽）"
    SHOOT_ON_DEATH = "临死前选择带走的玩家"


class EngineContexts:
    """Chinese free-form context fragments for phase discussions."""

    @staticmethod
    def werewolf_coordination_note(werewolf_names: list[str], target_names: list[str]) -> list[str]:
        return [
            f"与你协同的狼人：{', '.join(werewolf_names)}。",
            f"可选目标：{', '.join(target_names)}。",
        ]

    @staticmethod
    def werewolf_discussion(
        player_name: str,
        round_number: int,
        werewolf_names: list[str],
        target_names: list[str],
        history: str = "",
    ) -> str:
        parts = [
            f"你是 {player_name}，身份为狼人。",
            f"当前：第 {round_number} 轮 · 夜晚",
            f"与你协同的狼人：{', '.join(werewolf_names)}。",
            f"可选目标：{', '.join(target_names)}。",
        ]
        if history:
            parts.append(history)
        parts.extend([
            "",
            "与狼队友讨论今晚要淘汰谁，简要说明理由（1-2 句）。",
            "公开发言写入 SpeechDecision.public_speech；推理写入 private_thought。",
            "谁能听到由系统根据狼队频道分发，无需你指定听众。",
        ])
        return "\n".join(parts)

    @staticmethod
    def day_discussion_prompt() -> str:
        return (
            "分享你的看法、怀疑或掌握的信息（1-3 句）。"
            "公开发言写入 SpeechDecision.public_speech；推理写入 private_thought。"
            "谁能听到由系统根据白天公开频道分发，无需你指定听众。"
        )

    @staticmethod
    def hub_roundtable_memory_notice(channel: str) -> str:
        """Tell the model that in-round dialogue lives in MsgHub memory, not the event block."""
        audience = "所有存活玩家" if channel == "public" else "狼队队友"
        return "\n".join([
            "【对话记忆 · MsgHub】",
            f"本轮已在对话中出现的公开发言由系统注入你的历史（{audience}可见），请据此接话。",
            "下方「可见事件」仅为局面变化记录（死亡、阶段等），不含玩家发言文本。",
        ])

    @staticmethod
    def hub_decision_memory_notice() -> str:
        """Remind the model that speeches/discussion live in ReAct/MsgHub history, not Event log."""
        return "\n".join([
            "【决策上下文 · MsgHub】",
            "玩家发言、狼队夜聊、警上发言等对话内容在你上方的对话记忆中。",
            "下方「可见事件」仅记录局面变化（死亡、平安夜、阶段切换等），不含发言全文。",
            "做投票或夜间决策时请优先依据对话记忆，不要等待事件里重复的发言。",
        ])

    @staticmethod
    def sheriff_run(player_name: str, role_name: str, round_number: int) -> str:
        return (
            f"你是 {player_name}，身份为 {role_name}。\n"
            f"当前：第 {round_number} 轮 · 警长竞选\n"
            "是否参加警长竞选？回复 [[1]] 参加，[[0]] 不参加。"
        )

    @staticmethod
    def sheriff_speech(
        player_name: str,
        role_name: str,
        round_number: int,
        num_candidates: int,
    ) -> str:
        return (
            f"你是 {player_name}，身份为 {role_name}。\n"
            f"当前：第 {round_number} 轮 · 警长竞选发言\n"
            f"你是 {num_candidates} 名候选人之一。\n"
            "请发表竞选发言（1-3 句），内容放在 [[]] 中。"
        )

    @staticmethod
    def sheriff_vote_intro(
        player_name: str,
        role_name: str,
        round_number: int,
        candidate_names: list[str],
    ) -> str:
        return (
            f"你是 {player_name}，身份为 {role_name}。\n"
            f"当前：第 {round_number} 轮 · 警长投票\n"
            f"候选人：{', '.join(candidate_names)}。\n"
            "请投票选出你认为合适的警长。"
        )

    @staticmethod
    def sheriff_died(sheriff_name: str) -> str:
        return f"你是警长 {sheriff_name}，你已死亡，请处理警徽。"
