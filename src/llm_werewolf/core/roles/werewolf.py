from llm_werewolf.core.types import (
    Camp,
    RoleConfig,
    ActionPriority,
    PlayerProtocol,
    GameStateProtocol,
)
from llm_werewolf.core.roles.base import Role


def build_werewolf_team_context(
    role: Role,
    game_state: GameStateProtocol,
    werewolf_names: list[str],
) -> str:
    private_notes = role.get_private_notes(game_state)
    role_name = role.name
    return "\n\n".join(filter(None, [
        *private_notes,
        (
            f"You are working with these werewolves: {', '.join(werewolf_names)}.\n"
            f"All werewolves will vote on who to eliminate tonight.\n"
            f"作为{role_name}，请选择要投票击杀的好人目标。"
        ),
    ]))


class Werewolf(Role):
    """标准狼人角色。

    狼人夜晚醒来并集体选择一名受害者击杀。
    当狼人数量等于或超过好人时获胜。
    """

    def get_private_notes(self, game_state: GameStateProtocol | None = None) -> list[str]:
        notes = super().get_private_notes(game_state)
        if game_state is None:
            return notes

        teammates = [
            player.name
            for player in game_state.get_players_by_camp(Camp.WEREWOLF)
            if player.player_id != self.player.player_id and player.is_alive()
        ]
        if teammates:
            notes.append(f"Your living werewolf teammates: {', '.join(teammates)}.")
        return notes

    def get_config(self) -> RoleConfig:
        """获取狼人角色的配置。"""
        return RoleConfig(
            name="Werewolf",
            camp=Camp.WEREWOLF,
            description=(
                "You are a Werewolf. Each night, you wake up with other werewolves "
                "and collectively choose a villager to eliminate. Your goal is to "
                "outnumber the villagers."
            ),
            priority=ActionPriority.WEREWOLF,
            can_act_night=True,
            can_act_day=False,
        )



class AlphaWolf(Werewolf):
    """狼王（Alpha Wolf）角色。

    与普通狼人类似，但被放逐或猎人带走时，
    可以再带走一名玩家。
    """


    def get_config(self) -> RoleConfig:
        """获取狼王角色的配置。"""
        return RoleConfig(
            name="Alpha Wolf",
            camp=Camp.WEREWOLF,
            description=(
                "You are the Alpha Wolf. You wake up with other werewolves each night "
                "to kill a villager. When you are eliminated (by voting or hunter), "
                "you can immediately shoot and eliminate another player before you die."
            ),
            priority=ActionPriority.WEREWOLF,
            can_act_night=True,
            can_act_day=True,  # 死亡时可开枪
        )


class WhiteWolf(Role):
    """白狼王角色。

    每两夜可击杀一名狼队友的狼人。
    白狼王往往试图成为最后存活的狼人。
    """


    def get_config(self) -> RoleConfig:
        """获取白狼王角色的配置。"""
        return RoleConfig(
            name="White Wolf",
            camp=Camp.WEREWOLF,
            description=(
                "You are the White Wolf. You wake up with other werewolves to kill villagers. "
                "Additionally, every other night, you wake up alone and can choose to kill "
                "another werewolf. Your ultimate goal may be to be the last werewolf standing."
            ),
            priority=ActionPriority.WHITE_WOLF,
            can_act_night=True,
            can_act_day=False,
        )


class WolfBeauty(Role):
    """狼美人角色。

    每晚可魅惑一名玩家的狼人。狼美人死亡时，
    被魅惑的玩家也会殉情。
    """

    def __init__(self, player: PlayerProtocol) -> None:
        """初始化狼美人角色。"""
        super().__init__(player)
        self.charmed_player: str | None = None


    def get_config(self) -> RoleConfig:
        """获取狼美人角色的配置。"""
        return RoleConfig(
            name="Wolf Beauty",
            camp=Camp.WEREWOLF,
            description=(
                "You are the Wolf Beauty. You wake up with other werewolves to kill villagers. "
                "Each night, you can also charm a player. If you die, the charmed player "
                "dies with you immediately."
            ),
            priority=ActionPriority.WEREWOLF,
            can_act_night=True,
            can_act_day=False,
        )


class GuardianWolf(Role):
    """守卫狼角色。

    每晚可保护一名狼队友免受击杀的狼人。
    """


    def get_config(self) -> RoleConfig:
        """获取守卫狼角色的配置。"""
        return RoleConfig(
            name="Guardian Wolf",
            camp=Camp.WEREWOLF,
            description=(
                "You are the Guardian Wolf. You wake up with other werewolves to kill villagers. "
                "Additionally, you can choose to protect one werewolf each night. "
                "The protected werewolf cannot be eliminated that night."
            ),
            priority=ActionPriority.GUARD,
            can_act_night=True,
            can_act_day=False,
        )


class HiddenWolf(Role):
    """隐狼角色。

    被预言家查验时显示为好人的狼人。
    """


    def get_config(self) -> RoleConfig:
        """获取隐狼角色的配置。"""
        return RoleConfig(
            name="Hidden Wolf",
            camp=Camp.WEREWOLF,
            description=(
                "You are the Hidden Wolf. You wake up with other werewolves to kill villagers. "
                "Your special ability is that you appear as a villager when checked by the Seer. "
                "This makes you much harder to detect."
            ),
            priority=ActionPriority.WEREWOLF,
            can_act_night=True,
            can_act_day=False,
        )


class BloodMoonApostle(Role):
    """血月使徒角色。

    不与狼队同醒的狼人支持者，但与狼人共同获胜。
    整局游戏中可一次变身为真正的狼人。
    """

    def __init__(self, player: PlayerProtocol) -> None:
        """初始化血月使徒角色。"""
        super().__init__(player)
        self.transformed = False


    def get_config(self) -> RoleConfig:
        """获取血月使徒角色的配置。"""
        return RoleConfig(
            name="Blood Moon Apostle",
            camp=Camp.WEREWOLF,
            description=(
                "You are the Blood Moon Apostle. You support the werewolves but don't wake up "
                "with them initially. Once per game, if all werewolves are dead, you transform "
                "into a werewolf and can start killing. You appear as a villager to the Seer "
                "until transformed."
            ),
            priority=ActionPriority.WEREWOLF,  # 变身后与狼人一同行动
            can_act_night=True,  # 每夜需检查变身条件
            can_act_day=False,
            max_uses=None,  # 变身后每夜均可行动
        )


class NightmareWolf(Role):
    """梦魇狼角色。

    可封锁一名玩家使其当夜无法使用技能的狼人。
    """


    def get_config(self) -> RoleConfig:
        """获取梦魇狼角色的配置。"""
        return RoleConfig(
            name="Nightmare Wolf",
            camp=Camp.WEREWOLF,
            description=(
                "You are the Nightmare Wolf. You wake up with other werewolves to kill villagers. "
                "Additionally, you can choose one player each night to block their ability. "
                "That player cannot use their role ability that night."
            ),
            priority=ActionPriority.WEREWOLF,
            can_act_night=True,
            can_act_day=False,
        )
