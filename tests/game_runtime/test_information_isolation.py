"""信息隔离测试——验证跨角色无信息泄露。

测试目标：
- 预言家查验结果仅预言家可见，狼队/村民不可见
- 女巫救人/毒人仅女巫可见
- 狼队讨论仅狼队可见，村民/神职不可见
- 守卫保护仅守卫可见
- 白狼王击杀仅狼队可见
- 刀口结算对狼队+女巫可见，村民不可见
- 复盘类事件（投票意向快照、信念快照）对所有玩家不可见
"""

from __future__ import annotations

import pytest

from llm_werewolf.game_runtime.types import EventType
from llm_werewolf.game_runtime.events.event_visibility import resolve_visible_to


WOLF_IDS = ["wolf_1", "wolf_2"]
WITCH_IDS = ["witch_1"]
SEER_ID = "seer_1"
GUARD_ID = "guard_1"
VILLAGER_ID = "villager_1"


class TestSeerIsolation:
    """预言家查验结果不可泄露给任何其他角色。"""

    def test_seer_result_only_visible_to_seer(self) -> None:
        visible = resolve_visible_to(
            EventType.SEER_CHECKED,
            {"player_id": SEER_ID, "target_id": "wolf_1", "result": "werewolf"},
            wolf_player_ids=WOLF_IDS,
            witch_player_ids=WITCH_IDS,
        )
        assert visible == [SEER_ID]

    def test_seer_result_not_visible_to_wolves(self) -> None:
        visible = resolve_visible_to(
            EventType.SEER_CHECKED,
            {"player_id": SEER_ID, "target_id": "wolf_1", "result": "werewolf"},
            wolf_player_ids=WOLF_IDS,
        )
        assert WOLF_IDS[0] not in visible
        assert WOLF_IDS[1] not in visible

    def test_seer_result_not_visible_to_witch(self) -> None:
        visible = resolve_visible_to(
            EventType.SEER_CHECKED,
            {"player_id": SEER_ID},
            witch_player_ids=WITCH_IDS,
        )
        assert WITCH_IDS[0] not in visible


class TestWitchIsolation:
    """女巫操作仅女巫自己可见。"""

    def test_witch_save_only_visible_to_witch(self) -> None:
        visible = resolve_visible_to(
            EventType.WITCH_SAVED,
            {"player_id": "witch_1", "target_id": "villager_1"},
            wolf_player_ids=WOLF_IDS,
            witch_player_ids=WITCH_IDS,
        )
        assert visible == ["witch_1"]

    def test_witch_poison_only_visible_to_witch(self) -> None:
        visible = resolve_visible_to(
            EventType.WITCH_POISON_USED,
            {"player_id": "witch_1", "target_id": "wolf_1"},
            wolf_player_ids=WOLF_IDS,
            witch_player_ids=WITCH_IDS,
        )
        assert visible == ["witch_1"]

    def test_witch_save_not_visible_to_wolves(self) -> None:
        visible = resolve_visible_to(
            EventType.WITCH_SAVED,
            {"player_id": "witch_1", "target_id": "villager_1"},
            wolf_player_ids=WOLF_IDS,
        )
        for wid in WOLF_IDS:
            assert wid not in visible

    def test_witch_poison_not_visible_to_villager(self) -> None:
        visible = resolve_visible_to(
            EventType.WITCH_POISON_USED,
            {"player_id": "witch_1", "target_id": VILLAGER_ID},
            wolf_player_ids=WOLF_IDS,
        )
        assert VILLAGER_ID not in visible


class TestWolfTeamIsolation:
    """狼队内部通信和击杀决议不泄露给好人阵营。"""

    def test_wolf_discussion_only_visible_to_wolves(self) -> None:
        visible = resolve_visible_to(
            EventType.PLAYER_DISCUSSION,
            {"player_id": "wolf_1", "content": "今晚刀3号"},
            wolf_player_ids=WOLF_IDS,
            witch_player_ids=WITCH_IDS,
        )
        assert set(visible) == set(WOLF_IDS)

    def test_wolf_wake_message_not_visible_to_villagers(self) -> None:
        visible = resolve_visible_to(
            EventType.MESSAGE,
            {"action": "werewolves_wake"},
            wolf_player_ids=WOLF_IDS,
        )
        assert set(visible) == set(WOLF_IDS)

    def test_wolf_vote_message_not_visible_to_seer(self) -> None:
        visible = resolve_visible_to(
            EventType.MESSAGE,
            {"action": "werewolves_vote"},
            wolf_player_ids=WOLF_IDS,
        )
        assert SEER_ID not in visible

    def test_wolf_sleep_message_not_visible_to_guard(self) -> None:
        visible = resolve_visible_to(
            EventType.MESSAGE,
            {"action": "werewolves_sleep"},
            wolf_player_ids=WOLF_IDS,
        )
        assert GUARD_ID not in visible

    def test_white_wolf_kill_only_visible_to_wolf_team(self) -> None:
        visible = resolve_visible_to(
            EventType.WHITE_WOLF_KILLED,
            {"player_id": "wolf_1", "target_id": "wolf_2"},
            wolf_player_ids=WOLF_IDS,
            witch_player_ids=WITCH_IDS,
        )
        assert set(visible) == set(WOLF_IDS)
        assert WITCH_IDS[0] not in visible

    def test_guardian_wolf_protect_only_visible_to_wolf_team(self) -> None:
        visible = resolve_visible_to(
            EventType.GUARDIAN_WOLF_PROTECTED,
            {"player_id": "wolf_1", "target_id": "wolf_2"},
            wolf_player_ids=WOLF_IDS,
            witch_player_ids=WITCH_IDS,
        )
        assert set(visible) == set(WOLF_IDS)


