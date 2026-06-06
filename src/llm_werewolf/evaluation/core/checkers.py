import re
import itertools

from llm_werewolf.game_runtime.types import Camp, Event, EventType
from llm_werewolf.strategy.contracts.decisions import SPEECH_PUBLIC_MIN_CHARS, looks_like_seat_only

_EMPTY_SPEECH_MARKERS = ("（无公开发言）", "无公开发言")

from llm_werewolf.evaluation.core.models import CheckResult, CheckSeverity


class PromptBadCaseChecker:
    """自动发现 Prompt 调优用的候选 bad case。

    这一版只做可复现的规则检查，不声称判断“最优博弈”。它的目标是把
    明显可定位的问题先从对局日志里捞出来，供 prompt_tuning 复盘使用。
    """

    _generic_speech_markers = {
        "i agree",
        "i am not sure",
        "let me think",
        "that's interesting",
        "我同意",
        "不确定",
        "大家谨慎",
        "好好分析",
    }
    _public_speech_events = {EventType.PLAYER_SPEECH, EventType.SHERIFF_CANDIDATE_SPEECH}
    _unsupported_claim_patterns = (
        re.compile(r"(?:玩家)?\d+号?.{0,6}(?:跳|自称|认|报).{0,4}(?:女巫|预言家|猎人|守卫)"),
        re.compile(r"(?:玩家)?\d+号?.{0,6}(?:救了|救过|银水|查验|验了|金水|查杀)"),
    )
    _claim_support_markers = (
        "跳",
        "自称",
        "女巫",
        "预言家",
        "猎人",
        "守卫",
        "救",
        "银水",
        "查验",
        "验了",
        "金水",
        "查杀",
    )
    _prior_public_info_patterns = (
        re.compile(r"(?:白天|今天|刚才|上一轮|上轮).{0,12}发言"),
        re.compile(r"发言.{0,12}(?:活跃|带队|站边|划水|可疑|做好|做坏|狼面|好人面)"),
        re.compile(r"(?:票型|归票|冲票|分票|投票记录|警上|警下)"),
    )

    def check(
        self,
        events: list[Event],
        player_roles: dict[str, str] | None = None,
        player_camps: dict[str, Camp] | None = None,
    ) -> list[CheckResult]:
        player_roles = player_roles or {}
        player_camps = player_camps or {}
        results: list[CheckResult] = []
        results.extend(self._check_response_format(events))
        results.extend(self._check_low_information_speech(events))
        results.extend(self._check_repeated_seer_checks(events))
        results.extend(self._check_harmful_power_targets(events, player_roles, player_camps))
        results.extend(self._check_unsupported_public_fact_claims(events))
        results.extend(self._check_night_claims_before_public_context(events))
        return results

    def _bad_case(
        self,
        message: str,
        event: Event,
        data: dict | None = None,
        severity: CheckSeverity = CheckSeverity.WARNING,
        bad_case_kind: str = "strategy_mistake",
        confidence: str = "medium",
        confidence_score: float = 0.7,
    ) -> CheckResult:
        payload = {
            "round_number": event.round_number,
            "phase": event.phase.value if hasattr(event.phase, "value") else str(event.phase),
            "event_type": event.event_type.value,
            "bad_case_kind": bad_case_kind,
            "confidence": confidence,
            "confidence_score": round(max(0.0, min(1.0, confidence_score)), 3),
        }
        payload.update(data or {})
        return CheckResult(
            checker=self.__class__.__name__,
            passed=False,
            message=f"Potential prompt bad case: {message}",
            severity=severity,
            data=payload,
        )

    @staticmethod
    def _has_bracket_answer(text: str) -> bool:
        return "[[" in text and "]]" in text

    @staticmethod
    def _extract_speech_text(text: str) -> str:
        if "[[" not in text or "]]" not in text:
            return text.strip()
        start = text.find("[[") + 2
        end = text.rfind("]]")
        return text[start:end].strip()

    def _check_response_format(self, events: list[Event]) -> list[CheckResult]:
        """运行时发言使用 SpeechDecision JSON；日志存 public_speech 文本。"""
        results: list[CheckResult] = []
        for event in events:
            if event.event_type != EventType.PLAYER_SPEECH:
                continue
            speech = self._extract_speech_text(str(event.data.get("speech", "")))
            if not speech or any(m in speech for m in _EMPTY_SPEECH_MARKERS):
                results.append(
                    self._bad_case(
                        "day speech was empty or a placeholder",
                        event,
                        data={"player_id": event.data.get("player_id")},
                        severity=CheckSeverity.INFO,
                        bad_case_kind="format_error",
                        confidence="high",
                        confidence_score=0.95,
                    )
                )
                continue
            if looks_like_seat_only(speech) or len(speech) < SPEECH_PUBLIC_MIN_CHARS:
                results.append(
                    self._bad_case(
                        "day speech was too short or looked like a seat token, not SpeechDecision public_speech",
                        event,
                        data={"player_id": event.data.get("player_id"), "speech": speech[:120]},
                        severity=CheckSeverity.INFO,
                        bad_case_kind="format_error",
                        confidence="high",
                        confidence_score=0.9,
                    )
                )
        return results

    def _check_low_information_speech(self, events: list[Event]) -> list[CheckResult]:
        results: list[CheckResult] = []
        for event in events:
            if event.event_type != EventType.PLAYER_SPEECH:
                continue
            raw_speech = str(event.data.get("speech", ""))
            speech = self._extract_speech_text(raw_speech).lower()
            if not speech:
                continue
            has_player_reference = any(char.isdigit() for char in speech)
            is_too_short = len(speech) < SPEECH_PUBLIC_MIN_CHARS
            is_generic = any(marker in speech for marker in self._generic_speech_markers)
            if is_too_short or (is_generic and not has_player_reference):
                kind = "format_error" if is_too_short else "low_information"
                results.append(
                    self._bad_case(
                        "speech was too generic to support role-specific reasoning",
                        event,
                        data={
                            "player_id": event.data.get("player_id"),
                            "speech": raw_speech[:120],
                        },
                        severity=CheckSeverity.INFO,
                        bad_case_kind=kind,
                        confidence="high" if is_too_short else "medium",
                        confidence_score=0.85 if is_too_short else 0.68,
                    )
                )
        return results

    def _check_repeated_seer_checks(self, events: list[Event]) -> list[CheckResult]:
        results: list[CheckResult] = []
        checked_targets: set[str] = set()
        for event in events:
            if event.event_type != EventType.SEER_CHECKED:
                continue
            target_id = event.data.get("target_id")
            if not target_id:
                continue
            if target_id in checked_targets:
                results.append(
                    self._bad_case(
                        "seer checked the same target more than once",
                        event,
                        data={"target_id": target_id},
                        bad_case_kind="strategy_mistake",
                        confidence="high",
                        confidence_score=0.9,
                    )
                )
            checked_targets.add(target_id)
        return results

    def _check_harmful_power_targets(
        self, events: list[Event], player_roles: dict[str, str], player_camps: dict[str, Camp]
    ) -> list[CheckResult]:
        results: list[CheckResult] = []
        for event in events:
            if event.event_type == EventType.HUNTER_REVENGE:
                target_id = event.data.get("target_id")
                if target_id and player_camps.get(target_id) == Camp.VILLAGER:
                    results.append(
                        self._bad_case(
                            "death-shot ability targeted a villager-camp player",
                            event,
                            data={
                                "shooter_id": event.data.get("shooter_id"),
                                "target_id": target_id,
                                "target_role": player_roles.get(target_id),
                            },
                            bad_case_kind="strategy_mistake",
                            confidence="medium",
                            confidence_score=0.72,
                        )
                    )
            elif event.event_type in {EventType.WITCH_POISON_USED, EventType.WITCH_POISONED}:
                target_id = event.data.get("target_id")
                if target_id and player_camps.get(target_id) == Camp.VILLAGER:
                    results.append(
                        self._bad_case(
                            "witch poison targeted a villager-camp player",
                            event,
                            data={
                                "target_id": target_id,
                                "target_role": player_roles.get(target_id),
                            },
                            bad_case_kind="strategy_mistake",
                            confidence="medium",
                            confidence_score=0.72,
                        )
                    )
        return results

    def _check_unsupported_public_fact_claims(self, events: list[Event]) -> list[CheckResult]:
        """标记“别人已跳身份/报技能结果”这类没有公开前文支撑的发言。"""
        results: list[CheckResult] = []
        previous_public_speech = ""

        for event in events:
            if event.event_type not in self._public_speech_events:
                continue

            raw_speech = str(event.data.get("speech", event.message))
            speech = self._extract_speech_text(raw_speech)
            if not speech:
                continue

            unsupported = any(pattern.search(speech) for pattern in self._unsupported_claim_patterns)
            has_public_support = any(
                marker in previous_public_speech for marker in self._claim_support_markers
            )
            if unsupported and not has_public_support:
                results.append(
                    self._bad_case(
                        "public speech asserted another player's role/action claim without prior public support",
                        event,
                        data={
                            "player_id": event.data.get("player_id"),
                            "speech": speech[:120],
                        },
                        severity=CheckSeverity.WARNING,
                        bad_case_kind="hallucination",
                        confidence="high",
                        confidence_score=0.86,
                    )
                )

            previous_public_speech += "\n" + speech

        return results

    def _check_night_claims_before_public_context(
        self, events: list[Event]
    ) -> list[CheckResult]:
        """标记首个公开阶段前，夜聊凭空引用白天发言/票型等事实。"""
        results: list[CheckResult] = []
        has_prior_public_context = False

        for event in events:
            if event.event_type in self._public_speech_events or event.event_type in {
                EventType.VOTE_CAST,
                EventType.VOTE_RESULT,
                EventType.PLAYER_ELIMINATED,
            }:
                has_prior_public_context = True

            if event.event_type != EventType.PLAYER_DISCUSSION:
                continue

            phase = event.phase.value if hasattr(event.phase, "value") else str(event.phase)
            if phase != "night" or has_prior_public_context:
                continue

            raw_speech = str(event.data.get("speech", event.message))
            speech = self._extract_speech_text(raw_speech)
            if not speech:
                continue

            if any(pattern.search(speech) for pattern in self._prior_public_info_patterns):
                results.append(
                    self._bad_case(
                        "night speech referenced public-day evidence before any public context existed",
                        event,
                        data={
                            "player_id": event.data.get("player_id"),
                            "speech": speech[:120],
                        },
                        severity=CheckSeverity.WARNING,
                        bad_case_kind="hallucination",
                        confidence="high",
                        confidence_score=0.88,
                    )
                )

        return results


