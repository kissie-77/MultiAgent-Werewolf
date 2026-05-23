from llm_werewolf.core.types import (
    Camp,
    RoleConfig,
    ActionPriority,
    ActionProtocol,
    PlayerProtocol,
    GameStateProtocol,
)
from llm_werewolf.core.roles.base import Role


class Thief(Role):
    """盗贼角色。

    首夜可在两张随机发放的身份牌中选择其一。
    所选身份将成为其本局实际角色。
    """

    def __init__(self, player: PlayerProtocol) -> None:
        """初始化盗贼角色。"""
        super().__init__(player)
        self.available_roles: list[Role] = []
        self.has_chosen = False


    def get_config(self) -> RoleConfig:
        """获取盗贼角色的配置。"""
        return RoleConfig(
            name="Thief",
            camp=Camp.NEUTRAL,  # 初始为中立，选择身份后变为对应阵营
            description=(
                "你是盗贼。第一夜，你会看到两张未发给其他玩家的身份牌。"
                "你必须从中选择一个身份进行剩余游戏。请谨慎选择！"
            ),
            priority=ActionPriority.THIEF,
            can_act_night=True,
            can_act_day=False,
            max_uses=1,
        )


class Lover(Role):
    """情侣角色（由丘比特创建）。

    这不是开局角色，而是丘比特赋予的状态。
    情侣同生共死、共同获胜。
    """

    def __init__(self, player: PlayerProtocol) -> None:
        """初始化情侣角色。"""
        super().__init__(player)
        self.partner_id: str | None = None
        self.original_role: Role | None = None


    def get_config(self) -> RoleConfig:
        """获取情侣角色的配置。

        注意：情侣是状态/修饰符，而非主身份。
        玩家保留原身份，同时获得情侣状态。
        """
        return RoleConfig(
            name="Lover",
            camp=Camp.NEUTRAL,  # 情侣拥有独立的胜利条件
            description=(
                "你被丘比特选为恋人。你与另一名玩家有特殊羁绊，彼此知晓对方身份。"
                "如果你的恋人死亡，你会立即心碎殉情。"
                "你的目标是与恋人一起存活到最后，即使这意味着背叛你的原始阵营。"
            ),
            priority=None,
            can_act_night=False,
            can_act_day=False,
        )


class WhiteLoverWolf(Role):
    """白狼情侣 — 特殊情况。

    当狼人与好人结为情侣时，形成独特的同盟关系。
    此动态角色表示这种矛盾状态。
    """

    def __init__(self, player: PlayerProtocol) -> None:
        """初始化白狼情侣角色。"""
        super().__init__(player)


    def get_config(self) -> RoleConfig:
        """获取白狼情侣角色的配置。"""
        return RoleConfig(
            name="White Lover Wolf",
            camp=Camp.NEUTRAL,
            description=(
                "你处于一种特殊情况：你（或你的恋人）是狼人，而你的恋人（或你）是好人。"
                "你们必须合作淘汰所有其他玩家，直到仅剩你们两人。"
                "这是一个极具挑战性的胜利条件，但如果达成，你们将共同获胜。"
            ),
            priority=None,
            can_act_night=False,
            can_act_day=False,
        )
