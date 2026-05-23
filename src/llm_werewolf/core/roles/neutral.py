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
                "You are the Thief. On the first night, you are shown two extra role cards "
                "that were not dealt to other players. You must choose one of these roles "
                "to play for the rest of the game. Choose wisely!"
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
                "You have been chosen as a Lover by Cupid. You share a special bond with another "
                "player. You both know each other's identities. If your partner dies, you will "
                "die immediately from heartbreak. Your goal is to survive together with your lover, "
                "even if it means going against your original camp."
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
                "You are in a unique situation: you (or your lover) are a werewolf, "
                "and your lover (or you) are a villager. You must work together to eliminate "
                "all other players so that only you two remain. This is an extremely challenging "
                "victory condition, but if achieved, you both win together."
            ),
            priority=None,
            can_act_night=False,
            can_act_day=False,
        )
