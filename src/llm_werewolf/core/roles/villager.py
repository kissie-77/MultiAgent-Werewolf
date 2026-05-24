from llm_werewolf.core.types import (
    Camp,
    RoleConfig,
    ActionPriority,
    ActionProtocol,
    PlayerProtocol,
    GameStateProtocol,
)
from llm_werewolf.core.actions import (
    CupidLinkAction,
    RavenMarkAction,
    SeerCheckAction,
    WitchSaveAction,
    WitchPoisonAction,
    GuardProtectAction,
    GraveyardKeeperCheckAction,
)
from llm_werewolf.core.roles.base import Role
from llm_werewolf.core.roles.names import seer_apparent_camp


class Villager(Role):
    """标准村民角色。

    无特殊技能的普通村民。
    仅在白天阶段可以投票。
    """

    def get_config(self) -> RoleConfig:
        """获取村民角色的配置。"""
        return RoleConfig(
            name="Villager",
            camp=Camp.VILLAGER,
            description=(
                "你是平民。你没有特殊技能，但可以在白天投票淘汰疑似狼人的玩家。"
                "运用你的推理和说服能力帮助好人阵营获胜！"
            ),
            priority=None,
            can_act_night=False,
            can_act_day=False,
        )



class Seer(Role):
    """预言家角色。

    每晚可查验一名玩家是狼人还是好人。
    """

    def get_private_notes(self, game_state: GameStateProtocol | None = None) -> list[str]:
        notes = super().get_private_notes(game_state)
        if game_state is None:
            return notes

        checked_info = []
        for round_num, player_id in game_state.seer_checked.items():
            player = game_state.get_player(player_id)
            if player:
                apparent = seer_apparent_camp(player)
                result = "狼人" if apparent == Camp.WEREWOLF else "好人"
                checked_info.append(f"第{round_num}夜：查验{player.name}，结果为{result}。")

        return notes + checked_info

    def get_config(self) -> RoleConfig:
        """获取预言家角色的配置。"""
        return RoleConfig(
            name="Seer",
            camp=Camp.VILLAGER,
            description=(
                "你是预言家。每晚可以查验一名玩家的真实身份（狼人或好人）。"
                "善用这些信息引导好人阵营，但要注意不要过早暴露自己。"
            ),
            priority=ActionPriority.SEER,
            can_act_night=True,
            can_act_day=False,
        )



class Witch(Role):
    """女巫角色。

    拥有两瓶药：一瓶救人、一瓶毒人。
    每瓶药整局游戏只能使用一次。
    """

    def __init__(self, player: PlayerProtocol) -> None:
        """初始化女巫角色。"""
        super().__init__(player)
        self.has_save_potion = True
        self.has_poison_potion = True

    def get_private_notes(self, game_state: GameStateProtocol | None = None) -> list[str]:
        notes = super().get_private_notes(game_state)
        notes.append(f"解药可用：{'是' if self.has_save_potion else '否'}。")
        notes.append(f"毒药可用：{'是' if self.has_poison_potion else '否'}。")
        if game_state and game_state.werewolf_target:
            target = game_state.get_player(game_state.werewolf_target)
            if target:
                notes.append(f"今晚狼人目标是{target.name}。")
        return notes

    def get_config(self) -> RoleConfig:
        """获取女巫角色的配置。"""
        return RoleConfig(
            name="Witch",
            camp=Camp.VILLAGER,
            description=(
                "你是女巫。你有两瓶药：解药可以救活被狼人击杀的人，毒药可以毒死任意一名玩家。"
                "每瓶药整局游戏只能使用一次，请谨慎使用！"
            ),
            priority=ActionPriority.WITCH,
            can_act_night=True,
            can_act_day=False,
        )



class Hunter(Role):
    """猎人角色。

    被放逐或被狼人击杀时，可开枪带走另一名玩家。
    """


    def get_config(self) -> RoleConfig:
        """获取猎人角色的配置。"""
        return RoleConfig(
            name="Hunter",
            camp=Camp.VILLAGER,
            description=(
                "你是猎人。当你被击杀（被狼人或被投票出局）时，可以立即开枪带走另一名玩家。"
                "请谨慎选择你的目标！"
            ),
            priority=None,
            can_act_night=False,
            can_act_day=True,  # 死亡时触发
            max_uses=1,
        )


class Guard(Role):
    """守卫角色。

    每晚可保护一名玩家免受狼人攻击。
    不能连续两晚保护同一名玩家。
    """

    def __init__(self, player: PlayerProtocol) -> None:
        """初始化守卫角色。"""
        super().__init__(player)
        self.last_protected: str | None = None

    def get_private_notes(self, game_state: GameStateProtocol | None = None) -> list[str]:
        notes = super().get_private_notes(game_state)
        if self.last_protected and game_state:
            last_player = game_state.get_player(self.last_protected)
            if last_player:
                notes.append(f"你昨晚保护了{last_player.name}，今晚不能再次保护他/她。")
        return notes

    def get_config(self) -> RoleConfig:
        """获取守卫角色的配置。"""
        return RoleConfig(
            name="Guard",
            camp=Camp.VILLAGER,
            description=(
                "你是守卫。每晚可以保护一名玩家免受狼人攻击。"
                "被保护的玩家当夜不会被狼人击杀，但你不能连续两晚保护同一名玩家。"
            ),
            priority=ActionPriority.GUARD,
            can_act_night=True,
            can_act_day=False,
        )



