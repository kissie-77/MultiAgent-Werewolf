"""Coordinates working, episodic, semantic, and procedural memory."""

from __future__ import annotations

from typing import Any

from llm_werewolf.agent_team.memory.base import SemanticBackend
from llm_werewolf.agent_team.memory.config import MemoryConfig
from llm_werewolf.agent_team.memory.episodic_memory import EpisodicMemory, _KEY_EVENT_TYPES
from llm_werewolf.agent_team.memory.llm_compressor import LLMCompressor
from llm_werewolf.agent_team.memory.procedural_memory import ProceduralMemory
from llm_werewolf.agent_team.memory.semantic_memory import SemanticMemory
from llm_werewolf.agent_team.memory.working_memory import WorkingMemory
from llm_werewolf.game_runtime.roles.registry import get_werewolf_roles


class MemoryManager:
    """Unified lifecycle manager for all memory layers."""

    def __init__(
        self,
        event_logger,
        role: str = "",
        player_id: str = "",
        plan_name: str = "default",
        config: MemoryConfig | None = None,
        semantic_backend: SemanticBackend | None = None,
        compressor: object | None = None,
    ):
        self.config = config or MemoryConfig()
        self.player_id = player_id
        self.role = role
        self.plan_name = plan_name
        self._llm_compressor = compressor

        self.working = WorkingMemory(
            max_rounds=self.config.working_max_rounds,
            max_dynamic_items=self.config.working_max_dynamic_items,
            max_persistent_chars=self.config.working_max_persistent_chars,
            compressor=compressor,
        )
        self.episodic = EpisodicMemory(event_logger)
        self.procedural = ProceduralMemory()
        self.semantic = SemanticMemory(backend=semantic_backend, compressor=compressor)
        self._used_card_ids: list[str] = []
        self._seen_event_keys: set[tuple[object, ...]] = set()

    async def aclose(self) -> None:
        """Compatibility hook for optional async resources."""
        return None

    def on_game_start(self, role: str) -> None:
        """Inject role skills and procedural summaries at game start."""
        self.role = role
        self._used_card_ids = []
        self._seen_event_keys = set()
        if not self._prompt_context_enabled():
            return
        if self._semantic_enabled():
            self._inject_semantic_context(role)
        plan_summary = self.procedural.build_plan_summary(self.plan_name, role)
        self.working.add_persistent(f"[程序记忆] {plan_summary}", tag="procedural")

    def on_round_end(self, round_number: int) -> None:
        """Compress working memory at round end."""
        del round_number
        if not self._prompt_context_enabled():
            return
        self.working.end_round()

    def on_game_end(self, won: bool) -> None:
        """Update used skill weights and optionally extract new candidates."""
        if self._semantic_enabled() and self._used_card_ids:
            self.semantic.update_after_game(self.role, won, self._used_card_ids)
        if self._semantic_enabled() and self.config.extract_semantic_on_game_end:
            for candidate in self.extract_semantic_candidates(won):
                self.semantic.add_or_merge_card(self.role, candidate)
        if self._semantic_enabled():
            self.semantic.decay_all(self.role, self._max_cards_for_role(self.role))

    def get_context_for_decision(self) -> str:
        """Return memory context for private decision prompts."""
        if not self._prompt_context_enabled():
            return ""
        parts: list[str] = []
        working_context = self.working.get_context()
        if working_context:
            parts.append(working_context)
        return "\n\n".join(parts)

    def add_public_speech(self, speaker_name: str, speech: str, round_number: int) -> None:
        """Record public speech into working memory."""
        if not self._prompt_context_enabled():
            return
        self.working.add_dynamic(
            f"{speaker_name}发言：{speech}",
            tag="speech",
            round_number=round_number,
        )

    def add_decision(self, decision: str) -> None:
        """Record the agent's own decision into working memory."""
        if not self._prompt_context_enabled():
            return
        self.working.add_dynamic(
            decision,
            tag="decision",
            round_number=self.working.current_round,
        )

    def add_event(self, event: Any) -> None:
        """Record visible key events into working memory."""
        if not self._prompt_context_enabled():
            return
        event_type = getattr(event, "event_type", None)
        message = getattr(event, "message", "")
        if event_type in _KEY_EVENT_TYPES and message:
            event_key = self._event_key(event)
            if event_key in self._seen_event_keys:
                return
            self._seen_event_keys.add(event_key)
            self.working.add_dynamic(
                message,
                tag="event",
                round_number=getattr(event, "round_number", self.working.current_round),
                priority=2,
            )

    def extract_semantic_candidates(self, won: bool) -> list[str]:
        """Rule-based extraction of semantic skill candidates from episodic memory."""
        if not self.player_id or not self._episodic_enabled():
            return []
        report = self.episodic.export_episode_report(self.player_id)
        if self.config.enable_llm_semantic_extraction:
            llm_candidates = self._extract_semantic_candidates_with_llm(report, won)
            if llm_candidates:
                return llm_candidates[: self.config.semantic_top_k]
        return self._extract_semantic_candidates_by_rules(report, won)

    def _prompt_context_enabled(self) -> bool:
        """Whether any memory text may be injected into decision prompts."""
        return self.config.enabled and self.config.enable_working_memory

    def _semantic_enabled(self) -> bool:
        return self.config.enabled and self.config.enable_semantic_memory

    def _episodic_enabled(self) -> bool:
        return self.config.enabled and self.config.enable_episodic_memory

    def _inject_semantic_context(self, role: str) -> None:
        for card in self.semantic.retrieve_for_role(role, top_k=self.config.semantic_top_k):
            description = card.description or self.semantic._extract_description(card.content)
            self.working.add_persistent(f"[经验] {description}", tag="semantic")
            self._used_card_ids.append(card.id)

    def _semantic_llm(self):
        if self._llm_compressor is not None:
            return self._llm_compressor
        if not self.config.working_compression_api_key or not self.config.working_compression_base_url:
            return None
        return LLMCompressor(
            api_key=self.config.working_compression_api_key,
            base_url=self.config.working_compression_base_url,
            model=self.config.working_compression_model,
            timeout=self.config.working_compression_timeout,
        )

    def _max_cards_for_role(self, role: str) -> int:
        if role in get_werewolf_roles() or role in {"wolf", "werewolf", "wolf_king"}:
            return self.config.semantic_max_cards_wolf
        return self.config.semantic_max_cards_good

    @staticmethod
    def _event_key(event: Any) -> tuple[object, ...]:
        data = getattr(event, "data", {})
        if isinstance(data, dict):
            data_key: object = tuple(sorted((str(key), repr(value)) for key, value in data.items()))
        else:
            data_key = repr(data)
        visible_to = getattr(event, "visible_to", None)
        visible_key = tuple(sorted(str(player_id) for player_id in visible_to)) if visible_to else ()
        return (
            str(getattr(event, "event_type", "")),
            getattr(event, "round_number", None),
            str(getattr(event, "phase", "")),
            getattr(event, "message", ""),
            data_key,
            visible_key,
        )

    def _extract_semantic_candidates_with_llm(self, report: dict, won: bool) -> list[str]:
        lines = [
            "请从以下狼人杀对局记录中提炼 1-3 条可复用的策略经验。",
            "每条不超过 50 字，只输出策略经验列表，不要写流水账。",
            f"本局结果：{'胜利' if won else '失败'}",
        ]
        for episode in report.get("episodes", []):
            messages = episode.get("key_event_messages", []) + episode.get("decision_event_messages", [])
            if messages:
                lines.append(f"第{episode.get('round_number')}轮：" + "；".join(messages[:4]))
        compressor = self._semantic_llm()
        if compressor is None:
            return []
        try:
            response = compressor._call_llm_text("\n".join(lines), max_tokens=300)
        except Exception:
            response = ""
        candidates = []
        for raw_line in response.splitlines():
            line = raw_line.strip().lstrip("-*0123456789.、) ")
            if line:
                candidates.append(line[:80])
        return self.semantic.deduplicate_candidates(candidates)

    def _extract_semantic_candidates_by_rules(self, report: dict, won: bool) -> list[str]:
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
