"""权威角色目录：名称、实现、阵营、胜利目标。"""

from llm_werewolf.game_runtime.types.enums import Camp, VictoryGoal
from llm_werewolf.game_runtime.roles.definition import RoleDefinition

V = VictoryGoal
C = Camp
R = RoleDefinition

ROLE_CATALOG: list[RoleDefinition] = [
    R(
        name="Werewolf",
        display_name="狼人",
        implementation="llm_werewolf.game_runtime.roles.werewolf:Werewolf",
        camp=C.WEREWOLF,
        victory_goal=V.WEREWOLF_PARITY,
    ),
    R(
        name="AlphaWolf",
        display_name="狼王",
        implementation="llm_werewolf.game_runtime.roles.werewolf:AlphaWolf",
        camp=C.WEREWOLF,
        victory_goal=V.WEREWOLF_PARITY,
    ),
    R(
        name="WhiteWolf",
        display_name="白狼",
        implementation="llm_werewolf.game_runtime.roles.werewolf:WhiteWolf",
        camp=C.WEREWOLF,
        victory_goal=V.WEREWOLF_PARITY,
    ),
    R(
        name="WolfBeauty",
        display_name="狼美人",
        implementation="llm_werewolf.game_runtime.roles.werewolf:WolfBeauty",
        camp=C.WEREWOLF,
        victory_goal=V.WEREWOLF_PARITY,
    ),
    R(
        name="GuardianWolf",
        display_name="守卫狼",
        implementation="llm_werewolf.game_runtime.roles.werewolf:GuardianWolf",
        camp=C.WEREWOLF,
        victory_goal=V.WEREWOLF_PARITY,
    ),
    R(
        name="HiddenWolf",
        display_name="隐狼",
        implementation="llm_werewolf.game_runtime.roles.werewolf:HiddenWolf",
        camp=C.WEREWOLF,
        victory_goal=V.WEREWOLF_PARITY,
    ),
    R(
        name="BloodMoonApostle",
        display_name="血月使徒",
        implementation="llm_werewolf.game_runtime.roles.werewolf:BloodMoonApostle",
        camp=C.WEREWOLF,
        victory_goal=V.WEREWOLF_PARITY,
    ),
    R(
        name="NightmareWolf",
        display_name="梦魇狼",
        implementation="llm_werewolf.game_runtime.roles.werewolf:NightmareWolf",
        camp=C.WEREWOLF,
        victory_goal=V.WEREWOLF_PARITY,
    ),
    R(
        name="Villager",
        display_name="平民",
        implementation="llm_werewolf.game_runtime.roles.villager:Villager",
        camp=C.VILLAGER,
        victory_goal=V.VILLAGER_ELIMINATE_WEREWOLVES,
    ),
    R(
        name="Seer",
        display_name="预言家",
        implementation="llm_werewolf.game_runtime.roles.villager:Seer",
        camp=C.VILLAGER,
        victory_goal=V.VILLAGER_ELIMINATE_WEREWOLVES,
    ),
    R(
        name="Witch",
        display_name="女巫",
        implementation="llm_werewolf.game_runtime.roles.villager:Witch",
        camp=C.VILLAGER,
        victory_goal=V.VILLAGER_ELIMINATE_WEREWOLVES,
    ),
    R(
        name="Hunter",
        display_name="猎人",
        implementation="llm_werewolf.game_runtime.roles.villager:Hunter",
        camp=C.VILLAGER,
        victory_goal=V.VILLAGER_ELIMINATE_WEREWOLVES,
    ),
    R(
        name="Guard",
        display_name="守卫",
        implementation="llm_werewolf.game_runtime.roles.villager:Guard",
        camp=C.VILLAGER,
        victory_goal=V.VILLAGER_ELIMINATE_WEREWOLVES,
    ),
    R(
        name="Idiot",
        display_name="白痴",
        implementation="llm_werewolf.game_runtime.roles.villager:Idiot",
        camp=C.VILLAGER,
        victory_goal=V.VILLAGER_ELIMINATE_WEREWOLVES,
    ),
    R(
        name="Elder",
        display_name="长老",
        implementation="llm_werewolf.game_runtime.roles.villager:Elder",
        camp=C.VILLAGER,
        victory_goal=V.VILLAGER_ELIMINATE_WEREWOLVES,
    ),
    R(
        name="Knight",
        display_name="骑士",
        implementation="llm_werewolf.game_runtime.roles.villager:Knight",
        camp=C.VILLAGER,
        victory_goal=V.VILLAGER_ELIMINATE_WEREWOLVES,
    ),
    R(
        name="Magician",
        display_name="魔术师",
        implementation="llm_werewolf.game_runtime.roles.villager:Magician",
        camp=C.VILLAGER,
        victory_goal=V.VILLAGER_ELIMINATE_WEREWOLVES,
    ),
    R(
        name="Cupid",
        display_name="丘比特",
        implementation="llm_werewolf.game_runtime.roles.villager:Cupid",
        camp=C.VILLAGER,
        victory_goal=V.VILLAGER_ELIMINATE_WEREWOLVES,
    ),
    R(
        name="Raven",
        display_name="乌鸦",
        implementation="llm_werewolf.game_runtime.roles.villager:Raven",
        camp=C.VILLAGER,
        victory_goal=V.VILLAGER_ELIMINATE_WEREWOLVES,
    ),
    R(
        name="GraveyardKeeper",
        display_name="守墓人",
        implementation="llm_werewolf.game_runtime.roles.villager:GraveyardKeeper",
        camp=C.VILLAGER,
        victory_goal=V.VILLAGER_ELIMINATE_WEREWOLVES,
    ),
    R(
        name="Thief",
        display_name="盗贼",
        implementation="llm_werewolf.game_runtime.roles.neutral:Thief",
        camp=C.NEUTRAL,
        victory_goal=V.NEUTRAL_THIEF,
    ),
    R(
        name="Lover",
        display_name="恋人",
        implementation="llm_werewolf.game_runtime.roles.neutral:Lover",
        camp=C.NEUTRAL,
        victory_goal=V.NEUTRAL_LOVER,
    ),
]

