"""Semantic memory backed by role Skill markdown files."""

from __future__ import annotations

import logging
import re
import uuid
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path

from llm_werewolf.agent_team.memory.base import CompressorProtocol, SemanticBackend
from llm_werewolf.agent_team.memory.semantic_matching import (
    deduplicate_candidates as deduplicate_candidate_texts,
    merge_card_contents,
    merge_reflections as merge_reflection_texts,
    normalize_content,
    similarity,
)
from llm_werewolf.agent_team.skill_support import skill_loader
from llm_werewolf.agent_team.skill_support.skill_markdown import (
    ensure_description_format,
    extract_description,
    read_skill_markdown,
    render_frontmatter_markdown,
)

logger = logging.getLogger(__name__)

_WEIGHT_MIN = 0.1
_WEIGHT_MAX = 5.0


def clamp_weight(weight: float) -> float:
    """将权重限制在 [_WEIGHT_MIN, _WEIGHT_MAX] 范围内。"""
    return max(_WEIGHT_MIN, min(_WEIGHT_MAX, weight))


@dataclass
class StrategyCard:
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    role: str = ""
    description: str = ""
    content: str = ""
    weight: float = 1.0
    win_count: int = 0
    use_count: int = 0
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    path: str = ""


class InMemoryBackend:
    def __init__(self) -> None:
        self._cards: dict[str, StrategyCard] = {}

    def store(self, card_id: str, data: dict) -> None:
        self._cards[card_id] = StrategyCard(**data)

    def retrieve(self, role: str, limit: int) -> list[dict]:
        matched = [card for card in self._cards.values() if card.role == role]
        matched.sort(key=lambda card: card.weight, reverse=True)
        return [asdict(card) for card in matched[:limit]]

    def retrieve_all(self, role: str) -> list[dict]:
        matched = [card for card in self._cards.values() if card.role == role]
        matched.sort(key=lambda card: card.weight, reverse=True)
        return [asdict(card) for card in matched]

    def delete(self, card_id: str) -> None:
        self._cards.pop(card_id, None)

    def update_weight(self, card_id: str, delta: float) -> None:
        card = self._cards.get(card_id)
        if card is not None:
            card.weight = clamp_weight(card.weight + delta)


