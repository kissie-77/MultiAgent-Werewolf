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
                "You are a Villager. You have no special abilities, but you can vote "
                "during the day to eliminate suspected werewolves. Use your deduction "
                "and persuasion skills to help the village win!"
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
                result = "werewolf" if player.get_camp() == Camp.WEREWOLF else "villager"
                checked_info.append(f"Round {round_num}: {player.name} was confirmed as {result}.")

        return notes + checked_info

    def get_config(self) -> RoleConfig:
        """获取预言家角色的配置。"""
        return RoleConfig(
            name="Seer",
            camp=Camp.VILLAGER,
            description=(
                "You are the Seer (Prophet). Each night, you can check one player "
                "to learn their true identity (werewolf or villager). Use this information "
                "wisely to guide the village, but be careful not to reveal yourself too early."
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
        notes.append(f"Save potion available: {'yes' if self.has_save_potion else 'no'}.")
        notes.append(f"Poison potion available: {'yes' if self.has_poison_potion else 'no'}.")
        if game_state and game_state.werewolf_target:
            target = game_state.get_player(game_state.werewolf_target)
            if target:
                notes.append(f"Tonight's werewolf target is {target.name}.")
        return notes

    def get_config(self) -> RoleConfig:
        """获取女巫角色的配置。"""
        return RoleConfig(
            name="Witch",
            camp=Camp.VILLAGER,
            description=(
                "You are the Witch. You have two potions: a save potion to resurrect someone "
                "killed by werewolves, and a poison potion to kill any player. "
                "Each potion can only be used once per game. Use them wisely!"
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
                "You are the Hunter. When you are eliminated (by werewolves at night or "
                "by voting during the day), you can immediately shoot and eliminate another "
                "player before you die. Choose your target carefully!"
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
                notes.append(f"You protected {last_player.name} last night and cannot protect them again tonight.")
        return notes

    def get_config(self) -> RoleConfig:
        """获取守卫角色的配置。"""
        return RoleConfig(
            name="Guard",
            camp=Camp.VILLAGER,
            description=(
                "You are the Guard. Each night, you can protect one player from werewolf attacks. "
                "The protected player cannot be killed by werewolves that night. "
                "However, you cannot protect the same player two nights in a row."
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
                "You are the Idiot. If you are voted out during the day, you reveal your "
                "identity card and survive the elimination. However, you lose your right to vote "
                "for the rest of the game. You can still be killed by werewolves at night."
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
                "You are the Elder. You have two lives and can survive one werewolf attack. "
                "However, if you are eliminated by voting during the day, all villagers with "
                "special abilities lose their powers as punishment for killing an elder."
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
                "You are the Knight. Once per game during the day, you can challenge a player "
                "to a duel before voting. If they are a werewolf, they die immediately. "
                "If they are not a werewolf, you die instead. Use this power wisely!"
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
                "You are the Magician. Once per game, you can swap the roles of two players "
                "at night. The players will not be aware of the swap initially. "
                "Use this to confuse the werewolves or save valuable roles!"
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
                "You are Cupid. On the first night only, you choose two players to become lovers. "
                "The lovers will learn each other's identities. If one lover dies, the other dies "
                "immediately from heartbreak. Lovers win together regardless of their original camps."
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
                "You are the Raven. Each night, you can mark a player with a curse. "
                "During the next day's voting, that player will have one extra vote against them "
                "from the start. Use this to help eliminate werewolves!"
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
                "You are the Graveyard Keeper. Each night, you can check the true identity "
                "of one dead player (werewolf or villager). This helps you piece together "
                "who the remaining werewolves might be."
            ),
            priority=ActionPriority.GRAVEYARD_KEEPER,
            can_act_night=True,
            can_act_day=False,
        )