VICTORY_GOAL_DESCRIPTIONS: dict[VictoryGoal, str] = {
    V.WEREWOLF_PARITY: "狼人阵营获胜条件：场上存活狼人数量不少于存活好人数量。",
    V.VILLAGER_ELIMINATE_WEREWOLVES: "好人阵营获胜条件：消灭所有狼人（含需计数的特殊狼人）。",
    V.NEUTRAL_LOVER: "恋人获胜条件：与恋人一起存活到最后，可跨越原阵营。",
    V.NEUTRAL_THIEF: "盗贼：首夜选择一张额外身份牌，胜利目标随所选身份而定。",
    V.NEUTRAL_WHITE_LOVER_WOLF: "白狼恋人：与恋人消灭其余所有人后双人获胜。",
    V.FOLLOW_ASSIGNED_CAMP: "胜利目标随当前阵营技能而定。",
}


def get_catalog() -> list[RoleDefinition]:
    """返回所有内置角色定义。"""
    return list(ROLE_CATALOG)


def get_definition(name: str) -> RoleDefinition:
    """按注册表名称查找角色定义。"""
    for definition in ROLE_CATALOG:
        if definition.name == name:
            return definition
    msg = f"Unknown role definition: {name}"
    raise KeyError(msg)


def get_definition_by_role_class(role_class: type) -> RoleDefinition:
    """按角色类查找定义。"""
    impl_path = f"{role_class.__module__}:{role_class.__name__}"
    for definition in ROLE_CATALOG:
        if definition.implementation == impl_path:
            return definition
    msg = f"No definition for role class {impl_path}"
    raise KeyError(msg)
