"""Registry of offline evaluation checkers — extend without editing runner."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any
from dataclasses import dataclass
from collections.abc import Callable

from llm_werewolf.evaluation.core.models import CheckResult
from llm_werewolf.evaluation.core.checkers import (
    AsyncFlowChecker,
    RoleSkillChecker,
    PromptBadCaseChecker,
    VictoryCheckerEvaluator,
    DecisionConsistencyChecker,
    InformationIsolationChecker,
)

if TYPE_CHECKING:
    from llm_werewolf.game_runtime.types import Event


@dataclass(frozen=True)
class CheckerRunContext:
    events: list[Event]
    observations_by_player: dict[str, str]
    final_winner: str | None
    player_roles: dict[str, str]
    player_camps: dict[str, str]


CheckerSpec = tuple[type[Any], Callable[[CheckerRunContext], dict[str, Any]]]


def default_checker_specs() -> list[CheckerSpec]:
    """Built-in checker list; append via ``register_checker`` for plugins."""
    return list(_CHECKER_SPECS)


def register_checker(spec: CheckerSpec) -> CheckerSpec:
    _CHECKER_SPECS.append(spec)
    return spec


def run_registered_checkers(context: CheckerRunContext) -> list[CheckResult]:
    checks: list[CheckResult] = []
    for checker_cls, kwargs_builder in default_checker_specs():
        checker = checker_cls()
        try:
            checks.extend(checker.check(**kwargs_builder(context)))
        except Exception as exc:
            checks.append(
                CheckResult(
                    checker=checker_cls.__name__,
                    passed=False,
                    message=f"Checker raised {type(exc).__name__}: {exc}",
                )
            )
    return checks


_CHECKER_SPECS: list[CheckerSpec] = [
    (RoleSkillChecker, lambda ctx: {"events": ctx.events}),
    (
        InformationIsolationChecker,
        lambda ctx: {
            "events": ctx.events,
            "observations_by_player": ctx.observations_by_player,
        },
    ),
    (
        VictoryCheckerEvaluator,
        lambda ctx: {"events": ctx.events, "final_winner": ctx.final_winner},
    ),
    (AsyncFlowChecker, lambda ctx: {"events": ctx.events}),
    (DecisionConsistencyChecker, lambda ctx: {"events": ctx.events}),
    (
        PromptBadCaseChecker,
        lambda ctx: {
            "events": ctx.events,
            "player_roles": ctx.player_roles,
            "player_camps": ctx.player_camps,
        },
    ),
]