class InformationIsolationChecker:
    """检查私有事件是否泄露到无权限玩家视角。

    检测 message 全文与 data 内敏感字段（如验人 result、狼票明细）是否出现在他人 observation。
    """

    _SENSITIVE_DATA_KEYS = frozenset({"result", "werewolf_votes", "private_thought", "decision"})
    _MIN_FRAGMENT_LEN = 12

    def check(
        self, events: list[Event], observations_by_player: dict[str, str] | None = None
    ) -> list[CheckResult]:
        observations_by_player = observations_by_player or {}
        results: list[CheckResult] = []

        for event in events:
            if not event.visible_to:
                continue

            allowed = set(event.visible_to)
            sensitive_fragments = self._collect_sensitive_fragments(event)

            for player_id, observation in observations_by_player.items():
                if player_id in allowed:
                    continue
                for fragment in sensitive_fragments:
                    if self._fragment_leaked(fragment, observation):
                        results.append(
                            CheckResult(
                                checker=self.__class__.__name__,
                                passed=False,
                                message="Private event content appeared in unauthorized observation",
                                severity=CheckSeverity.CRITICAL,
                                data={
                                    "player_id": player_id,
                                    "event_type": event.event_type.value,
                                    "round_number": event.round_number,
                                    "phase": event.phase.value
                                    if hasattr(event.phase, "value")
                                    else str(event.phase),
                                    "leaked_fragment": fragment[:80],
                                },
                            )
                        )
                        break

        return results

    def _fragment_leaked(self, fragment: str, observation: str) -> bool:
        text = fragment.strip()
        if len(text) < self._MIN_FRAGMENT_LEN:
            return False
        return text in observation

    def _collect_sensitive_fragments(self, event: Event) -> list[str]:
        fragments: list[str] = []
        if event.message and event.message.strip():
            fragments.append(event.message.strip())
        data = event.data or {}
        for key in self._SENSITIVE_DATA_KEYS:
            value = data.get(key)
            if value is None:
                continue
            if isinstance(value, str):
                fragments.append(value.strip())
            elif isinstance(value, list):
                for item in value:
                    if isinstance(item, dict):
                        for part in item.values():
                            if isinstance(part, str) and part.strip():
                                fragments.append(part.strip())
        return [frag for frag in fragments if len(frag) >= self._MIN_FRAGMENT_LEN]


