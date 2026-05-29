import os

from pydantic import Field, BaseModel, computed_field, field_validator, model_validator
from openai.types.shared import ReasoningEffort
from pydantic_core.core_schema import ValidationInfo
from typing_extensions import Self

from llm_werewolf.game_runtime.config.memory_config import MemoryConfig


class PlayerConfig(BaseModel):
    """单个玩家的游戏配置。

    智能体类型由 model 字段决定：
    - model="human"：通过控制台输入的人类玩家
    - model="demo"：用于测试的随机响应机器人
    - model=<model_name> + base_url：使用 ChatCompletion API 的 LLM 智能体
    """

    name: str = Field(..., description="Display name for the player")
    model: str | None = Field(
        default=None,
        title="Model Name",
        description="The model name of your player",
        examples=["gpt-5", "human", "demo"],
    )
    model_env: str | None = Field(
        default=None,
        title="Model Environment Variable",
        description=(
            "Environment variable name containing the model or endpoint id "
            "(e.g. ARK_EP for Volcengine Ark). Resolved at config load time."
        ),
        examples=["ARK_EP", "OPENAI_MODEL"],
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
        model = info.data.get("model") or ""
        model_env = info.data.get("model_env")
        is_builtin = model in {"human", "demo"}
        is_llm = not is_builtin and (bool(model) or bool(model_env))
        if is_llm and not v:
            label = model or model_env
            msg = f"base_url is required for LLM model '{label}'"
            raise ValueError(msg)
        return v

    @model_validator(mode="after")
    def resolve_model_from_env(self) -> Self:
        """从 model_env 解析 endpoint / model id（密钥类配置不进 YAML）。"""
        if self.model in {"human", "demo"}:
            return self
        if self.model_env:
            resolved = os.getenv(self.model_env, "").strip()
            if not resolved:
                msg = (
                    f"Environment variable '{self.model_env}' is not set "
                    f"(required for player '{self.name}')"
                )
                raise ValueError(msg)
            self.model = resolved
        elif not self.model:
            msg = f"Either model or model_env is required for player '{self.name}'"
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
    memory: MemoryConfig = Field(
        default_factory=MemoryConfig,
        description="Memory framework configuration.",
    )
    prompt_version: str = Field(
        default="v2",
        description="Prompt registry version (e.g. v2). Maps to strategy/prompts/<version>/",
        examples=["v2", "v3"],
    )
    vote_intention_concurrency: int = Field(
        default=1,
        ge=1,
        le=20,
        description=(
            "Maximum concurrent LLM calls for vote-intention fan-out. "
            "Set to the player count for fastest batches if the provider allows it."
        ),
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

    @field_validator("prompt_version")
    @classmethod
    def validate_prompt_version(cls, v: str) -> str:
        """只接受 v 前缀的小写版本号（如 v2、v3）。"""
        version = v.strip().lower()
        if not version.startswith("v") or len(version) < 2:
            msg = f"prompt_version must look like 'v2', got '{v}'"
            raise ValueError(msg)
        return version

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
