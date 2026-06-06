"""游戏引擎的死亡处理逻辑。"""

from collections.abc import Callable

from llm_werewolf.game_runtime.types import Camp, EventType, PlayerProtocol
from llm_werewolf.game_runtime.i18n.locale import Locale
from llm_werewolf.game_runtime.roles.names import RoleNames
from llm_werewolf.game_runtime.state.game_state import GameState
from llm_werewolf.game_runtime.rules.death_abilities import DEATH_ABILITY_ROLE_NAMES


class DeathHandlerMixin:
    """处理死亡相关游戏逻辑的 Mixin。"""

    game_state: GameState | None
    locale: Locale
    _log_event: Callable

    def _handle_lover_death(self, dead_player: PlayerProtocol) -> None:
        """处理玩家死亡时情侣伴侣的连带死亡。

        情侣死亡不再递归触发新的情侣链（防止循环），但会将伴侣加入死亡集合，
        使 _handle_death_abilities 能在后续统一处理其死亡能力（猎人/白狼王）。

        Args:
            dead_player: 已死亡的玩家。
        """
        if not self.game_state or not dead_player.is_lover() or not dead_player.lover_partner_id:
            return

        partner = self.game_state.get_player(dead_player.lover_partner_id)
        if partner and partner.is_alive():
            partner.kill()
            if self.game_state.phase.value == "night":
                self.game_state.night_deaths.add(partner.player_id)
            else:
                self.game_state.day_deaths.add(partner.player_id)
            self._log_event(
                EventType.LOVER_DIED,
                self.locale.get("died_of_heartbreak", player=partner.name),
                data={"player_id": partner.player_id},
            )
            # 情侣伴侣本身若也是恋人（三角恋边缘情况）不再递归，避免死循环。
            # 但若伴侣也是某人的情侣且对方存活，仍需处理——在下一次 _handle_lover_death 调用时处理。

    def _handle_wolf_beauty_charm_death(self, wolf_beauty: PlayerProtocol) -> None:
        """处理狼美人死亡时被魅惑玩家的连带死亡。

        Args:
            wolf_beauty: 已死亡的狼美人玩家。
        """
        if not self.game_state:
            return

        charmed_id = self.game_state.wolf_beauty_charmed or getattr(
            wolf_beauty.role, "charmed_player", None
        )
        if not charmed_id:
            return

        charmed = self.game_state.get_player(charmed_id)
        if charmed and charmed.is_alive():
            charmed.kill()
            if self.game_state.phase.value == "night":
                self.game_state.night_deaths.add(charmed.player_id)
            else:
                self.game_state.day_deaths.add(charmed.player_id)
            self._log_event(
                EventType.PLAYER_DIED,
                self.locale.get(
                    "died_from_charm", player=charmed.name, wolf_beauty=wolf_beauty.name
                ),
                data={"player_id": charmed.player_id, "reason": "wolf_beauty_charm"},
            )

    def _handle_elder_penalty(self) -> None:
        """长老被投票出局时禁用所有村民技能。"""
        if not self.game_state:
            return

        for player in self.game_state.players:
            if player.get_camp() == Camp.VILLAGER and player.is_alive():
                player.role.disabled = True

        self._log_event(
            EventType.ROLE_REVEALED,
            self.locale.get("elder_penalty"),
            data={"reason": "elder_penalty"},
        )

    def _handle_werewolf_kill(self, target: PlayerProtocol) -> list[str]:
        """处理狼人击杀及其后果。

        Args:
            target: 被击杀的目标玩家。

        Returns:
            list[str]: 描述击杀过程的消息。
        """
        if not self.game_state:
            return []

        messages: list[str] = []
        target_id = target.player_id
        guard_id = self.game_state.guard_protected
        witch_save_id = self.game_state.witch_saved_target

        # 毒奶：守卫与女巫同夜同时作用于刀口，目标仍会死亡
        if guard_id == target_id and witch_save_id == target_id:
            target.kill()
            self.game_state.night_deaths.add(target_id)
            self.game_state.death_causes[target_id] = "guard_witch_conflict"
            self._log_event(
                EventType.PLAYER_DIED,
                self.locale.get("killed_by_guard_witch_conflict", player=target.name),
                data={"player_id": target_id, "reason": "guard_witch_conflict"},
            )
            if target.is_lover() and target.lover_partner_id:
                self._handle_lover_death(target)
        elif target_id in (witch_save_id, guard_id):
            pass
        elif hasattr(target.role, "lives") and target.role.lives > 1:
            target.role.lives -= 1
            self._log_event(
                EventType.MESSAGE,
                self.locale.get("elder_attacked", player=target.name),
                data={"player_id": target.player_id, "reason": "elder_survived"},
            )
        else:
            target.kill()
            self.game_state.night_deaths.add(target.player_id)

            self._log_event(
                EventType.PLAYER_DIED,
                self.locale.get("killed_by_werewolves", player=target.name),
                data={"player_id": target.player_id},
            )

            if target.is_lover() and target.lover_partner_id:
                self._handle_lover_death(target)

        return messages

    async def _handle_sheriff_badge_transfer(self) -> list[str]:
        """处理警长死亡时的警徽移交。

        Returns:
            list[str]: 警徽移交产生的消息。
        """
        if not self.game_state:
            return []

        messages: list[str] = []
        all_deaths = self.game_state.night_deaths | self.game_state.day_deaths

        # 检查警长是否死亡
        if self.game_state.sheriff_id and self.game_state.sheriff_id in all_deaths:
            sheriff = self.game_state.get_player(self.game_state.sheriff_id)
            if not sheriff or sheriff.player_id in self.game_state.death_abilities_used:
                return messages

            self.game_state.death_abilities_used.add(sheriff.player_id)

            self._log_event(
                EventType.MESSAGE,
                self.locale.get("sheriff_died_transfer", sheriff=sheriff.name),
                data={"player_id": sheriff.player_id},
            )

            # 询问警长是否移交警徽
            possible_targets = self.game_state.get_alive_players()
            if not possible_targets or not sheriff.agent:
                # 无人可移交，或无 agent —— 撕毁警徽
                self.game_state.remove_sheriff()
                self._log_event(
                    EventType.SHERIFF_BADGE_TORN,
                    self.locale.get("sheriff_badge_torn", sheriff=sheriff.name),
                    data={"player_id": sheriff.player_id},
                )
                return messages

            from llm_werewolf.game_runtime.prompts.actions import (
                EngineContexts,
                ActionDescriptions,
            )

            context = (
                EngineContexts.sheriff_died(sheriff.name)
                + self.locale.get("sheriff_transfer_note")
                + "\n"
                + self.locale.get(
                    "sheriff_transfer_targets", targets=", ".join(p.name for p in possible_targets)
                )
                + "\n"
            )

            interaction = self.game_state.require_phase_interaction()
            target = await interaction.request_seat_choice(
                sheriff,
                sheriff.agent,
                "警长",
                ActionDescriptions.TRANSFER_BADGE,
                possible_targets,
                allow_skip=True,
                additional_context=context,
                fallback_random=False,
            )

            if target:
                # 将警徽移交给目标
                self.game_state.set_sheriff(target.player_id)
                self._log_event(
                    EventType.SHERIFF_BADGE_TRANSFERRED,
                    self.locale.get(
                        "sheriff_badge_transferred", sheriff=sheriff.name, target=target.name
                    ),
                    data={"from_player_id": sheriff.player_id, "to_player_id": target.player_id},
                )
            else:
                # 撕毁警徽
                self.game_state.remove_sheriff()
                self._log_event(
                    EventType.SHERIFF_BADGE_TORN,
                    self.locale.get("sheriff_badge_torn", sheriff=sheriff.name),
                    data={"player_id": sheriff.player_id},
                )

        return messages

    async def _process_hunter_or_alpha_death(self, player: PlayerProtocol) -> list[str]:
        """处理猎人或白狼王死亡技能。

        Args:
            player: 拥有死亡技能的玩家。

        Returns:
            list[str]: 技能执行产生的消息。
        """
        if not self.game_state:
            return []

        messages: list[str] = []
        possible_targets = self.game_state.get_alive_players()
        if not possible_targets:
            return messages

        role_name = player.get_role_name()
        self._log_event(
            EventType.MESSAGE,
            self.locale.get("death_ability_active", player=player.name, role=role_name),
            data={"player_id": player.player_id, "role": role_name},
        )

        # 从 agent 获取目标；失败时不替玩家随机选择，避免系统静默改变胜负结果。
        target = None
        if player.agent:
            interaction = self.game_state.require_phase_interaction()
            target = await interaction.request_seat_choice(
                player,
                player.agent,
                role_name,
                "临死前选择带走的玩家",
                possible_targets,
                allow_skip=False,
                additional_context=self.locale.get("death_skill_context", player=player.name),
                fallback_random=False,
            )

        if target and target.is_alive():
            self._execute_death_shot(player, target, role_name, messages)

        return messages

    def _execute_death_shot(
        self, shooter: PlayerProtocol, target: PlayerProtocol, role_name: str, messages: list[str]
    ) -> None:
        """执行死亡开枪并处理后果。

        Args:
            shooter: 开枪的玩家。
            target: 目标玩家。
            role_name: 开枪者角色名称。
            messages: 用于追加消息的列表。
        """
        if not self.game_state:
            return

        target.kill()
        if self.game_state.phase.value == "night":
            self.game_state.night_deaths.add(target.player_id)
        else:
            self.game_state.day_deaths.add(target.player_id)

        # 根据角色记录相应事件
        event_msg = (
            self.locale.get("hunter_shoots", hunter=shooter.name, target=target.name)
            if shooter.role.name == RoleNames.HUNTER
            else self.locale.get("alpha_wolf_shoots", alpha=shooter.name, target=target.name)
            if shooter.role.name == RoleNames.ALPHA_WOLF
            else self.locale.get("white_wolf_shoots", white_wolf=shooter.name, target=target.name)
        )

        self._log_event(
            EventType.HUNTER_REVENGE,
            event_msg,
            data={
                "shooter_id": shooter.player_id,
                "target_id": target.player_id,
                "role": role_name,
            },
        )

        # 处理情侣死亡
        if target.is_lover() and target.lover_partner_id:
            self._handle_lover_death(target)

    async def _handle_death_abilities(self) -> list[str]:
        """处理死亡时触发的技能（猎人、白狼王）。

        Returns:
            list[str]: 死亡技能产生的消息。
        """
        if not self.game_state:
            return []

        # 优先处理警徽移交
        sheriff_messages = await self._handle_sheriff_badge_transfer()

        messages = []
        all_deaths = self.game_state.night_deaths | self.game_state.day_deaths

        for player_id in all_deaths:
            if player_id in self.game_state.death_abilities_used:
                continue
            player = self.game_state.get_player(player_id)
            if not player:
                continue

            if player.role.name in DEATH_ABILITY_ROLE_NAMES:
                # 检查是否被毒杀
                death_cause = self.game_state.death_causes.get(player_id)
                if death_cause == "witch_poison":
                    self._log_event(
                        EventType.MESSAGE,
                        self.locale.get("poisoned_no_ability", player=player.name),
                        data={"player_id": player_id},
                    )
                    self.game_state.death_abilities_used.add(player_id)
                    continue

                self.game_state.death_abilities_used.add(player_id)
                ability_messages = await self._process_hunter_or_alpha_death(player)
                messages.extend(ability_messages)

        messages.extend(sheriff_messages)
        return messages

    def _resolve_witch_poison_death(self) -> None:
        """结算女巫毒杀死亡及情侣连带后果。"""
        if not self.game_state or not self.game_state.witch_poison_target:
            return

        target = self.game_state.get_player(self.game_state.witch_poison_target)
        if not target or not target.is_alive():
            return

        target.kill()
        self.game_state.night_deaths.add(target.player_id)
        self.game_state.death_causes[target.player_id] = "witch_poison"

        self._log_event(
            EventType.PLAYER_DIED,
            self.locale.get("witch_poisoned_target", target=target.name),
            data={
                "player_id": target.player_id,
                "reason": "witch_poison",
                "cause": "witch_poison",
            },
        )

        # 处理情侣死亡
        if target.is_lover() and target.lover_partner_id:
            self._handle_lover_death(target)

    def _resolve_wolf_beauty_charm_deaths(self) -> None:
        """结算狼美人死亡时被魅惑玩家的连带死亡。"""
        if not self.game_state:
            return

        charmed_id = self.game_state.wolf_beauty_charmed
        if not charmed_id:
            return

        # 检查是否有狼美人已死亡
        all_deaths = self.game_state.night_deaths | self.game_state.day_deaths
        wolf_beauty_player = None
        for player in self.game_state.players:
            if (
                hasattr(player.role, "charmed_player")
                and not player.is_alive()
                and player.player_id in all_deaths
            ):
                wolf_beauty_player = player
                break

        if wolf_beauty_player is None:
            return

        charmed = self.game_state.get_player(charmed_id)
        if charmed and charmed.is_alive():
            charmed.kill()
            self.game_state.night_deaths.add(charmed.player_id)
            self._log_event(
                EventType.PLAYER_DIED,
                self.locale.get(
                    "died_from_charm", player=charmed.name, wolf_beauty=wolf_beauty_player.name
                ),
                data={"player_id": charmed.player_id, "reason": "wolf_beauty_charm"},
            )
            # 被魅惑者若是情侣，其伴侣也随之死亡（死亡链传播）
            if charmed.is_lover() and charmed.lover_partner_id:
                self._handle_lover_death(charmed)

    async def resolve_deaths(self) -> list[str]:
        """根据夜间行动结算所有死亡。

        Returns:
            list[str]: 描述死亡情况的消息。
        """
        if not self.game_state:
            return []

        messages = []

        # 处理狼人击杀
        if self.game_state.werewolf_target:
            target = self.game_state.get_player(self.game_state.werewolf_target)
            if target:
                messages.extend(self._handle_werewolf_kill(target))
                if not target.is_alive() and target.player_id not in self.game_state.death_causes:
                    self.game_state.death_causes[target.player_id] = "werewolf"

        # 处理女巫毒杀
        self._resolve_witch_poison_death()

        # 处理狼美人魅惑连带死亡
        self._resolve_wolf_beauty_charm_deaths()

        # 处理死亡技能
        death_ability_messages = await self._handle_death_abilities()
        messages.extend(death_ability_messages)

        return messages
