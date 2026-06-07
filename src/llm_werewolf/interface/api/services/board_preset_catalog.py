"""Curated board presets (YAML with ``preset:`` metadata + optional ``role_names``)."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import yaml

from llm_werewolf.game_runtime.config.presets import create_game_config_from_player_count
from llm_werewolf.game_runtime.config.standard_boards import STANDARD_BOARD_SIZES, standard_config_id
from llm_werewolf.game_runtime.roles.catalog import ROLE_CATALOG, get_definition
from llm_werewolf.interface.api.models.actions import BoardPresetOption, BoardPresetsResponse, PlayableRoleOption

if TYPE_CHECKING:
    from pathlib import Path

_CAMP_ZH = {
    "werewolf": "狼人阵营",
    "villager": "好人阵营",
    "neutral": "第三方",
}


def _camp_counts(role_names: list[str]) -> tuple[int, int, int]:
    wolf = villager = neutral = 0
    for key in role_names:
        camp = get_definition(key).camp.value
        if camp == "werewolf":
            wolf += 1
        elif camp == "neutral":
            neutral += 1
        else:
            villager += 1
    return wolf, villager, neutral


def build_playable_roles() -> list[PlayableRoleOption]:
    return [
        PlayableRoleOption(
            key=defn.name,
            display_name=defn.display_name,
            camp=defn.camp.value,
            camp_label=_CAMP_ZH.get(defn.camp.value, defn.camp.value),
        )
        for defn in ROLE_CATALOG
    ]


def _standard_auto_presets() -> list[BoardPresetOption]:
    presets: list[BoardPresetOption] = []
    for count in STANDARD_BOARD_SIZES:
        if count < 6:
            continue
        cfg = create_game_config_from_player_count(count)
        wolf, villager, neutral = _camp_counts(cfg.role_names)
        presets.append(
            BoardPresetOption(
                preset_id=standard_config_id(count),
                kind="standard",
                title=f"标准 {count} 人局",
                description=f"按人数自动配板：{wolf} 狼 / {villager + neutral} 神民",
                tags=["标准", f"{count}人"],
                player_count=count,
                role_names=list(cfg.role_names),
                role_labels=[get_definition(r).display_name for r in cfg.role_names],
                werewolf_count=wolf,
                villager_count=villager,
                neutral_count=neutral,
            )
        )
    return presets


def _load_yaml_meta(path: Path) -> dict[str, Any]:
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    return data if isinstance(data, dict) else {}


def _curated_presets(configs_dir: Path) -> list[BoardPresetOption]:
    out: list[BoardPresetOption] = []
    for path in sorted(configs_dir.glob("preset-*.yaml")):
        data = _load_yaml_meta(path)
        meta = data.get("preset")
        if not isinstance(meta, dict):
            continue
        if meta.get("featured") is not True:
            continue
        role_names = data.get("role_names")
        if not isinstance(role_names, list) or not role_names:
            continue
        keys = [str(r) for r in role_names]
        wolf, villager, neutral = _camp_counts(keys)
        out.append(
            BoardPresetOption(
                preset_id=path.stem,
                kind="curated",
                title=str(meta.get("title") or path.stem),
                description=str(meta.get("description") or ""),
                tags=[str(t) for t in meta.get("tags") or []],
                player_count=len(keys),
                role_names=keys,
                role_labels=[get_definition(r).display_name for r in keys],
                werewolf_count=wolf,
                villager_count=villager,
                neutral_count=neutral,
            )
        )
    return out


def build_board_presets_response(configs_dir: Path) -> BoardPresetsResponse:
    curated = _curated_presets(configs_dir)
    standard = _standard_auto_presets()
    return BoardPresetsResponse(
        roles=build_playable_roles(),
        presets=[*curated, *standard],
        default_preset_id=standard[1].preset_id if len(standard) > 1 else (standard[0].preset_id if standard else ""),
    )
