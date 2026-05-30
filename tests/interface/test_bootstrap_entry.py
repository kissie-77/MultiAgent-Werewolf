from llm_werewolf.interface.bootstrap import prepare_game_roster


def test_interface_bootstrap_exposes_roster_entrypoint() -> None:
    assert callable(prepare_game_roster)
    assert prepare_game_roster.__module__ == "llm_werewolf.interface.cli.runtime.bootstrap"
