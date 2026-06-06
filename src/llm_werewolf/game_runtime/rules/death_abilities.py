"""死亡触发的技能（猎人开枪、狼王等）。"""

from __future__ import annotations

DEATH_ABILITY_ROLE_NAMES: frozenset[str] = frozenset({"Hunter", "Alpha Wolf", "White Wolf"})

POISON_BLOCKS_DEATH_ABILITY = "witch_poison"
