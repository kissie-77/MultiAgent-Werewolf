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
_DESCRIPTION_PREFIXES = ("描述：", "描述:", "description:", "Description:")
_DESCRIPTION_SUFFIX = "的情况下，使用该 skill"


@dataclass
class StrategyCard:
    """A long-term role experience card."""

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
    """Test-only in-memory backend kept for isolated memory tests."""

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
            card.weight += delta


class SemanticMemory:
    """Manages cross-game strategy skills and their learning weights."""

    def __init__(
        self,
        backend: SemanticBackend | None = None,
        compressor: object | None = None,
    ) -> None:
        self._backend = backend
        self._compressor = compressor

    def retrieve_for_role(self, role: str, top_k: int = 3) -> list[StrategyCard]:
        if self._backend is not None:
            return [self._normalize_card(StrategyCard(**data)) for data in self._backend.retrieve(role, top_k)]
        return [
            self._card_from_skill(skill, role)
            for skill in skill_loader.load_role_skills(role, max_skills=top_k)
        ]

    def add_card(self, role: str, content: str) -> StrategyCard:
        description, body = self._split_description_line(content)
        card = StrategyCard(
            role=role,
            description=description or self._extract_description(content),
            content=body,
        )
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
            description, body = self._split_description_line(content)
            if not existing.description:
                existing.description = description or self._extract_description(content)
            existing.content = self._merge_card_contents(existing.content, body)
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

    def decay_all(self, role: str, max_count: int = 8) -> int:
        """Delete lowest-weight skill files when a role exceeds max_count cards."""
        cards = self._retrieve_all_for_role(role)
        if len(cards) <= max_count:
            return 0
        cards.sort(key=lambda card: card.weight)
        to_delete = cards[: len(cards) - max_count]
        if self._backend is not None:
            delete = getattr(self._backend, "delete", None)
            if delete is None:
                return 0
            for card in to_delete:
                delete(card.id)
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
            retrieve_all = getattr(self._backend, "retrieve_all", None)
            if retrieve_all is not None:
                return [self._normalize_card(StrategyCard(**data)) for data in retrieve_all(role)]
            return [self._normalize_card(StrategyCard(**data)) for data in self._backend.retrieve(role, 10_000)]
        return [
            self._card_from_skill({"path": str(path)}, role)
            for path in skill_loader.list_role_skill_files(role)
        ]

    def format_for_prompt(self, role: str) -> str:
        cards = self.retrieve_for_role(role)
        if not cards:
            return ""
        lines = ["【跨局经验】"]
        for card in cards:
            description = card.description or self._extract_description(card.content)
            lines.append(f"- {description}")
        return "\n".join(lines)

    @classmethod
    def _normalize_card(cls, card: StrategyCard) -> StrategyCard:
        card.description = cls._ensure_description_format(card.description or cls._extract_description(card.content))
        return card

    @staticmethod
    def _card_from_skill(skill: dict, role: str) -> StrategyCard:
        path = str(skill.get("path", ""))
        meta, body = SemanticMemory._read_skill_file(Path(path)) if path else ({}, str(skill.get("body", "")))
        raw_body = str(skill.get("body") or body)
        body_description, body_content = SemanticMemory._split_description_line(raw_body)
        description = str(skill.get("description") or meta.get("description") or body_description)
        if not description:
            description = SemanticMemory._extract_description(body_content)
        return StrategyCard(
            id=str(skill.get("skill_id") or meta.get("skill_id") or Path(path).stem),
            role=str(meta.get("prompt_role_key") or role),
            description=SemanticMemory._ensure_description_format(description),
            content=body_content,
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
        lines.extend(["---", ""])
        if card.description:
            lines.extend([f"描述：{card.description}", ""])
        lines.extend([card.content.strip(), ""])
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

    @staticmethod
    def _split_description_line(content: str) -> tuple[str, str]:
        lines = content.strip().splitlines()
        if not lines:
            return "", ""
        first = lines[0].strip()
        for prefix in _DESCRIPTION_PREFIXES:
            if first.startswith(prefix):
                description = first[len(prefix) :].strip()
                return SemanticMemory._ensure_description_format(description), "\n".join(lines[1:]).strip()
        return "", content.strip()

    @classmethod
    def _extract_description(cls, content: str) -> str:
        description, body = cls._split_description_line(content)
        if description:
            return description
        source = body or content
        match = re.search(r"[。！？!?；;]", source)
        if match:
            candidate = source[: match.start()].strip()
        else:
            candidate = source.strip()[:30]
        return cls._ensure_description_format(candidate)

    @staticmethod
    def _ensure_description_format(text: str) -> str:
        normalized = " ".join(text.strip().split())
        if not normalized:
            return f"通用对局经验{_DESCRIPTION_SUFFIX}"
        if normalized.endswith(_DESCRIPTION_SUFFIX):
            return normalized
        normalized = normalized.rstrip("。.!！")
        if normalized.endswith("的情况下"):
            return f"{normalized}，使用该 skill"
        return f"{normalized}{_DESCRIPTION_SUFFIX}"

    def _call_llm(self, prompt: str, max_tokens: int = 10) -> str:
        if self._compressor is None:
            raise RuntimeError("No LLM compressor configured")
        return self._compressor._call_llm_text(prompt, max_tokens=max_tokens)

    def find_similar_card(self, role: str, content: str, threshold: float = 0.78) -> StrategyCard | None:
        description = self._extract_description(content)
        existing_cards = self._retrieve_all_for_role(role)
        if not existing_cards:
            return None

        if self._compressor is not None:
            options = []
            for idx, card in enumerate(existing_cards, start=1):
                card_description = card.description or self._extract_description(card.content)
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
                idx = int(response) - 1
                if 0 <= idx < len(existing_cards):
                    return existing_cards[idx]
            except (Exception, ValueError):
                pass
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
            existing_description = existing.description or self._extract_description(existing.content)
            score = self._similarity(existing_description, description)
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
