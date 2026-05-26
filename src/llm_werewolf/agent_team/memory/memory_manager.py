"""统一管理工作记忆、情景记忆、语义记忆与程序记忆。"""

from __future__ import annotations

from typing import Any

from llm_werewolf.agent_team.memory.base import SemanticBackend
from llm_werewolf.agent_team.memory.config import MemoryConfig
from llm_werewolf.agent_team.memory.episodic_memory import EpisodicMemory, _KEY_EVENT_TYPES
from llm_werewolf.agent_team.memory.procedural_memory import ProceduralMemory
from llm_werewolf.agent_team.memory.semantic_memory import InMemoryBackend, SemanticMemory
from llm_werewolf.agent_team.memory.working_memory import WorkingMemory


class MemoryManager:
    """记忆统一调度器。"""

    def __init__(
        self,
        event_logger,
        role: str = "",
        player_id: str = "",
        plan_name: str = "default",
        config: MemoryConfig | None = None,
        semantic_backend: SemanticBackend | None = None,
    ):
        self.config = config or MemoryConfig()
        self.player_id = player_id
        self.role = role
        self.plan_name = plan_name

        self._reme_backend = None
        compressor = None

        if semantic_backend is not None:
            pass
        elif self.config.reme_enabled:
            from llm_werewolf.agent_team.memory.reme_backend import LLMCompressor, ReMeSemanticBackend

            self._reme_backend = ReMeSemanticBackend(self.config)
            semantic_backend = self._reme_backend
            if self.config.reme_compress_working_memory:
                compressor = LLMCompressor(self.config)
        else:
            semantic_backend = InMemoryBackend()

        self.working = WorkingMemory(
            max_rounds=self.config.working_max_rounds,
            max_dynamic_items=self.config.working_max_dynamic_items,
            compressor=compressor,
        )
        self.episodic = EpisodicMemory(event_logger)
        self.procedural = ProceduralMemory()
        self.semantic = SemanticMemory(backend=semantic_backend)
        self._used_card_ids: list[str] = []

    async def aclose(self) -> None:
        """释放 ReMe 等异步资源。"""
        if self._reme_backend is not None:
            await self._reme_backend.aclose()

    def on_game_start(self, role: str) -> None:
        """开局注入跨局经验。"""
        self.role = role
        self._used_card_ids = []
        if not self.config.enabled or not self.config.enable_semantic_memory:
            return
        for card in self.semantic.retrieve_for_role(role, top_k=self.config.semantic_top_k):
            self.working.add_persistent(f"[经验] {card.content}", tag="semantic")
            self._used_card_ids.append(card.id)
        plan_summary = self.procedural.build_plan_summary(self.plan_name, role)
        self.working.add_persistent(f"[程序记忆] {plan_summary}", tag="procedural")

    def on_round_end(self, round_number: int) -> None:
        """轮结束时压缩工作记忆。"""
        del round_number
        if not self.config.enabled or not self.config.enable_working_memory:
            return
        self.working.end_round()

    def on_game_end(self, won: bool) -> None:
        """局结束时回写经验卡片权重，并预留情景到语义的提炼口。"""
        if self.config.enabled and self.config.enable_semantic_memory and self._used_card_ids:
            self.semantic.update_after_game(self.role, won, self._used_card_ids)
        if self.config.extract_semantic_on_game_end:
            for candidate in self.extract_semantic_candidates(won):
                self.semantic.add_or_merge_card(self.role, candidate)

    def get_context_for_decision(self) -> str:
        """输出注入私有决策 prompt 的记忆上下文。"""
        if not self.config.enabled:
            return ""
        parts: list[str] = []
        if self.config.enable_working_memory:
            working_context = self.working.get_context()
            if working_context:
                parts.append(working_context)
        if self.config.enable_semantic_memory:
            semantic_context = self.semantic.format_for_prompt(self.role)
            if semantic_context:
                parts.append(semantic_context)
        return "\n\n".join(parts)

    def add_public_speech(self, speaker_name: str, speech: str, round_number: int) -> None:
        """记录本轮公开发言。"""
        if not self.config.enabled or not self.config.enable_working_memory:
            return
        self.working.add_dynamic(
            f"{speaker_name}发言：{speech}",
            tag="speech",
            round_number=round_number,
        )

    def add_event(self, event: Any) -> None:
        """记录当前玩家可见的关键事件。"""
        if not self.config.enabled or not self.config.enable_working_memory:
            return
        event_type = getattr(event, "event_type", None)
        message = getattr(event, "message", "")
        if event_type in _KEY_EVENT_TYPES and message:
            self.working.add_dynamic(
                message,
                tag="event",
                round_number=getattr(event, "round_number", self.working.current_round),
                priority=2,
            )

    def extract_semantic_candidates(self, won: bool) -> list[str]:
        """从情景记忆提炼可沉淀为语义记忆的候选策略。"""
        if not self.player_id or not self.config.enable_episodic_memory:
            return []
        report = self.episodic.export_episode_report(self.player_id)
        candidates: list[str] = []
        for episode in report["episodes"]:
            round_number = episode["round_number"]
            key_messages = episode["key_event_messages"]
            decision_messages = episode["decision_event_messages"]

            if key_messages:
                candidates.append(
                    f"关键局势复盘：第{round_number}轮出现" + "；".join(key_messages[:2])
                )
            if decision_messages:
                candidates.append(
                    f"决策经验：第{round_number}轮重点关注" + "；".join(decision_messages[:2])
                )

            if won and key_messages:
                candidates.append(
                    f"胜利经验：第{round_number}轮保留对"
                    + "；".join(key_messages[:1])
                    + "的持续跟踪"
                )
            if not won and decision_messages:
                candidates.append(
                    f"失败反思：第{round_number}轮不要过早依赖"
                    + "；".join(decision_messages[:1])
                    + "形成判断"
                )

        merged = self.semantic.merge_reflections(self.semantic.deduplicate_candidates(candidates))
        return merged[: self.config.semantic_top_k]
