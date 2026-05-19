from llm_werewolf.core.types import Event, EventType
from llm_werewolf.evaluation.models import CheckResult, CheckSeverity


class InformationIsolationChecker:
    """Detects private event messages in unauthorized observations."""

    def check(
        self,
        events: list[Event],
        observations_by_player: dict[str, str] | None = None,
    ) -> list[CheckResult]:
        observations_by_player = observations_by_player or {}
        results: list[CheckResult] = []

        for event in events:
            if not event.visible_to or not event.message:
                continue

            allowed = set(event.visible_to)
            for player_id, observation in observations_by_player.items():
                if player_id in allowed:
                    continue
                if event.message in observation:
                    results.append(
                        CheckResult(
                            checker=self.__class__.__name__,
                            passed=False,
                            message="Private event appeared in unauthorized observation",
                            severity=CheckSeverity.CRITICAL,
                            data={
                                "player_id": player_id,
                                "event_type": event.event_type.value,
                                "round_number": event.round_number,
                                "phase": event.phase,
                            },
                        )
                    )

        return results


class AsyncFlowChecker:
    """Checks phase transition consistency."""

    _allowed_transitions = {
        "setup": {"night", "ended"},
        "night": {"sheriff_election", "day_discussion", "ended"},
        "sheriff_election": {"day_discussion", "ended"},
        "day_discussion": {"day_voting", "ended"},
        "day_voting": {"night", "ended"},
        "ended": set(),
    }

    def check(self, events: list[Event]) -> list[CheckResult]:
        phase_events = [event for event in events if event.event_type == EventType.PHASE_CHANGED]
        results: list[CheckResult] = []

        for previous, current in zip(phase_events, phase_events[1:], strict=False):
            allowed = self._allowed_transitions.get(previous.phase, set())
            if current.phase not in allowed:
                results.append(
                    CheckResult(
                        checker=self.__class__.__name__,
                        passed=False,
                        message="Illegal phase transition",
                        data={
                            "from_phase": previous.phase,
                            "to_phase": current.phase,
                            "from_round": previous.round_number,
                            "to_round": current.round_number,
                        },
                    )
                )

        return results


class VictoryCheckerEvaluator:
    """Checks final winner consistency between engine state and events."""

    def check(self, events: list[Event], final_winner: str | None = None) -> list[CheckResult]:
        if final_winner is None:
            return []

        game_end_events = [event for event in events if event.event_type == EventType.GAME_ENDED]
        if not game_end_events:
            return []

        last_end_event = game_end_events[-1]
        event_winner = last_end_event.data.get("winner_camp")
        if event_winner != final_winner:
            return [
                CheckResult(
                    checker=self.__class__.__name__,
                    passed=False,
                    message="GAME_ENDED winner does not match final game state winner",
                    severity=CheckSeverity.CRITICAL,
                    data={"event_winner": event_winner, "final_winner": final_winner},
                )
            ]

        return []


class RoleSkillChecker:
    """Checks whether role action events contain enough structured data."""

    _required_fields = {
        EventType.WEREWOLF_KILLED: {"target_id"},
        EventType.WITCH_SAVED: {"target_id"},
        EventType.WITCH_POISONED: {"target_id"},
        EventType.SEER_CHECKED: {"target_id", "result"},
        EventType.GUARD_PROTECTED: {"target_id"},
        EventType.HUNTER_REVENGE: {"shooter_id", "target_id", "role"},
        EventType.VOTE_CAST: {"voter_id", "target_id"},
    }

    def check(self, events: list[Event]) -> list[CheckResult]:
        results: list[CheckResult] = []

        for event in events:
            required = self._required_fields.get(event.event_type)
            if not required:
                continue

            missing = sorted(field for field in required if field not in event.data)
            if missing:
                results.append(
                    CheckResult(
                        checker=self.__class__.__name__,
                        passed=False,
                        message="Structured action event is missing required fields",
                        severity=CheckSeverity.WARNING,
                        data={
                            "event_type": event.event_type.value,
                            "phase": event.phase,
                            "round_number": event.round_number,
                            "missing_fields": missing,
                        },
                    )
                )

        return results
