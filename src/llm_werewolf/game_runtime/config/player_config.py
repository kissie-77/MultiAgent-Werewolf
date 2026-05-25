from typing import Literal

from pydantic import Field, BaseModel, computed_field, field_validator, model_validator
from openai.types.shared import ReasoningEffort
from pydantic_core.core_schema import ValidationInfo


class PlayerConfig(BaseModel):
    """单个玩家的游戏配置。

    智能体类型由 model 字段决定：
    - model="human"：通过控制台输入的人类玩家
    - model="demo"：用于测试的随机响应机器人
    - model=<model_name> + base_url：使用 ChatCompletion API 的 LLM 智能体
    """

    name: str = Field(..., description="Display name for the player")
    model: str = Field(
        ...,
        title="Model Name",
        description="The model name of your player",
        examples=["gpt-5", "human", "demo"],
    )
    base_url: str | None = Field(
        default=None,
        title="API Base URL",
        description="API base URL (required for LLM models).",
        examples=["https://api.openai.com/v1", "https://api.anthropic.com/v1"],
    )
    api_key_env: str | None = Field(
        default=None,
        title="API Key Environment Variable",
        description="Environment variable name containing the API key (e.g., OPENAI_API_KEY)",
        examples=["OPENAI_API_KEY", "ANTHROPIC_API_KEY"],
    )
    reasoning_effort: ReasoningEffort | None = Field(
        default=None, title="Reasoning Effort", description="Reasoning effort level for LLM"
    )
    plan: str | None = Field(
        default=None,
        description="Plan strategy name (default, complicated, bold, ...) for AgentScope prompts",
    )

    @field_validator("base_url")
    @classmethod
    def validate_base_url(cls, v: str | None, info: ValidationInfo) -> str | None:
        """校验 LLM 模型是否提供了 base_url。"""
        model = info.data.get("model", "")
        if model not in {"human", "demo"} and not v:
            msg = f"base_url is required for LLM model '{model}'"
            raise ValueError(msg)
        return v


class PlayerTemplateConfig(BaseModel):
    """Reusable player settings for generated rosters."""

    name_prefix: str = Field(
        default="Player",
        description="Prefix used when generating player display names.",
    )
    model: str = Field(
        ...,
        title="Model Name",
        description="The model name used by generated LLM players.",
        examples=["gpt-5", "deepseek-v4-flash", "demo"],
    )
    base_url: str | None = Field(
        default=None,
        title="API Base URL",
        description="API base URL (required for LLM models).",
        examples=["https://api.openai.com/v1", "https://api.deepseek.com/v1"],
    )
    api_key_env: str | None = Field(
        default=None,
        title="API Key Environment Variable",
        description="Environment variable name containing the API key.",
        examples=["OPENAI_API_KEY", "DEEPSEEK_API_KEY"],
    )
    reasoning_effort: ReasoningEffort | None = Field(
        default=None, title="Reasoning Effort", description="Reasoning effort level for LLM"
    )
    plan: str | None = Field(
        default=None,
        description="Plan strategy name (default, complicated, bold, ...) for AgentScope prompts",
    )

    @field_validator("base_url")
    @classmethod
    def validate_base_url(cls, v: str | None, info: ValidationInfo) -> str | None:
        model = info.data.get("model", "")
        if model not in {"human", "demo"} and not v:
            msg = f"base_url is required for LLM model '{model}'"
            raise ValueError(msg)
        return v


class PlayerRosterConfig(BaseModel):
    """Generated roster settings for variable-size games."""

    count: int = Field(
        default=12,
        ge=6,
        le=20,
        description="Number of seats to generate for the game.",
    )
    mode: Literal["all_agent", "human_mixed"] = Field(
        default="all_agent",
        description="Roster participation mode.",
    )
    human: PlayerConfig | None = Field(
        default=None,
        description="Optional human player config for human_mixed mode.",
    )
    llm_template: PlayerTemplateConfig = Field(
        ...,
        description="Template used to generate LLM player configs.",
    )

    @model_validator(mode="after")
    def validate_human_config(self) -> "PlayerRosterConfig":
        if self.mode == "all_agent" and self.human is not None:
            msg = "human is only valid when player_roster.mode is 'human_mixed'"
            raise ValueError(msg)
        if self.human is not None and self.human.model != "human":
            msg = "player_roster.human must use model 'human'"
            raise ValueError(msg)
        return self


class PlayersConfig(BaseModel):
    """包含所有玩家及可选游戏设置的根配置。"""

    language: str = Field(
        default="en-US",
        title="Language",
        description="Language code for the game.",
        examples=["en-US", "zh-TW"],
    )
    agent_backend: str = Field(
        default="agentscope",
        description="Agent backend: 'agentscope'.",
    )
    default_plan: str = Field(
        default="default",
        description="Default plan strategy for AgentScope RolePrompts / PlanStrategies",
    )
    players: list[PlayerConfig] | None = Field(
        default=None,
        title="Player List",
        description="List of player configs, you should define it under ./configs/<name>.yaml",
        min_length=6,
        max_length=20,
    )
    player_roster: PlayerRosterConfig | None = Field(
        default=None,
        description="Template-based roster config for variable-size games.",
    )

    @computed_field  # type: ignore[prop-decorator]
    @property
    def use_agentscope_backend(self) -> bool:
        """YAML ``agent_backend`` 当前统一使用 AgentScope ReAct。"""
        return True

    @field_validator("agent_backend")
    @classmethod
    def validate_agent_backend(cls, v: str) -> str:
        """只保留 AgentScope 后端，避免旧单轮 LLM 接口重新进入主路径。"""
        if v.strip().lower() != "agentscope":
            msg = "agent_backend only supports 'agentscope'"
            raise ValueError(msg)
        return v

    @field_validator("players")
    @classmethod
    def validate_player_names_unique(
        cls, v: list[PlayerConfig] | None
    ) -> list[PlayerConfig] | None:
        """校验所有玩家名称唯一。"""
        if v is None:
            return v
        names = [p.name for p in v]
        if len(names) != len(set(names)):
            duplicates = {name for name in names if names.count(name) > 1}
            msg = f"Duplicate player names found: {duplicates}"
            raise ValueError(msg)
        return v

    @model_validator(mode="after")
    def validate_roster_source(self) -> "PlayersConfig":
        has_players = self.players is not None
        has_roster = self.player_roster is not None
        if has_players == has_roster:
            msg = "Provide either players or player_roster, but not both"
            raise ValueError(msg)
        return self
