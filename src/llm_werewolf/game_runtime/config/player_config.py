import os

from pydantic import Field, BaseModel, computed_field, field_validator, model_validator
from typing_extensions import Self
from typing import Literal
from openai.types.shared import ReasoningEffort
from pydantic_core.core_schema import ValidationInfo

from llm_werewolf.game_runtime.config.memory_config import MemoryConfig
from llm_werewolf.strategy.registry.role_version_manifest import (
    DEFAULT_PROMPT_VERSION,
    DEFAULT_SKILL_VERSION,
    RoleVersionManifest,
)


class RoleVersionConfig(BaseModel):
    """Per-role prompt/skill version map; unset roles use defaults."""

    default_prompt_version: str = Field(
        default=DEFAULT_PROMPT_VERSION,
        description="Fallback when no prompt version folders exist; runtime uses latest by default.",
    )
    default_skill_version: str = Field(
        default=DEFAULT_SKILL_VERSION,
        description="Fallback when no skill version folders exist; runtime uses latest by default.",
    )
    prompt_versions: dict[str, str] = Field(
        default_factory=dict,
        description="Optional overrides: prompt_role_key -> prompt version.",
    )
    skill_versions: dict[str, str] = Field(
        default_factory=dict,
        description="Optional overrides: prompt_role_key -> skill version folder.",
    )

    def to_manifest(self) -> RoleVersionManifest:
        return RoleVersionManifest(
            default_prompt_version=self.default_prompt_version.strip(),
            default_skill_version=self.default_skill_version.strip(),
            prompt_versions={str(k): str(v) for k, v in self.prompt_versions.items()},
            skill_versions={str(k): str(v) for k, v in self.skill_versions.items()},
        )


class PlayerConfig(BaseModel):
    """单个玩家的游戏配置。

    智能体类型由 model 字段决定：
    - model="human"：通过控制台输入的人类玩家
    - model="demo"：离线 smoke 用确定性 DemoAgent（无需 API）
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


class PlanAssignmentConfig(BaseModel):
    """角色分配后的自动 plan 分流配置。"""

    enabled: bool = Field(
        default=False,
        description="Whether to assign role-specific plans to players without manual plan.",
    )
    mode: Literal["role_cycle", "role_random"] = Field(
        default="role_cycle",
        description="role_cycle assigns plans in order; role_random samples with seed support.",
    )
    seed: int | None = Field(
        default=None,
        description="Optional seed for deterministic role_random assignment in A/B tests.",
    )
    role_plans: dict[str, list[str]] = Field(
        default_factory=dict,
        description="Optional role prompt key -> plan names. Missing roles use defaults.",
    )


class PlayersConfig(BaseModel):
    """包含所有玩家及可选游戏设置的根配置。"""

    language: str = Field(
        default="en-US",
        title="Language",
        description="Language code for the game.",
        examples=["en-US", "zh-TW"],
    )
    agent_backend: str = Field(default="agentscope", description="Agent backend: 'agentscope'.")
    default_plan: str = Field(
        default="default",
        description="Default plan strategy for AgentScope RolePrompts / PlanStrategies",
    )
    memory: MemoryConfig = Field(
        default_factory=MemoryConfig, description="Memory framework configuration."
    )
    role_versions: RoleVersionConfig = Field(
        default_factory=RoleVersionConfig,
        description="Per-role prompt/skill version manifest.",
    )
    plan_assignment: PlanAssignmentConfig = Field(
        default_factory=PlanAssignmentConfig,
        description="Automatic role-specific plan assignment for players without manual plan.",
    )
    prompt_version: str = Field(
        default=DEFAULT_PROMPT_VERSION,
        description=(
            "Legacy default prompt version; synced into role_versions when unset."
        ),
        examples=["latest", "v1", "v2"],
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
    day_timeout: int | None = Field(
        default=None,
        ge=30,
        description="Optional override for day discussion timeout (seconds).",
    )
    vote_timeout: int | None = Field(
        default=None,
        ge=10,
        description="Optional override for voting timeout (seconds).",
    )
    night_timeout: int | None = Field(
        default=None,
        ge=10,
        description="Optional override for night action timeout (seconds).",
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

    @model_validator(mode="after")
    def sync_legacy_prompt_version(self) -> Self:
        """Keep YAML prompt_version as default for per-role packages."""
        if self.prompt_version.strip():
            legacy = self.prompt_version.strip().lower()
            if (
                self.role_versions.default_prompt_version == DEFAULT_PROMPT_VERSION
                and legacy != DEFAULT_PROMPT_VERSION
            ):
                self.role_versions.default_prompt_version = legacy
            elif legacy != self.role_versions.default_prompt_version and not self.role_versions.prompt_versions:
                self.role_versions.default_prompt_version = legacy
        return self

    def role_version_manifest(self) -> RoleVersionManifest:
        return self.role_versions.to_manifest()

    @field_validator("prompt_version")
    @classmethod
    def validate_prompt_version(cls, v: str) -> str:
        version = v.strip().lower()
        if version == "latest":
            return version
        if not version.startswith("v") or len(version) < 2:
            msg = f"prompt_version must look like 'latest' or 'v1', got '{v}'"
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
