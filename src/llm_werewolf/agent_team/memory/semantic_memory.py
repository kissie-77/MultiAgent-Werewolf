"""语义记忆：跨局策略卡片与默认 JSON 后端。"""

from __future__ import annotations

import json
import uuid
from collections import defaultdict
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from difflib import SequenceMatcher

from llm_werewolf.agent_team.memory.base import SemanticBackend


@dataclass
class StrategyCard:
    """跨局经验卡片。"""

    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    role: str = ""
    content: str = ""
    weight: float = 1.0
    win_count: int = 0
    use_count: int = 0
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now().isoformat())


class JSONFileBackend:
    """默认 JSON 文件后端。"""

    def __init__(self, data_dir: Path):
        self._dir = data_dir
        self._dir.mkdir(parents=True, exist_ok=True)
        self._cards: dict[str, StrategyCard] = {}
        self._load()

    def _load(self) -> None:
        for file_path in self._dir.glob("*.json"):
            data = json.loads(file_path.read_text(encoding="utf-8"))
            self._cards[data["id"]] = StrategyCard(**data)

    def store(self, card_id: str, data: dict) -> None:
        card = StrategyCard(**data)
        self._cards[card_id] = card
        file_path = self._dir / f"{card_id}.json"
        file_path.write_text(
            json.dumps(asdict(card), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    def retrieve(self, role: str, limit: int) -> list[dict]:
        matched = [card for card in self._cards.values() if card.role == role]
        matched.sort(key=lambda card: card.weight, reverse=True)
        return [asdict(card) for card in matched[:limit]]


class SemanticMemory:
    """跨局策略卡片管理器。"""

    def __init__(
        self,
        backend: SemanticBackend | None = None,
        data_dir: Path | None = None,
    ):
        self._backend = backend or JSONFileBackend(data_dir or Path("data/semantic_cards"))

    def retrieve_for_role(self, role: str, top_k: int = 3) -> list[StrategyCard]:
        raw_cards = self._backend.retrieve(role, top_k)
        return [StrategyCard(**data) for data in raw_cards]

    def add_card(self, role: str, content: str) -> StrategyCard:
        card = StrategyCard(role=role, content=content)
        self._backend.store(card.id, asdict(card))
        return card

    def add_or_merge_card(self, role: str, content: str) -> StrategyCard:
        """新增卡片；若存在同类卡片，则合并更新而非重复新增。"""
        existing = self.find_similar_card(role, content)
        if existing is not None:
            existing.use_count += 1
            existing.updated_at = datetime.now().isoformat()
            existing.content = self._merge_card_contents(existing.content, content)
            self._backend.store(existing.id, asdict(existing))
            return existing
        return self.add_card(role, content)

    def update_after_game(self, role: str, won: bool, used_card_ids: list[str]) -> None:
        delta = 0.1 if won else -0.05
        cards = {card.id: card for card in self.retrieve_for_role(role, top_k=100)}
        for card_id in used_card_ids:
            card = cards.get(card_id)
            if card is None:
                continue
            card.use_count += 1
            if won:
                card.win_count += 1
            card.updated_at = datetime.now().isoformat()
            card.weight += delta
            self._backend.store(card.id, asdict(card))

    def format_for_prompt(self, role: str) -> str:
        """将角色相关策略卡格式化为提示词片段。"""
        cards = self.retrieve_for_role(role)
        if not cards:
            return ""
        lines = ["【跨局经验】"]
        for card in cards:
            lines.append(f"- {card.content}（置信度：{card.weight:.2f}）")
        return "\n".join(lines)

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
        """查找语义上相近的卡片。"""
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
        """在保留原句的同时追加新增信息，避免简单覆盖。"""
        if cls._normalize_content(base) == cls._normalize_content(incoming):
            return base
        base_prefix = base.split("：", 1)[0] if "：" in base else base
        incoming_suffix = incoming.split("：", 1)[1] if "：" in incoming else incoming
        if incoming_suffix in base:
            return base
        return f"{base_prefix}：{base.split('：', 1)[1] if '：' in base else base}；{incoming_suffix}"

    @staticmethod
    def deduplicate_candidates(candidates: list[str]) -> list[str]:
        """按归一化内容去重候选策略。"""
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
        """按前缀聚合同类反思，避免同类候选碎片化。"""
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
            merged.append(f"{prefix}：{'；'.join(dict.fromkeys(suffixes))}")
        return merged
