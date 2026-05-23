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
            f"你的狼队友：{', '.join(werewolf_names)}。\n"
            f"所有狼人将在今晚投票决定击杀目标。\n"
            f"作为{role_name}，请选择要投票击杀的目标。"
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
            notes.append(f"存活的狼队友：{', '.join(teammates)}。")
        return notes

    def get_config(self) -> RoleConfig:
        """获取狼人角色的配置。"""
        return RoleConfig(
            name="Werewolf",
            camp=Camp.WEREWOLF,
            description=(
                "你是狼人。每晚与其他狼人一起醒来，集体选择一名玩家击杀。"
                "你的目标是让狼人数量不少于好人数量。"
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
                "你是狼王。每晚与其他狼人一起击杀玩家。"
                "当你被放逐或被猎人带走时，可以立即开枪带走另一名玩家。"
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
                "你是白狼王。每晚与其他狼人一起击杀好人。"
                "此外，每隔一晚你可以独自醒来并选择击杀另一名狼人。"
                "你的最终目标可能是成为最后存活的狼人。"
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
                "你是狼美人。每晚与其他狼人一起击杀好人。"
                "此外，每晚你可以魅惑一名玩家。如果你死亡，被魅惑的玩家会立即殉情。"
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
                "你是守卫狼。每晚与其他狼人一起击杀好人。"
                "此外，每晚你可以选择保护一名狼队友，使其当夜不会被击杀。"
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
                "你是隐狼。每晚与其他狼人一起击杀好人。"
                "你的特殊能力是：预言家查验你时会显示为好人，这让你更难被发现。"
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
                "你是血月使徒。你支持狼人阵营，但最初不与狼队一起醒来。"
                "每局游戏一次，当所有狼人死亡后，你可以变身为真正的狼人并开始击杀。"
                "变身前，预言家查验你时会显示为好人。"
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
                "你是梦魇狼。每晚与其他狼人一起击杀好人。"
                "此外，每晚你可以选择封锁一名玩家，使其当夜无法使用技能。"
            ),
            priority=ActionPriority.WEREWOLF,
            can_act_night=True,
            can_act_day=False,
        )
