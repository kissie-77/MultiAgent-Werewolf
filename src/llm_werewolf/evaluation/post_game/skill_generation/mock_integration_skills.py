"""兼容入口：请使用 reference_skills.sync_agent_skill_library。"""

from llm_werewolf.evaluation.post_game.skill_generation.reference_skills import (
    find_best_source_run,
    build_reference_skills,
    sync_agent_skill_library,
    build_mock_integration_skills,
    write_mock_integration_skills,
)

__all__ = [
    "build_mock_integration_skills",
    "build_reference_skills",
    "find_best_source_run",
    "sync_agent_skill_library",
    "write_mock_integration_skills",
]