class AsyncFlowChecker:
    """检查游戏阶段流转是否符合引擎允许顺序。

    这个 checker 只看 `PHASE_CHANGED` 事件，不直接读取 GameState。
    这样可以对历史事件流做离线复盘，也能发现“事件记录和状态推进不一致”的问题。
    """

    # 允许的有向状态转移。ended 是终态，之后不应该再有新阶段。
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

        # 逐对比较相邻阶段事件；只要出现不在白名单里的跳转就记录违规。
        for previous, current in itertools.pairwise(phase_events):
            prev_phase = (
                previous.phase.value if hasattr(previous.phase, "value") else str(previous.phase)
            )
            curr_phase = (
                current.phase.value if hasattr(current.phase, "value") else str(current.phase)
            )
            allowed = self._allowed_transitions.get(prev_phase, set())
            if curr_phase not in allowed:
                results.append(
                    CheckResult(
                        checker=self.__class__.__name__,
                        passed=False,
                        message="Illegal phase transition",
                        data={
                            "from_phase": prev_phase,
                            "to_phase": curr_phase,
                            "from_round": previous.round_number,
                            "to_round": current.round_number,
                        },
                    )
                )

        return results


class VictoryCheckerEvaluator:
    """检查胜负事件与最终状态是否一致。

    `GameEngine.check_victory()` 会写入 `game_state.winner`，同时记录 GAME_ENDED。
    如果两者不一致，后续报告和复盘会互相矛盾，所以这里单独检测。
    """

    def check(self, events: list[Event], final_winner: str | None = None) -> list[CheckResult]:
        # 游戏未结束或没有 winner 时，不做胜负一致性判断。
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
    """检查角色动作事件是否具备最小结构化字段。

    第一版还不尝试完整验证每个角色技能语义，而是先保证事件能被机器读懂。
    例如女巫救人事件至少要有 `target_id`，预言家查验至少要有 `target_id/result`。
    这些字段是后续做更细角色规则检查和 Web 复盘的基础。
    """

    # 不同事件需要的最小字段集合。字段缺失时，报告会提示 missing_structured_event。
    _required_fields = {
        EventType.WEREWOLF_KILLED: {"target_id"},
        EventType.WITCH_SAVED: {"target_id"},
        EventType.WITCH_POISON_USED: {"target_id"},
        EventType.WITCH_POISONED: {"target_id"},
        EventType.SEER_CHECKED: {"target_id", "result"},
        EventType.GUARD_PROTECTED: {"target_id"},
        EventType.WHITE_WOLF_KILLED: {"actor_id", "target_id"},
        EventType.WOLF_BEAUTY_CHARMED: {"actor_id", "target_id"},
        EventType.NIGHTMARE_BLOCKED: {"actor_id", "target_id"},
        EventType.GUARDIAN_WOLF_PROTECTED: {"actor_id", "target_id"},
        EventType.RAVEN_MARKED: {"actor_id", "target_id"},
        EventType.HUNTER_REVENGE: {"shooter_id", "target_id", "role"},
        EventType.VOTE_CAST: {"voter_id", "target_id"},
    }

    def check(self, events: list[Event]) -> list[CheckResult]:
        results: list[CheckResult] = []

        for event in events:
            required = self._required_fields.get(event.event_type)
            if not required:
                continue

            # 只检查字段是否存在，不在这里判断目标是否合法；非法动作后续由专门 checker 负责。
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
                            "phase": event.phase.value
                            if hasattr(event.phase, "value")
                            else str(event.phase),
                            "round_number": event.round_number,
                            "missing_fields": missing,
                        },
                    )
                )

        return results


