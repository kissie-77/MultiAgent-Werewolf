from pydantic import Field, BaseModel, computed_field, field_validator
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
        description="Agent backend: 'agentscope' (default) or 'openai' (legacy LLMAgent)",
    )
    default_plan: str = Field(
        default="default",
        description="Default plan strategy for AgentScope RolePrompts / PlanStrategies",
    )
    players: list[PlayerConfig] = Field(
        ...,
        title="Player List",
        description="List of player configs, you should define it under ./configs/<name>.yaml",
        min_length=6,
        max_length=20,
    )

    @computed_field  # type: ignore[prop-decorator]
    @property
    def use_agentscope_backend(self) -> bool:
        """YAML ``agent_backend`` 选择 AgentScope ReAct（非旧版 OpenAI）时为 True。"""
        return self.agent_backend.strip().lower() not in {"openai", "legacy", "llm"}

    @field_validator("players")
    @classmethod
    def validate_player_names_unique(cls, v: list[PlayerConfig]) -> list[PlayerConfig]:
        """校验所有玩家名称唯一。"""
        names = [p.name for p in v]
        if len(names) != len(set(names)):
            duplicates = {name for name in names if names.count(name) > 1}
            msg = f"Duplicate player names found: {duplicates}"
            raise ValueError(msg)
        return v