class Idiot(Role):
    """白痴角色。

    被投票出局时亮明身份并存活，但失去投票权。
    """

    def __init__(self, player: PlayerProtocol) -> None:
        """初始化白痴角色。"""
        super().__init__(player)
        self.revealed = False

    def get_config(self) -> RoleConfig:
        """获取白痴角色的配置。"""
        return RoleConfig(
            name="Idiot",
            camp=Camp.VILLAGER,
            description=(
                "你是白痴。如果你在白天被投票出局，你会亮明身份并存活，但会失去剩余游戏的投票权。"
                "你仍然可能在夜间被狼人击杀。"
            ),
            priority=None,
            can_act_night=False,
            can_act_day=False,
        )



class Elder(Role):
    """长老角色。

    需承受两次狼人攻击才会死亡。若被好人投票出局，
    所有拥有特殊技能的好人将失去能力。
    """

    def __init__(self, player: PlayerProtocol) -> None:
        """初始化长老角色。"""
        super().__init__(player)
        self.lives = 2

    def get_config(self) -> RoleConfig:
        """获取长老角色的配置。"""
        return RoleConfig(
            name="Elder",
            camp=Camp.VILLAGER,
            description=(
                "你是长老。你有两条命，可以承受一次狼人攻击。"
                "但如果你在白天被投票出局，所有拥有特殊技能的好人将失去能力，作为对杀害长老的惩罚。"
            ),
            priority=None,
            can_act_night=False,
            can_act_day=False,
        )



class Knight(Role):
    """骑士角色。

    整局游戏中可在白天与一名玩家决斗一次。若目标是狼人则其死亡，
    否则骑士自己死亡。
    """

    def __init__(self, player: PlayerProtocol) -> None:
        """初始化骑士角色。"""
        super().__init__(player)
        self.has_dueled = False


    def get_config(self) -> RoleConfig:
        """获取骑士角色的配置。"""
        return RoleConfig(
            name="Knight",
            camp=Camp.VILLAGER,
            description=(
                "你是骑士。整局游戏中，你可以在白天投票前与一名玩家决斗一次。"
                "如果对方是狼人，对方立即死亡；如果对方不是狼人，你死亡。请明智使用你的能力！"
            ),
            priority=None,
            can_act_night=False,
            can_act_day=True,
            max_uses=1,
        )


class Magician(Role):
    """魔术师角色。

    整局游戏中可在夜晚交换两名玩家的身份一次。
    """

    def __init__(self, player: PlayerProtocol) -> None:
        """初始化魔术师角色。"""
        super().__init__(player)
        self.has_swapped = False


    def get_config(self) -> RoleConfig:
        """获取魔术师角色的配置。"""
        return RoleConfig(
            name="Magician",
            camp=Camp.VILLAGER,
            description=(
                "你是魔术师。整局游戏中，你可以在夜晚交换两名玩家的身份一次。"
                "被交换的玩家最初不会察觉。利用这个能力来迷惑狼人或保护重要角色！"
            ),
            priority=ActionPriority.GUARD,
            can_act_night=True,
            can_act_day=False,
            max_uses=1,
        )


class Cupid(Role):
    """丘比特角色。

    首夜选择两名玩家结为情侣。
    情侣同生共死、共同获胜。
    """

    def __init__(self, player: PlayerProtocol) -> None:
        """初始化丘比特角色。"""
        super().__init__(player)
        self.has_linked = False


    def get_config(self) -> RoleConfig:
        """获取丘比特角色的配置。"""
        return RoleConfig(
            name="Cupid",
            camp=Camp.VILLAGER,
            description=(
                "你是丘比特。仅在第一夜，你选择两名玩家结为恋人。"
                "恋人会知晓彼此的身份。如果一名恋人死亡，另一名会立即心碎殉情。"
                "无论原始阵营如何，恋人共同获胜。"
            ),
            priority=ActionPriority.CUPID,
            can_act_night=True,
            can_act_day=False,
            max_uses=1,
        )


class Raven(Role):
    """渡鸦角色。

    每晚可标记一名玩家，使其在次日投票阶段
    额外获得一票。
    """


    def get_config(self) -> RoleConfig:
        """获取渡鸦角色的配置。"""
        return RoleConfig(
            name="Raven",
            camp=Camp.VILLAGER,
            description=(
                "你是渡鸦。每晚你可以诅咒一名玩家。"
                "在次日的投票阶段，被诅咒的玩家从一开始就会额外获得一票反对。"
                "利用这个能力帮助淘汰狼人！"
            ),
            priority=ActionPriority.RAVEN,
            can_act_night=True,
            can_act_day=False,
        )


class GraveyardKeeper(Role):
    """守墓人角色。

    每晚可查验一名已死亡玩家是狼人还是好人。
    """


    def get_config(self) -> RoleConfig:
        """获取守墓人角色的配置。"""
        return RoleConfig(
            name="Graveyard Keeper",
            camp=Camp.VILLAGER,
            description=(
                "你是守墓人。每晚可以查验一名已死亡玩家的真实身份（狼人或好人）。"
                "这有助于你推断剩余的狼人可能是谁。"
            ),
            priority=ActionPriority.GRAVEYARD_KEEPER,
            can_act_night=True,
            can_act_day=False,
        )
