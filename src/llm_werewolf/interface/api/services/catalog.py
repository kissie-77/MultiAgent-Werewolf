"""Role catalog service."""

from __future__ import annotations

from llm_werewolf.game_runtime.roles.catalog import get_catalog, get_definition
from llm_werewolf.interface.api.models.pages import RoleDetail, RoleListItem, RoleListPageData
from llm_werewolf.game_runtime.roles.registry import build_catalog_to_runtime_map
from llm_werewolf.game_runtime.prompts.identity import _VICTORY_TEXT, get_identity_template
from llm_werewolf.interface.api.services.content import CAMP_LABELS

_CATALOG_TO_RUNTIME = build_catalog_to_runtime_map()

_NIGHT_ACTION_ROLES = {
    "Werewolf",
    "AlphaWolf",
    "WhiteWolf",
    "WolfBeauty",
    "GuardianWolf",
    "HiddenWolf",
    "BloodMoonApostle",
    "NightmareWolf",
    "Seer",
    "Witch",
    "Guard",
    "Cupid",
    "Raven",
    "GraveyardKeeper",
    "Thief",
    "Magician",
}


def _to_list_item(defn) -> RoleListItem:
    return RoleListItem(
        key=defn.name,
        display_name=defn.display_name,
        camp=defn.camp.value,
        camp_label=CAMP_LABELS.get(defn.camp.value, defn.camp.value),
        victory_goal=defn.victory_goal.value,
        has_night_action=defn.name in _NIGHT_ACTION_ROLES,
    )


def list_roles_page() -> RoleListPageData:
    items = [_to_list_item(d) for d in get_catalog()]
    camps: dict[str, list[RoleListItem]] = {}
    for item in items:
        camps.setdefault(item.camp, []).append(item)
    return RoleListPageData(title="角色列表", camps=camps, total=len(items))


def get_role_detail(role_key: str) -> RoleDetail:
    defn = get_definition(role_key)
    fields = get_identity_template(defn.name)
    victory_text = _VICTORY_TEXT.get(defn.victory_goal, "")
    runtime_name = _CATALOG_TO_RUNTIME.get(defn.name, defn.name)
    base = _to_list_item(defn)
    tips = [fields.get("instruction", ""), fields.get("suggestion", "")]
    tips = [t for t in tips if t]
    return RoleDetail(
        **base.model_dump(),
        runtime_name=runtime_name,
        instruction=fields.get("instruction", ""),
        suggestion=fields.get("suggestion", ""),
        victory_text=victory_text,
        tips=tips,
    )
