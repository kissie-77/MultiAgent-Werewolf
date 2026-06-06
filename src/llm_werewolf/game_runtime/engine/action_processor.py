from typing import ClassVar
from collections.abc import Callable

from llm_werewolf.game_runtime.types import Camp, EventType
from llm_werewolf.game_runtime.i18n.locale import Locale
from llm_werewolf.game_runtime.roles.names import seer_apparent_camp
from llm_werewolf.game_runtime.actions.base import Action
from llm_werewolf.game_runtime.actions.villager import (
    CupidLinkAction,
    RavenMarkAction,
    SeerCheckAction,
    WitchSaveAction,
    WitchPoisonAction,
    GuardProtectAction,
    MagicianSwapAction,
    GraveyardKeeperCheckAction,
)
from llm_werewolf.game_runtime.actions.werewolf import (
    WhiteWolfKillAction,
    WolfBeautyCharmAction,
    NightmareWolfBlockAction,
    GuardianWolfProtectAction,
)
from llm_werewolf.game_runtime.state.game_state import GameState
from llm_werewolf.game_runtime.registries.action_registry import get_action_priority


class ActionProcessorMixin:
    """处理游戏行动的 Mixin。"""

    game_state: GameState | None
    locale: Locale
    _log_event: Callable
    _ACTION_LOGGER_NAMES: ClassVar[tuple[tuple[type[Action], str], ...]] = (
        (GuardProtectAction, "_log_guard_action"),
        (WitchSaveAction, "_log_witch_save_action"),
        (WitchPoisonAction, "_log_witch_poison_action"),
        (SeerCheckAction, "_log_seer_action"),
        (CupidLinkAction, "_log_cupid_action"),
        (WhiteWolfKillAction, "_log_white_wolf_action"),
        (WolfBeautyCharmAction, "_log_wolf_beauty_action"),
        (NightmareWolfBlockAction, "_log_nightmare_block_action"),
        (GuardianWolfProtectAction, "_log_guardian_wolf_action"),
        (MagicianSwapAction, "_log_magician_swap_action"),
        (RavenMarkAction, "_log_raven_action"),
        (GraveyardKeeperCheckAction, "_log_graveyard_keeper_action"),
    )

    @staticmethod
    def _get_action_priority(action: Action) -> int:
        """获取行动优先级。数值越大优先级越高（越先执行）。"""
        return get_action_priority(action.__class__.__name__)

    @staticmethod
    def _decision_data(action: Action) -> dict:
        """返回行动执行者最新解析的决策元数据。"""
        action_metadata = getattr(action, "_decision_metadata", None)
        if action_metadata:
            return {"decision": action_metadata}
        actor = getattr(action, "actor", None)
        agent = getattr(actor, "agent", None)
        metadata = getattr(agent, "_last_decision_metadata", None)
        if not metadata:
            return {}
        return {"decision": metadata}

    def _is_actor_blocked(self, action: Action) -> bool:
        """检查行动执行者是否被梦魇狼封锁。

        Args:
            action: 待检查的行动。

        Returns:
            bool: 若被封锁则为 True，否则为 False。
        """
        if not self.game_state or not self.game_state.nightmare_blocked:
            return False

        if not hasattr(action, "actor"):
            return False

        if isinstance(action, NightmareWolfBlockAction):
            return False

        return action.actor.player_id == self.game_state.nightmare_blocked

    def _log_guard_action(self, action: GuardProtectAction) -> None:
        """记录守卫保护行动。"""
        self._log_event(
            EventType.GUARD_PROTECTED,
            self.locale.get("guard_protected", target=action.target.name),
            data={
                "player_id": action.actor.player_id,
                "target_id": action.target.player_id,
                **self._decision_data(action),
            },
        )
        if action.actor.agent and self.game_state:
            action.actor.agent.add_decision(
                f"Round {self.game_state.round_number}: Protected {action.target.name}"
            )

    def _log_witch_save_action(self, action: WitchSaveAction) -> None:
        """记录女巫救人行动。"""
        self._log_event(
            EventType.WITCH_SAVED,
            self.locale.get("witch_saved", target=action.target.name),
            data={
                "player_id": action.actor.player_id,
                "target_id": action.target.player_id,
                **self._decision_data(action),
            },
        )
        if action.actor.agent and self.game_state:
            action.actor.agent.add_decision(
                f"Round {self.game_state.round_number}: Used save potion on {action.target.name}"
            )

    def _log_witch_poison_action(self, action: WitchPoisonAction) -> None:
        """记录女巫毒人行动。"""
        self._log_event(
            EventType.WITCH_POISON_USED,
            self.locale.get("witch_uses_poison", target=action.target.name),
            data={
                "player_id": action.actor.player_id,
                "target_id": action.target.player_id,
                **self._decision_data(action),
            },
        )
        if action.actor.agent and self.game_state:
            action.actor.agent.add_decision(
                f"Round {self.game_state.round_number}: Used poison on {action.target.name}"
            )

    def _log_seer_action(self, action: SeerCheckAction) -> None:
        """记录预言家查验行动。"""
        apparent = seer_apparent_camp(action.target)
        result = (
            ("狼人" if apparent == Camp.WEREWOLF else "好人")
            if getattr(self.locale, "language", "").startswith("zh")
            else apparent.value
        )
        self._log_event(
            EventType.SEER_CHECKED,
            self.locale.get("seer_checked", target=action.target.name, result=result),
            data={
                "player_id": action.actor.player_id,
                "target_id": action.target.player_id,
                "result": apparent.value,
                **self._decision_data(action),
            },
        )
        if action.actor.agent and self.game_state:
            action.actor.agent.add_decision(
                f"Round {self.game_state.round_number}: Checked {action.target.name}, "
                f"result: {apparent.value}"
            )
        if self.game_state and getattr(self.game_state, "belief_log", None) is not None:
            from llm_werewolf.strategy.belief.updater import (
                apply_seer_check,
                ensure_agent_belief_state,
            )
            from llm_werewolf.game_runtime.support.seat import get_player_seat

            alive = self.game_state.get_alive_players()
            state = ensure_agent_belief_state(action.actor, alive)
            target_seat = get_player_seat(action.target)
            if target_seat is not None:
                apply_seer_check(
                    state,
                    target_seat=target_seat,
                    is_werewolf=action.target.get_camp() == Camp.WEREWOLF,
                )
            from llm_werewolf.strategy.belief.format import sync_player_belief_memory

            sync_player_belief_memory(
                action.actor,
                alive=alive,
                wolf_camp_mind=getattr(self.game_state, "wolf_camp_mind", None),
            )

    def _log_cupid_action(self, action: CupidLinkAction) -> None:
        """记录丘比特连线行动。"""
        self._log_event(
            EventType.LOVERS_LINKED,
            self.locale.get(
                "cupid_links", player1=action.target1.name, player2=action.target2.name
            ),
            data={
                "player_id": action.actor.player_id,
                "player1_id": action.target1.player_id,
                "player2_id": action.target2.player_id,
            },
        )
        if action.actor.agent and self.game_state:
            action.actor.agent.add_decision(
                f"Round {self.game_state.round_number}: Linked {action.target1.name} and {action.target2.name} as lovers"
            )

    def _log_white_wolf_action(self, action: WhiteWolfKillAction) -> None:
        """记录白狼王击杀行动。"""
        self._log_event(
            EventType.WHITE_WOLF_KILLED,
            self.locale.get("white_wolf_kills", target=action.target.name),
            data={
                "player_id": action.actor.player_id,
                "target_id": action.target.player_id,
                **self._decision_data(action),
            },
        )

    def _log_wolf_beauty_action(self, action: WolfBeautyCharmAction) -> None:
        """记录狼美人魅惑行动。"""
        self._log_event(
            EventType.WOLF_BEAUTY_CHARMED,
            self.locale.get("wolf_beauty_charms", target=action.target.name),
            data={
                "player_id": action.actor.player_id,
                "target_id": action.target.player_id,
                **self._decision_data(action),
            },
        )

    def _log_nightmare_block_action(self, action: NightmareWolfBlockAction) -> None:
        """记录梦魇狼封锁行动。"""
        self._log_event(
            EventType.NIGHTMARE_BLOCKED,
            self.locale.get("nightmare_blocks", target=action.target.name),
            data={
                "player_id": action.actor.player_id,
                "target_id": action.target.player_id,
                **self._decision_data(action),
            },
        )

    def _log_guardian_wolf_action(self, action: GuardianWolfProtectAction) -> None:
        """记录守墓狼保护行动。"""
        self._log_event(
            EventType.GUARDIAN_WOLF_PROTECTED,
            self.locale.get("guardian_wolf_protected", target=action.target.name),
            data={
                "player_id": action.actor.player_id,
                "target_id": action.target.player_id,
                "visibility": "wolf_team",
                **self._decision_data(action),
            },
        )

    def _log_raven_action(self, action: RavenMarkAction) -> None:
        """记录乌鸦标记行动。"""
        self._log_event(
            EventType.RAVEN_MARKED,
            self.locale.get("raven_marks", target=action.target.name),
            data={
                "player_id": action.actor.player_id,
                "target_id": action.target.player_id,
                **self._decision_data(action),
            },
        )

    def _log_magician_swap_action(self, action: MagicianSwapAction) -> None:
        """记录魔术师换牌行动（仅魔术师可见）。"""
        self._log_event(
            EventType.MAGICIAN_SWAPPED,
            self.locale.get(
                "magician_swapped",
                target1=action.target1.name,
                target2=action.target2.name,
            ),
            data={
                "player_id": action.actor.player_id,
                "target1_id": action.target1.player_id,
                "target2_id": action.target2.player_id,
                **self._decision_data(action),
            },
        )

    def _log_graveyard_keeper_action(self, action: GraveyardKeeperCheckAction) -> None:
        """记录守墓人查验行动（仅守墓人可见，不泄露真实身份）。"""
        self._log_event(
            EventType.GRAVEYARD_KEEPER_CHECK,
            self.locale.get(
                "graveyard_keeper_checked",
                target=action.target.name,
                role=action.target.get_role_name(),
                camp=action.target.get_camp().value,
            ),
            data={
                "player_id": action.actor.player_id,
                "target_id": action.target.player_id,
                "role": action.target.get_role_name(),
                "camp": action.target.get_camp().value,
                **self._decision_data(action),
            },
        )

    def _log_action_event(self, action: Action) -> None:
        """为特定行动类型记录事件。

        Args:
            action: 待记录的行动。
        """
        for action_type, logger_name in self._ACTION_LOGGER_NAMES:
            if isinstance(action, action_type):
                getattr(self, logger_name)(action)
                return

    def process_actions(self, actions: list) -> list[str]:
        """处理行动列表。

        Args:
            actions: 待处理的 Action 对象列表。

        Returns:
            list[str]: 处理行动产生的消息。
        """
        messages = []

        # 按优先级排序：数值越大越先执行
        sorted_actions = sorted(actions, key=self._get_action_priority, reverse=True)

        for action in sorted_actions:
            # 检查行动执行者是否被梦魇狼封锁
            if self._is_actor_blocked(action):
                self._log_event(
                    EventType.MESSAGE,
                    self.locale.get(
                        "nightmare_blocked",
                        player=action.actor.name,
                        role=action.actor.get_role_name(),
                    ),
                    data={
                        "player_id": action.actor.player_id,
                        "role": action.actor.get_role_name(),
                    },
                )
                continue

            try:
                if action.validate():
                    result_messages = action.execute()
                    self._log_action_event(action)
                    if result_messages:
                        messages.extend(result_messages)
                else:
                    self._log_event(
                        EventType.ERROR,
                        self.locale.get(
                            "action_rejected",
                            role=action.actor.get_role_name(),
                            player=action.actor.name,
                            action=action.__class__.__name__,
                        ),
                        data={
                            "player_id": action.actor.player_id,
                            "role": action.actor.get_role_name(),
                            "action": action.__class__.__name__,
                        },
                    )
            except Exception as exc:
                self._log_event(
                    EventType.ERROR,
                    self.locale.get(
                        "action_failed",
                        role=action.actor.get_role_name(),
                        player=action.actor.name,
                        error=str(exc),
                    ),
                    data={
                        "player_id": action.actor.player_id,
                        "role": action.actor.get_role_name(),
                        "error": str(exc),
                        "error_type": type(exc).__name__,
                    },
                )

        return messages
