from llm_werewolf.interface.api.routes.actions import _redact_roster_for_seat

ROSTER = [
    {"seat": 1, "name": "P1", "role": "Witch", "camp": "villager", "is_alive": True},
    {"seat": 2, "name": "P2", "role": "Werewolf", "camp": "werewolf", "is_alive": True},
    {"seat": 3, "name": "P3", "role": "Seer", "camp": "villager", "is_alive": False},
    {"seat": 4, "name": "P4", "role": "Alpha Wolf", "camp": "werewolf", "is_alive": True},
]


def test_villager_human_sees_only_own_role():
    out = _redact_roster_for_seat(ROSTER, seat=1)
    by_seat = {r["seat"]: r for r in out}
    # always-public fields kept for everyone
    assert by_seat[2]["name"] == "P2" and by_seat[2]["is_alive"] is True
    assert by_seat[3]["is_alive"] is False
    # only own role/camp revealed
    assert by_seat[1]["role"] == "Witch" and by_seat[1]["camp"] == "villager"
    assert by_seat[2]["role"] is None and by_seat[2]["camp"] is None
    assert by_seat[3]["role"] is None and by_seat[4]["role"] is None


def test_wolf_human_sees_all_wolf_teammates():
    out = _redact_roster_for_seat(ROSTER, seat=2)  # P2 is a Werewolf
    by_seat = {r["seat"]: r for r in out}
    assert by_seat[2]["role"] == "Werewolf"      # self
    assert by_seat[4]["role"] == "Alpha Wolf"    # fellow wolf revealed
    assert by_seat[1]["role"] is None            # villager hidden
    assert by_seat[3]["role"] is None            # villager hidden


def test_empty_or_missing_roster_is_empty_list():
    assert _redact_roster_for_seat(None, seat=1) == []
    assert _redact_roster_for_seat([], seat=1) == []
