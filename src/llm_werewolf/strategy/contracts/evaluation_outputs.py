"""评测层 LLM 结构化输出 Schema（PostGame / eval_agent）。"""

from __future__ import annotations

from pydantic import Field, BaseModel


class ReplayAnalysisDecision(BaseModel):
    """赛后复盘分析师单次输出。"""

    summary_zh: str = Field(..., description="300字内中文复盘摘要")
    prompt_suggestions: list[str] = Field(
        default_factory=list, description="2-3 条可写入角色 Prompt 的改进建议要点"
    )
    risks: list[str] = Field(default_factory=list, description="风险或待观察点")


class SkillCardFields(BaseModel):
    """Skill 卡片四段式正文（LLM 提取时用）。"""

    title_zh: str = ""
    when_to_use: str = ""
    public_behavior: str = ""
    avoid: str = ""


class SkillExtractionDecision(BaseModel):
    """按身份 Skill 提取输出。"""

    skill_id: str = ""
    rationale: str = ""
    skill_card: SkillCardFields = Field(default_factory=SkillCardFields)
    quality_passed: bool = False


class LlmPromptProposalItem(BaseModel):
    """LLM 资产提取：单条 Prompt 提案。"""

    prompt_role_key: str
    kind: str = "llm_coaching"
    suggested_patch_text_zh: str = ""
    rationale: str = ""
    confidence_score: float = 0.8
    evidence_round: int | None = None
    target_layer: str | None = None
    evidence_excerpt: str | None = None


class LlmSkillItem(BaseModel):
    """LLM 资产提取：单条 Skill 卡片。"""

    prompt_role_key: str
    title_zh: str = ""
    when_to_use: str = ""
    belief_trigger_zh: str = ""
    wolf_camp_trigger_zh: str = ""
    public_behavior: str = ""
    avoid: str = ""
    rationale: str = ""
    quality_passed: bool = False
    source_player_id: str | None = None
    evidence_round: int | None = None
    evidence_phase: str | None = None


class PostGameAssetExtractionDecision(BaseModel):
    """LLM 资产提取结构化输出。"""

    prompt_proposals: list[LlmPromptProposalItem] = Field(default_factory=list)
    skills: list[LlmSkillItem] = Field(default_factory=list)
    extraction_notes: str = ""
