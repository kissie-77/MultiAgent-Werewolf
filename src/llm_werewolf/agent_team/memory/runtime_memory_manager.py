"""Coordinates working, episodic, semantic, and procedural memory."""

from __future__ import annotations

from typing import Any

from llm_werewolf.agent_team.memory.base import CompressorProtocol, SemanticBackend
from llm_werewolf.agent_team.memory.config import MemoryConfig
from llm_werewolf.agent_team.memory.episodic_memory import EpisodicMemory, KEY_EVENT_TYPES
from llm_werewolf.agent_team.memory.llm_compressor import LLMCompressor
from llm_werewolf.agent_team.memory.procedural_memory import ProceduralMemory
from llm_werewolf.agent_team.memory.semantic_memory import SemanticMemory
from llm_werewolf.agent_team.memory.working_memory import WorkingMemory
from llm_werewolf.agent_team.skill_support.skill_markdown import extract_description
from llm_werewolf.game_runtime.roles.registry import get_werewolf_roles


class RuntimeMemoryManager:
    """Unified lifecycle manager for all memory layers."""

    def __init__(
        self,
        event_logger,
        role: str = "",
        player_id: str = "",
        plan_name: str = "default",
        config: MemoryConfig | None = None,
        semantic_backend: SemanticBackend | None = None,
        compressor: CompressorProtocol | None = None,
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
        self.coach = None
        self._used_card_ids: list[str] = []
        self._seen_event_keys: set[tuple[object, ...]] = set()
        self._belief_rules_initialized = False

    async def aclose(self) -> None:
        """Compatibility hook for optional async resources."""
        return None

    def on_game_start(self, role: str, *, role_counts: dict[str, int] | None = None) -> None:
        """Inject role skills and procedural summaries at game start."""
        self.role = role
        self._used_card_ids = []
        self._seen_event_keys = set()
        if not self._prompt_context_enabled():
            return
        if role_counts:
            from llm_werewolf.game_runtime.prompts.actions import EngineContexts

            self.working.upsert_persistent(
                EngineContexts.role_pool_note(role_counts),
                tag="role_pool",
                priority=8,
            )
        if self._semantic_enabled():
            self._inject_semantic_context(role)
            self._record_prompt_injected_skills(role)
        plan_summary = self.procedural.build_plan_summary(self.plan_name, role)
        self.working.add_persistent(f"[程序记忆] {plan_summary}", tag="procedural")

    def on_round_end(self, round_number: int) -> None:
        """Compress working memory at round end."""
        del round_number
        if not self._prompt_context_enabled():
            return
        self.working.end_round()

    def on_game_end(self, won: bool) -> None:
        """Update used skills and let Coach own experience extraction."""
        if self._semantic_enabled() and self._used_card_ids:
            self.semantic.update_after_game(self.role, won, self._used_card_ids)
        if self._semantic_enabled() and self.config.extract_semantic_on_game_end:
            for candidate in self.extract_semantic_candidates(won):
                self.semantic.add_or_merge_card(self.role, candidate)
        if self._semantic_enabled():
            self.semantic.evict_excess(self.role, self._max_cards_for_role(self.role))

    def get_context_for_decision(self, *, include_belief: bool = True) -> str:
        """Return memory context for private decision prompts."""
        if not self._prompt_context_enabled():
            return ""
        parts: list[str] = []
        working_context = self.working.get_context(include_belief=include_belief)
        if working_context:
            parts.append(working_context)
        return "\n\n".join(parts)

    def sync_belief_context(self, state: object, *, wolf_camp_text: str = "") -> None:
        """Mirror belief matrix / vote intention into protected WorkingMemory slots."""
        if not self._prompt_context_enabled():
            return
        from llm_werewolf.agent_team.memory.working_memory import (
            BELIEF_PERSISTENT_PRIORITY,
            _BELIEF_RULES_TEXT,
        )
        from llm_werewolf.strategy.belief_format import format_belief_context

        if not self._belief_rules_initialized:
            self.working.upsert_persistent(
                _BELIEF_RULES_TEXT,
                tag="belief_rules",
                priority=BELIEF_PERSISTENT_PRIORITY,
            )
            self._belief_rules_initialized = True

        belief_text = format_belief_context(state)  # type: ignore[arg-type]
        if belief_text:
            self.working.upsert_persistent(
                belief_text,
                tag="belief",
                priority=BELIEF_PERSISTENT_PRIORITY,
            )
        else:
            self.working.remove_persistent("belief")

        if wolf_camp_text.strip():
            self.working.upsert_persistent(
                wolf_camp_text.strip(),
                tag="wolf_camp",
                priority=BELIEF_PERSISTENT_PRIORITY,
            )
        else:
            self.working.remove_persistent("wolf_camp")

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
        if event_type in KEY_EVENT_TYPES and message:
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
        """Delegate runtime semantic extraction to Coach."""
        if not self.player_id or not self._episodic_enabled():
            return []
        report = self.episodic.export_episode_report(self.player_id)
        return self._coach().extract_semantic_candidates(
            report,
            won=won,
            semantic=self.semantic,
            top_k=self.config.semantic_top_k,
            enable_llm_extraction=self.config.enable_llm_semantic_extraction,
            compressor=self._semantic_llm(),
        )

    def _prompt_context_enabled(self) -> bool:
        return self.config.enabled and self.config.enable_working_memory

    def _semantic_enabled(self) -> bool:
        return self.config.enabled and self.config.enable_semantic_memory

    def _episodic_enabled(self) -> bool:
        return self.config.enabled and self.config.enable_episodic_memory

    def _inject_semantic_context(self, role: str) -> None:
        # Shared Skill markdown is injected via sys_prompt; only backend cards enter working memory here.
        if self.semantic._backend is None:
            return
        for card in self.semantic.retrieve_for_role(role, top_k=self.config.semantic_top_k):
            description = card.description or extract_description(card.content)
            self.working.add_persistent(f"[经验] {description}", tag="semantic")
            self._used_card_ids.append(card.id)

    def _record_prompt_injected_skills(self, role: str) -> None:
        """Track active sys_prompt skills so post-game weight updates can still apply."""
        if self.semantic._backend is not None:
            return
        from llm_werewolf.agent_team.skill_support import skill_loader

        for skill in skill_loader.load_role_skills(role, max_skills=5):
            skill_id = str(skill.get("skill_id", ""))
            if skill_id and skill_id not in self._used_card_ids:
                self._used_card_ids.append(skill_id)

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

    def _coach(self):
        if self.coach is None:
            from llm_werewolf.evaluation.post_game.coach.coach import Coach

            self.coach = Coach()
        return self.coach

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


# Backward-compatible alias during migration.
MemoryManager = RuntimeMemoryManager
