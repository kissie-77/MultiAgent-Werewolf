from llm_werewolf.interface.cli.entry import _should_enable_sheriff


def test_explicit_config_does_not_enable_sheriff_by_default() -> None:
    assert not _should_enable_sheriff(
        config="configs/archive/human-6p-demo.yaml",
        rules=None,
        badge_flow=False,
    )


def test_explicit_badge_rule_enables_sheriff_even_with_config() -> None:
    assert _should_enable_sheriff(
        config="configs/custom.yaml",
        rules="badge_flow",
        badge_flow=False,
    )


def test_badge_flow_flag_enables_sheriff() -> None:
    assert _should_enable_sheriff(
        config="configs/custom.yaml",
        rules=None,
        badge_flow=True,
    )


def test_no_args_keeps_default_badge_flow_mode() -> None:
    assert _should_enable_sheriff(config=None, rules=None, badge_flow=False)
