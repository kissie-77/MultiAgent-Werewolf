"""打分包。"""

from llm_werewolf.evaluation.scoring.benefit import write_benefit_scores
from llm_werewolf.evaluation.scoring.intention import write_intention_scores

__all__ = ["write_benefit_scores", "write_intention_scores"]