class SemanticMemory:
    MIN_WEIGHT = 0.1
    MAX_WEIGHT = 5.0

    def __init__(
        self,
        backend: SemanticBackend | None = None,
        compressor: CompressorProtocol | None = None,
    ) -> None:
        self._backend = backend
        self._compressor = compressor

    def retrieve_for_role(self, role: str, top_k: int = 3) -> list[StrategyCard]:
        if self._backend is not None:
            return [self._normalize_card(StrategyCard(**data)) for data in self._backend.retrieve(role, top_k)]
        return self._cards_from_skill_loader(role, top_k=top_k, include_draft=False)

    @staticmethod
    def _cards_from_skill_loader(
        role: str, *, top_k: int = 3, include_draft: bool = False
    ) -> list[StrategyCard]:
        return [
            SemanticMemory._card_from_skill(skill, role)
            for skill in skill_loader.load_role_skills(role, max_skills=top_k, include_draft=include_draft)
        ]

    def add_card(self, role: str, content: str) -> StrategyCard:
        card = StrategyCard(role=role, description=extract_description(content), content=content.strip())
        if self._backend is not None:
            self._backend.store(card.id, asdict(card))
            return card
        return self._write_skill_card(card)

    def add_or_merge_card(self, role: str, content: str) -> StrategyCard:
        existing = self.find_similar_card(role, content)
        if existing is not None:
            existing.use_count += 1
            existing.updated_at = self._now()
            if not existing.description:
                existing.description = extract_description(content)
            existing.content = self._merge_card_contents(existing.content, content.strip())
            if self._backend is not None:
                self._backend.store(existing.id, asdict(existing))
                return existing
            return self._write_skill_card(existing)
        return self.add_card(role, content)

    def update_after_game(self, role: str, won: bool, used_card_ids: list[str]) -> None:
        delta = 0.1 if won else -0.05
        if self._backend is not None:
            cards = {card.id: card for card in self.retrieve_for_role(role, top_k=100)}
            for card_id in used_card_ids:
                card = cards.get(card_id)
                if card is None:
                    continue
                card.use_count += 1
                if won:
                    card.win_count += 1
                card.updated_at = self._now()
                card.weight = clamp_weight(card.weight + delta)
                self._backend.store(card.id, asdict(card))
            return

        for card in self._cards_from_skill_loader(role, top_k=100, include_draft=True):
            if card.id not in used_card_ids:
                continue
            card.use_count += 1
            if won:
                card.win_count += 1
            card.weight = clamp_weight(card.weight + delta)
            card.updated_at = self._now()
            self._write_skill_card(card)

    def evict_excess(self, role: str, max_count: int = 8) -> int:
        cards = self._retrieve_all_for_role(role)
        if len(cards) <= max_count:
            return 0
        cards.sort(key=lambda card: card.weight)
        to_delete = cards[: len(cards) - max_count]
        if self._backend is not None:
            for card in to_delete:
                self._backend.delete(card.id)
            return len(to_delete)
        deleted = 0
        for card in to_delete:
            path = Path(card.path)
            if path.is_file():
                path.unlink()
                deleted += 1
        if deleted:
            skill_loader.list_role_skill_files.cache_clear()
        return deleted

    def _retrieve_all_for_role(self, role: str) -> list[StrategyCard]:
        if self._backend is not None:
            return [self._normalize_card(StrategyCard(**data)) for data in self._backend.retrieve_all(role)]
        return [self._card_from_skill({"path": str(path)}, role) for path in skill_loader.list_role_skill_files(role)]

    def format_for_prompt(self, role: str) -> str:
        cards = self.retrieve_for_role(role)
        if not cards:
            return ""
        lines = ["【跨局经验】"]
        for card in cards:
            lines.append(f"- {card.description or extract_description(card.content)}")
        return "\n".join(lines)

    @classmethod
    def _normalize_card(cls, card: StrategyCard) -> StrategyCard:
        card.description = cls._ensure_description_format(card.description or extract_description(card.content))
        card.weight = clamp_weight(card.weight)
        return card

    @staticmethod
    def _card_from_skill(skill: dict, role: str) -> StrategyCard:
        path = str(skill.get("path", ""))
        meta, body = SemanticMemory._read_skill_file(Path(path)) if path else ({}, str(skill.get("body", "")))
        raw_body = str(skill.get("body") or body)
        description = str(skill.get("description") or meta.get("description") or extract_description(raw_body))
        return StrategyCard(
            id=str(skill.get("skill_id") or meta.get("skill_id") or Path(path).stem),
            role=str(meta.get("prompt_role_key") or role),
            description=SemanticMemory._ensure_description_format(description),
            content=raw_body,
            weight=SemanticMemory._float(meta.get("weight", skill.get("weight", 1.0)), default=1.0),
            win_count=SemanticMemory._int(meta.get("win_count", 0), default=0),
            use_count=SemanticMemory._int(meta.get("use_count", 0), default=0),
            created_at=str(meta.get("created_at", "")),
            updated_at=str(meta.get("updated_at", "")),
            path=path,
        )

    @staticmethod
    def _read_skill_file(path: Path) -> tuple[dict[str, str], str]:
        return read_skill_markdown(path)

    @staticmethod
    def _render_skill_file(card: StrategyCard, existing_meta: dict[str, str] | None = None) -> str:
        meta = dict(existing_meta or {})
        meta.update({
            "skill_id": card.id,
            "prompt_role_key": card.role,
            "status": meta.get("status", "draft"),
            "weight": f"{card.weight:.2f}",
            "win_count": str(card.win_count),
            "use_count": str(card.use_count),
            "created_at": meta.get("created_at") or card.created_at or SemanticMemory._now(),
            "updated_at": card.updated_at or SemanticMemory._now(),
        })
        body_parts = [f"描述：{card.description}", "", card.content.strip()]
        return render_frontmatter_markdown(meta, "\n".join(body_parts))

    def _write_skill_card(self, card: StrategyCard) -> StrategyCard:
        path = Path(card.path) if card.path else self._skill_path(card)
        existing_meta: dict[str, str] = {}
        if path.is_file():
            existing_meta, _ = self._read_skill_file(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(self._render_skill_file(card, existing_meta), encoding="utf-8")
        skill_loader.list_role_skill_files.cache_clear()
        card.path = str(path)
        return card

    @staticmethod
    def _skill_path(card: StrategyCard) -> Path:
        from llm_werewolf.strategy.role_version_manifest import get_active_manifest

        safe_id = re.sub(r"[^\w\u4e00-\u9fff-]+", "_", card.id).strip("_") or "skill"
        version = get_active_manifest().skill_version_for(card.role)
        return skill_loader.role_skill_version_dir(card.role, version) / f"{safe_id}.md"

    @staticmethod
    def _now() -> str:
        return datetime.now(timezone.utc).isoformat(timespec="seconds")

    @staticmethod
    def _float(value: object, *, default: float) -> float:
        try:
            return float(value)
        except (TypeError, ValueError):
            return default

    @staticmethod
    def _int(value: object, *, default: int) -> int:
        try:
            return int(value)
        except (TypeError, ValueError):
            return default

    @staticmethod
    def _normalize_content(content: str) -> str:
        return normalize_content(content)

    @classmethod
    def _similarity(cls, left: str, right: str) -> float:
        return similarity(left, right)

    @staticmethod
    def _split_description_line(content: str) -> tuple[str, str]:
        from llm_werewolf.agent_team.skill_support.skill_markdown import split_description_line

        return split_description_line(content)

    @staticmethod
    def _ensure_description_format(text: str) -> str:
        return ensure_description_format(text)

    def _call_llm(self, prompt: str, max_tokens: int = 10) -> str:
        if self._compressor is None:
            raise RuntimeError("No LLM compressor configured")
        return self._compressor.call_llm_text(prompt, max_tokens=max_tokens)

    def find_similar_card(self, role: str, content: str, threshold: float = 0.78) -> StrategyCard | None:
        description = extract_description(content)
        existing_cards = self._retrieve_all_for_role(role)
        if not existing_cards:
            return None

        if self._compressor is not None:
            options = []
            for idx, card in enumerate(existing_cards, start=1):
                card_description = card.description or extract_description(card.content)
                options.append(f"{idx}. {card_description}")
            prompt = (
                f"新经验的触发条件：{description}\n\n"
                f"已有经验列表：\n" + "\n".join(options) + "\n\n"
                "请判断新经验和哪一个已有经验的触发条件相同或高度相似。\n"
                "如果有一个匹配的，只回复对应编号，例如 1。\n"
                "如果没有匹配的，只回复 无。"
            )
            try:
                response = self._call_llm(prompt, max_tokens=10).strip()
                if response == "无":
                    return None
                match = re.search(r"\d+", response)
                if match is None:
                    return self._find_similar_by_sequence_matcher(description, existing_cards, threshold)
                idx = int(match.group(0)) - 1
                if 0 <= idx < len(existing_cards):
                    return existing_cards[idx]
            except Exception:
                logger.debug("LLM similarity match failed, falling back to sequence matcher", exc_info=True)
        return self._find_similar_by_sequence_matcher(description, existing_cards, threshold)

    def _find_similar_by_sequence_matcher(
        self,
        description: str,
        existing_cards: list[StrategyCard],
        threshold: float = 0.78,
    ) -> StrategyCard | None:
        best_match: StrategyCard | None = None
        best_score = 0.0
        for existing in existing_cards:
            existing_description = existing.description or extract_description(existing.content)
            score = self._similarity(existing_description, description)
            if score >= threshold and score > best_score:
                best_match = existing
                best_score = score
        return best_match

    @classmethod
    def _merge_card_contents(cls, base: str, incoming: str) -> str:
        return merge_card_contents(base, incoming)

    @staticmethod
    def deduplicate_candidates(candidates: list[str]) -> list[str]:
        return deduplicate_candidate_texts(candidates)

    @staticmethod
    def merge_reflections(candidates: list[str]) -> list[str]:
        return merge_reflection_texts(candidates)