class DecisionConsistencyChecker:
    """检查解析后的决策与最终行动目标一致。"""

    _target_events = {
        EventType.GUARD_PROTECTED,
        EventType.WITCH_SAVED,
        EventType.WITCH_POISON_USED,
        EventType.WITCH_POISONED,
        EventType.SEER_CHECKED,
        EventType.WHITE_WOLF_KILLED,
        EventType.WOLF_BEAUTY_CHARMED,
        EventType.NIGHTMARE_BLOCKED,
        EventType.GUARDIAN_WOLF_PROTECTED,
        EventType.RAVEN_MARKED,
        EventType.VOTE_CAST,
    }

    _public_speech_events = {EventType.PLAYER_SPEECH, EventType.PLAYER_DISCUSSION}

    def check(self, events: list[Event]) -> list[CheckResult]:
        results: list[CheckResult] = []

        for event in events:
            if event.event_type in self._target_events:
                decision = event.data.get("decision") or {}
                resolved_target_id = decision.get("resolved_target_id")
                if resolved_target_id and resolved_target_id != event.data.get("target_id"):
                    results.append(
                        CheckResult(
                            checker=self.__class__.__name__,
                            passed=False,
                            message="Parsed decision target does not match resolved event target",
                            severity=CheckSeverity.CRITICAL,
                            data={
                                "event_type": event.event_type.value,
                                "round_number": event.round_number,
                                "decision_target_id": resolved_target_id,
                                "event_target_id": event.data.get("target_id"),
                            },
                        )
                    )

            if event.event_type in self._public_speech_events:
                speech = event.data.get("speech", event.message)
                if "{" in speech or "}" in speech:
                    results.append(
                        CheckResult(
                            checker=self.__class__.__name__,
                            passed=False,
                            message="Public speech contains private-thought markers",
                            severity=CheckSeverity.WARNING,
                            data={
                                "event_type": event.event_type.value,
                                "round_number": event.round_number,
                                "player_id": event.data.get("player_id"),
                            },
                        )
                    )

        return results