class TestKillTargetVisibility:
    """刀口结算仅狼队和女巫可见——村民/守卫/预言家不可见。"""

    def test_werewolf_killed_visible_to_wolves_and_witch(self) -> None:
        visible = resolve_visible_to(
            EventType.WEREWOLF_KILLED,
            {"target_id": VILLAGER_ID},
            wolf_player_ids=WOLF_IDS,
            witch_player_ids=WITCH_IDS,
        )
        assert set(visible) == {"wolf_1", "wolf_2", "witch_1"}

    def test_werewolf_killed_not_visible_to_guard(self) -> None:
        visible = resolve_visible_to(
            EventType.WEREWOLF_KILLED,
            {"target_id": VILLAGER_ID},
            wolf_player_ids=WOLF_IDS,
            witch_player_ids=WITCH_IDS,
        )
        assert GUARD_ID not in visible

    def test_werewolf_killed_not_visible_to_seer(self) -> None:
        visible = resolve_visible_to(
            EventType.WEREWOLF_KILLED,
            {"target_id": VILLAGER_ID},
            wolf_player_ids=WOLF_IDS,
            witch_player_ids=WITCH_IDS,
        )
        assert SEER_ID not in visible

    def test_werewolf_killed_not_public(self) -> None:
        """刀口事件不是 None（公开），而是限定受众。"""
        visible = resolve_visible_to(
            EventType.WEREWOLF_KILLED,
            {"target_id": VILLAGER_ID},
            wolf_player_ids=WOLF_IDS,
            witch_player_ids=WITCH_IDS,
        )
        assert visible is not None


class TestGuardIsolation:
    """守卫保护仅守卫自己可见。"""

    def test_guard_protect_only_visible_to_guard(self) -> None:
        visible = resolve_visible_to(
            EventType.GUARD_PROTECTED,
            {"player_id": GUARD_ID, "target_id": VILLAGER_ID},
            wolf_player_ids=WOLF_IDS,
            witch_player_ids=WITCH_IDS,
        )
        assert visible == [GUARD_ID]

    def test_guard_protect_not_visible_to_wolves(self) -> None:
        visible = resolve_visible_to(
            EventType.GUARD_PROTECTED,
            {"player_id": GUARD_ID, "target_id": VILLAGER_ID},
            wolf_player_ids=WOLF_IDS,
        )
        for wid in WOLF_IDS:
            assert wid not in visible


class TestReplayOnlyIsolation:
    """复盘/评测专用事件对所有玩家不可见。"""

    def test_vote_intention_snapshot_hidden_from_all(self) -> None:
        visible = resolve_visible_to(
            EventType.VOTE_INTENTION_SNAPSHOT,
            {"round": 1, "intentions": {}},
            wolf_player_ids=WOLF_IDS,
            witch_player_ids=WITCH_IDS,
        )
        assert visible == []

    def test_belief_snapshot_hidden_from_all(self) -> None:
        visible = resolve_visible_to(
            EventType.BELIEF_SNAPSHOT,
            {"round": 1, "beliefs": {}},
            wolf_player_ids=WOLF_IDS,
            witch_player_ids=WITCH_IDS,
        )
        assert visible == []


class TestPrivateActorEvents:
    """各角色私有事件只对行动者本人可见。"""

    @pytest.mark.parametrize(
        "event_type,actor_id",
        [
            (EventType.WOLF_BEAUTY_CHARMED, "wolf_beauty_1"),
            (EventType.NIGHTMARE_BLOCKED, "nightmare_1"),
            (EventType.MAGICIAN_SWAPPED, "magician_1"),
            (EventType.RAVEN_MARKED, "raven_1"),
            (EventType.GRAVEYARD_KEEPER_CHECK, "keeper_1"),
        ],
    )
    def test_private_skill_events_only_actor_visible(
        self, event_type: EventType, actor_id: str
    ) -> None:
        visible = resolve_visible_to(
            event_type,
            {"player_id": actor_id, "target_id": "some_target"},
            wolf_player_ids=WOLF_IDS,
            witch_player_ids=WITCH_IDS,
        )
        assert visible == [actor_id]
        for other in [*WOLF_IDS, *WITCH_IDS, SEER_ID, GUARD_ID, VILLAGER_ID]:
            if other != actor_id:
                assert other not in visible


class TestCupidIsolation:
    """丘比特连线仅丘比特可见。"""

    def test_lovers_linked_only_visible_to_cupid(self) -> None:
        visible = resolve_visible_to(
            EventType.LOVERS_LINKED,
            {"player_id": "cupid_1", "player1_id": "p1", "player2_id": "p2"},
            wolf_player_ids=WOLF_IDS,
            witch_player_ids=WITCH_IDS,
        )
        assert visible == ["cupid_1"]

    def test_lovers_linked_not_visible_to_wolves(self) -> None:
        visible = resolve_visible_to(
            EventType.LOVERS_LINKED,
            {"player_id": "cupid_1", "player1_id": "p1", "player2_id": "p2"},
            wolf_player_ids=WOLF_IDS,
        )
        for wid in WOLF_IDS:
            assert wid not in visible
