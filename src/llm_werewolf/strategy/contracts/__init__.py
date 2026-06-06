"""结构化决策与阶段输出契约。"""

from llm_werewolf.strategy.contracts.decisions import (
    BeliefEntry,
    GodRoleDelta,
    WolfCampDelta,
    SpeechDecision,
    SecondOrderEntry,
    SeatChoiceDecision,
    WitchNightDecision,
    VoteIntentionDecision,
    normalize_speech_decision,
    speech_schema_instruction,
)
from llm_werewolf.strategy.contracts.phase_outputs import (
    ROUNDTABLE_SPEECH_ONLY_MARKER,
    ActionPhase,
    action_phase_instruction,
    resolve_roundtable_phase,
)
from llm_werewolf.strategy.contracts.evaluation_outputs import ReplayAnalysisDecision

__all__ = [
    "ROUNDTABLE_SPEECH_ONLY_MARKER",
    "ActionPhase",
    "BeliefEntry",
    "GodRoleDelta",
    "ReplayAnalysisDecision",
    "SeatChoiceDecision",
    "SecondOrderEntry",
    "SpeechDecision",
    "VoteIntentionDecision",
    "WitchNightDecision",
    "WolfCampDelta",
    "action_phase_instruction",
    "normalize_speech_decision",
    "resolve_roundtable_phase",
    "speech_schema_instruction",
]
