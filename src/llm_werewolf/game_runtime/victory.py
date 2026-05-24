from llm_werewolf.game_runtime.types import Camp, VictoryResult, PlayerProtocol, GameStateProtocol
from llm_werewolf.game_runtime.roles.names import (
    RoleNames,
    is_untransformed_blood_moon,
    player_camp_is,
    role_name_is,
)


class VictoryChecker:
    """检查狼人杀游戏的胜利条件。"""

    def __init__(self, game_state: GameStateProtocol) -> None:
        """初始化胜利判定器。

        Args:
            game_state: 当前游戏状态。
        """
        self.game_state = game_state

    @staticmethod
    def _is_white_lover_pair(player_a: PlayerProtocol, player_b: PlayerProtocol) -> bool:
        """情侣一方为狼、一方为好人（白狼情侣）。"""
        camps = {player_a.get_camp(), player_b.get_camp()}
        return Camp.WEREWOLF in camps and Camp.VILLAGER in camps

    def check_victory(self) -> VictoryResult:
        """检查是否已满足任一胜利条件。

        Returns:
            VictoryResult: 胜利判定结果。
        """
        special_result = self.check_special_victory()
        if special_result.has_winner:
            return special_result

        lover_result = self.check_lover_victory()
        if lover_result.has_winner:
            return lover_result

        werewolf_result = self.check_werewolf_victory()
        if werewolf_result.has_winner:
            return werewolf_result

        villager_result = self.check_villager_victory()
        if villager_result.has_winner:
            return villager_result

        return VictoryResult(has_winner=False, reason="Game continues")

    def check_werewolf_victory(self) -> VictoryResult:
        """检查狼人阵营是否获胜。

        狼人数量大于等于村民数量时狼人胜。
        注：未变身的血月使徒在胜利判定时不计入狼人。

        Returns:
            VictoryResult: 胜利判定结果。
        """
        alive_players = self.game_state.get_alive_players()

        # 统计狼人数量，排除未变身的血月使徒
        werewolf_count = 0
        for p in alive_players:
            if player_camp_is(p, Camp.WEREWOLF):
                if is_untransformed_blood_moon(p.role):
                    continue
                werewolf_count += 1

        villager_count = sum(
            1 for p in alive_players if player_camp_is(p, Camp.VILLAGER)
        )

        if werewolf_count >= villager_count and werewolf_count > 0:
            # 胜者列表包含所有狼人（含已变身血月使徒）
            werewolf_ids = []
            for p in alive_players:
                if player_camp_is(p, Camp.WEREWOLF):
                    if is_untransformed_blood_moon(p.role):
                        continue
                    werewolf_ids.append(p.player_id)

            return VictoryResult(
                has_winner=True,
                winner_camp="werewolf",
                winner_ids=werewolf_ids,
                reason=f"Werewolves ({werewolf_count}) equal or outnumber villagers ({villager_count})",
            )

        return VictoryResult(has_winner=False, reason="Werewolves have not won")

    def check_villager_victory(self) -> VictoryResult:
        """检查村民阵营是否获胜。

        所有狼人被消灭时村民胜。
        注：血月使徒（无论是否变身）在消灭判定时均视为狼人。

        Returns:
            VictoryResult: 胜利判定结果。
        """
        alive_players = self.game_state.get_alive_players()

        # 统计所有狼人（含血月使徒，即使未变身）
        werewolf_count = sum(
            1 for p in alive_players if player_camp_is(p, Camp.WEREWOLF)
        )

        if werewolf_count == 0:
            villager_ids = [
                p.player_id for p in alive_players if player_camp_is(p, Camp.VILLAGER)
            ]
            return VictoryResult(
                has_winner=True,
                winner_camp="villager",
                winner_ids=villager_ids,
                reason="All werewolves have been eliminated",
            )

        return VictoryResult(has_winner=False, reason="Villagers have not won")

    def check_lover_victory(self) -> VictoryResult:
        """检查同阵营情侣是否获胜（场上仅剩两名恋人且非白狼情侣）。

        Returns:
            VictoryResult: 胜利判定结果。
        """
        alive_players = self.game_state.get_alive_players()

        lovers = [p for p in alive_players if p.is_lover()]

        if len(lovers) == 2 and len(alive_players) == 2:
            if self._is_white_lover_pair(lovers[0], lovers[1]):
                return VictoryResult(has_winner=False, reason="White lover pair uses special victory")
            lover_ids = [p.player_id for p in lovers]
            return VictoryResult(
                has_winner=True,
                winner_camp="lover",
                winner_ids=lover_ids,
                reason="Only the lovers remain alive",
            )

        return VictoryResult(has_winner=False, reason="Lovers have not won")

    def check_white_lover_wolf_victory(self) -> VictoryResult:
        """白狼情侣：狼+好人恋人消灭其余所有人后双人获胜。"""
        alive_players = self.game_state.get_alive_players()
        lovers = [p for p in alive_players if p.is_lover()]

        if len(lovers) != 2 or len(alive_players) != 2:
            return VictoryResult(has_winner=False, reason="White lover wolves have not won")

        if not self._is_white_lover_pair(lovers[0], lovers[1]):
            return VictoryResult(has_winner=False, reason="Not a white lover wolf pair")

        lover_ids = [p.player_id for p in lovers]
        return VictoryResult(
            has_winner=True,
            winner_camp="white_lover_wolf",
            winner_ids=lover_ids,
            reason="White lover wolves eliminated all other players",
        )

    def check_thief_victory(self) -> VictoryResult:
        """盗贼选身份后随当前阵营获胜（仍走常规阵营判定，此处仅标记无独立终局）。"""
        for player in self.game_state.get_alive_players():
            if not role_name_is(player.role, RoleNames.THIEF):
                continue
            if not getattr(player.role, "has_chosen", False):
                continue
            camp = player.get_camp()
            if camp == Camp.WEREWOLF:
                return self.check_werewolf_victory()
            if camp == Camp.VILLAGER:
                return self.check_villager_victory()
        return VictoryResult(has_winner=False, reason="Thief has not won")

    def check_special_victory(self) -> VictoryResult:
        """检查特殊胜利条件（白狼情侣、盗贼随阵营等）。"""
        white_lover = self.check_white_lover_wolf_victory()
        if white_lover.has_winner:
            return white_lover

        thief = self.check_thief_victory()
        if thief.has_winner:
            return thief

        return VictoryResult(has_winner=False, reason="No special victory")

    def get_winner(self) -> VictoryResult:
        """获取当前胜者（若有）。

        Returns:
            VictoryResult: 胜利结果。
        """
        return self.check_victory()

    def is_game_over(self) -> bool:
        return self.check_victory().has_winner

    def get_winning_players(self) -> list[PlayerProtocol]:
        """获取获胜玩家列表。

        Returns:
            list[PlayerProtocol]: 获胜玩家列表；无胜者时为空。
        """
        result = self.check_victory()
        if not result.has_winner:
            return []

        return [
            self.game_state.get_player(player_id)
            for player_id in result.winner_ids
            if self.game_state.get_player(player_id) is not None
        ]

    def get_losing_players(self) -> list[PlayerProtocol]:
        """获取失败玩家列表。

        Returns:
            list[PlayerProtocol]: 失败玩家列表；无胜者时为空。
        """
        result = self.check_victory()
        if not result.has_winner:
            return []

        winning_ids = set(result.winner_ids)
        return [p for p in self.game_state.players if p.player_id not in winning_ids]
