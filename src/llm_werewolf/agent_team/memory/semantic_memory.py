"""Semantic memory backed by role Skill markdown files."""

from __future__ import annotations

import re
import uuid
from collections import defaultdict
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from difflib import SequenceMatcher
from pathlib import Path

from llm_werewolf.agent_team import skill_loader
from llm_werewolf.agent_team.memory.base import SemanticBackend

_FRONTMATTER_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n", re.DOTALL)


@dataclass
class StrategyCard:
    """A long-term role experience card."""

    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    role: str = ""
    content: str = ""
    weight: float = 1.0
    win_count: int = 0
    use_count: int = 0
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    path: str = ""


class InMemoryBackend:
    """Test-only in-memory backend kept for isolated memory tests."""

    def __init__(self) -> None:
        self._cards: dict[str, StrategyCard] = {}

    def store(self, card_id: str, data: dict) -> None:
        self._cards[card_id] = StrategyCard(**data)

    def retrieve(self, role: str, limit: int) -> list[dict]:
        matched = [card for card in self._cards.values() if card.role == role]
        matched.sort(key=lambda card: card.weight, reverse=True)
        return [asdict(card) for card in matched[:limit]]

    def update_weight(self, card_id: str, delta: float) -> None:
        card = self._cards.get(card_id)
        if card is not None:
            card.weight += delta


class SemanticMemory:
    """Manages cross-game strategy skills and their learning weights."""

    def __init__(self, backend: SemanticBackend | None = None) -> None:
        self._backend = backend

    def retrieve_for_role(self, role: str, top_k: int = 3) -> list[StrategyCard]:
        if self._backend is not None:
            return [StrategyCard(**data) for data in self._backend.retrieve(role, top_k)]
        return [
            self._card_from_skill(skill, role)
            for skill in skill_loader.load_role_skills(role, max_skills=top_k)
        ]

    def add_card(self, role: str, content: str) -> StrategyCard:
        card = StrategyCard(role=role, content=content)
        if self._backend is not None:
            self._backend.store(card.id, asdict(card))
            return card
        return self._write_skill_card(card)

    def add_or_merge_card(self, role: str, content: str) -> StrategyCard:
        """Add a skill, or merge it into a similar existing card."""
        existing = self.find_similar_card(role, content)
        if existing is not None:
            existing.use_count += 1
            existing.updated_at = self._now()
            existing.content = self._merge_card_contents(existing.content, content)
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
                card.weight += delta
                self._backend.store(card.id, asdict(card))
            return

        for card in self.retrieve_for_role(role, top_k=100):
            if card.id not in used_card_ids:
                continue
            card.use_count += 1
            if won:
                card.win_count += 1
            card.weight += delta
            card.updated_at = self._now()
            self._write_skill_card(card)

    def decay_all(self, role: str, threshold: float = 0.3) -> int:
        """Delete skill files whose weight is below the threshold."""
        if self._backend is not None:
            return 0
        role_dir = skill_loader.agent_skills_root() / role
        if not role_dir.is_dir():
            return 0
        deleted = 0
        for path in role_dir.glob("*.md"):
            meta, _ = self._read_skill_file(path)
            weight = self._float(meta.get("weight", 1.0), default=1.0)
            if weight < threshold:
                path.unlink()
                deleted += 1
        if deleted:
            skill_loader.list_role_skill_files.cache_clear()
        return deleted

    def format_for_prompt(self, role: str) -> str:
        cards = self.retrieve_for_role(role)
        if not cards:
            return ""
        lines = ["【跨局经验】"]
        for card in cards:
            lines.append(f"- {card.content}（置信度：{card.weight:.2f}）")
        return "\n".join(lines)

    @staticmethod
    def _card_from_skill(skill: dict, role: str) -> StrategyCard:
        path = str(skill.get("path", ""))
        meta, body = SemanticMemory._read_skill_file(Path(path)) if path else ({}, str(skill.get("body", "")))
        return StrategyCard(
            id=str(skill.get("skill_id") or meta.get("skill_id") or Path(path).stem),
            role=str(meta.get("prompt_role_key") or role),
            content=str(skill.get("body") or body),
            weight=SemanticMemory._float(meta.get("weight", skill.get("weight", 1.0)), default=1.0),
            win_count=SemanticMemory._int(meta.get("win_count", 0), default=0),
            use_count=SemanticMemory._int(meta.get("use_count", 0), default=0),
            created_at=str(meta.get("created_at", "")),
            updated_at=str(meta.get("updated_at", "")),
            path=path,
        )

    @staticmethod
    def _read_skill_file(path: Path) -> tuple[dict[str, str], str]:
        text = path.read_text(encoding="utf-8")
        match = _FRONTMATTER_RE.match(text)
        if not match:
            return {}, text.strip()
        meta: dict[str, str] = {}
        for line in match.group(1).splitlines():
            if ":" in line:
                key, _, value = line.partition(":")
                meta[key.strip()] = value.strip()
        return meta, text[match.end() :].strip()

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
        lines = ["---"]
        for key, value in meta.items():
            if value != "":
                lines.append(f"{key}: {value}")
        lines.extend(["---", "", card.content.strip(), ""])
        return "\n".join(lines)

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
        safe_id = re.sub(r"[^\w\u4e00-\u9fff-]+", "_", card.id).strip("_") or "skill"
        return skill_loader.agent_skills_root() / card.role / f"{safe_id}.md"

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
        return " ".join(content.strip().split())

    @classmethod
    def _similarity(cls, left: str, right: str) -> float:
        return SequenceMatcher(
            None,
            cls._normalize_content(left),
            cls._normalize_content(right),
        ).ratio()

    def find_similar_card(self, role: str, content: str, threshold: float = 0.78) -> StrategyCard | None:
        best_match: StrategyCard | None = None
        best_score = 0.0
        for existing in self.retrieve_for_role(role, top_k=100):
            score = self._similarity(existing.content, content)
            if score >= threshold and score > best_score:
                best_match = existing
                best_score = score
        return best_match

    @classmethod
    def _merge_card_contents(cls, base: str, incoming: str) -> str:
        if cls._normalize_content(base) == cls._normalize_content(incoming):
            return base
        if incoming in base:
            return base
        return f"{base}\n\n{incoming}"

    @staticmethod
    def deduplicate_candidates(candidates: list[str]) -> list[str]:
        seen: set[str] = set()
        deduped: list[str] = []
        for candidate in candidates:
            normalized = SemanticMemory._normalize_content(candidate)
            if not normalized or normalized in seen:
                continue
            seen.add(normalized)
            deduped.append(candidate.strip())
        return deduped

    @staticmethod
    def merge_reflections(candidates: list[str]) -> list[str]:
        grouped: dict[str, list[str]] = defaultdict(list)
        for candidate in candidates:
            prefix = candidate.split("：", 1)[0] if "：" in candidate else candidate
            grouped[prefix].append(candidate)

        merged: list[str] = []
        for prefix, items in grouped.items():
            if len(items) == 1:
                merged.append(items[0])
                continue
            suffixes = []
            for item in items:
                suffixes.append(item.split("：", 1)[1] if "：" in item else item)
            merged.append(f"{prefix}：" + "；".join(dict.fromkeys(suffixes)))
        return merged
