"""Canonical LLM provider definitions for env templates and roster resolution.

Each provider maps to a small, fixed set of environment variables (never per-seat).
Standard boards default to ``doubao``; mixed-model matches override seats at
``POST /games/start`` using these ``provider_id`` values.

Env naming convention
---------------------
* ``*_API_KEY``  — secret (required to call the provider)
* ``*_MODEL``    — model or deployment id (optional when a sensible default exists)
* ``*_BASE_URL`` — OpenAI-compatible API root (optional; registry supplies default)
* Doubao uses legacy names ``ARK_API_KEY`` / ``ARK_EP`` (already in standard YAML)
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ProviderEnvField:
    """One ``.env`` variable belonging to a provider."""

    env_name: str
    label: str
    required: bool = True
    secret: bool = True
    example: str = ""
    description: str = ""


@dataclass(frozen=True)
class ProviderSpec:
    """Static metadata for a supported vendor."""

    provider_id: str
    display_name: str
    env_fields: tuple[ProviderEnvField, ...]
    default_base_url: str
    default_model: str | None = None
    notes: str = ""

    @property
    def api_key_env(self) -> str:
        for field in self.env_fields:
            if field.secret and field.required:
                return field.env_name
        return self.env_fields[0].env_name

    @property
    def model_env(self) -> str | None:
        for field in self.env_fields:
            if field.secret:
                continue
            if "MODEL" in field.env_name or field.env_name.endswith("_EP"):
                return field.env_name
        return None


# provider_id → spec (order = UI / .env.example section order)
PROVIDER_REGISTRY: dict[str, ProviderSpec] = {
    "doubao": ProviderSpec(
        provider_id="doubao",
        display_name="豆包 (Volcengine Ark)",
        env_fields=(
            ProviderEnvField(
                env_name="ARK_API_KEY",
                label="API Key",
                example="your_ark_api_key_here",
                description="火山方舟控制台 API Key；标准对局默认供应商",
            ),
            ProviderEnvField(
                env_name="ARK_EP",
                label="Endpoint ID",
                secret=False,
                example="ep-xxxxxxxxxx-yyyy",
                description="推理接入点 ID（model_env）；非 Key 本身",
            ),
        ),
        default_base_url="https://ark.cn-beijing.volces.com/api/v3",
        default_model=None,
        notes="标准 ``standard-*p.yaml`` 使用 ``model_env: ARK_EP``。",
    ),
    "deepseek": ProviderSpec(
        provider_id="deepseek",
        display_name="DeepSeek",
        env_fields=(
            ProviderEnvField(
                env_name="DEEPSEEK_API_KEY",
                label="API Key",
                example="sk-xxxxxxxx",
            ),
            ProviderEnvField(
                env_name="DEEPSEEK_MODEL",
                label="Model",
                required=False,
                secret=False,
                example="deepseek-v4-flash",
                description="留空则使用默认模型",
            ),
        ),
        default_base_url="https://api.deepseek.com/v1",
        default_model="deepseek-v4-flash",
    ),
    "openai": ProviderSpec(
        provider_id="openai",
        display_name="OpenAI (GPT)",
        env_fields=(
            ProviderEnvField(
                env_name="OPENAI_API_KEY",
                label="API Key",
                example="sk-xxxxxxxx",
            ),
            ProviderEnvField(
                env_name="OPENAI_MODEL",
                label="Model",
                required=False,
                secret=False,
                example="gpt-4o",
            ),
        ),
        default_base_url="https://api.openai.com/v1",
        default_model="gpt-4o",
    ),
    "gemini": ProviderSpec(
        provider_id="gemini",
        display_name="Google Gemini",
        env_fields=(
            ProviderEnvField(
                env_name="GEMINI_API_KEY",
                label="API Key",
                example="AIzaxxxxxxxx",
            ),
            ProviderEnvField(
                env_name="GEMINI_MODEL",
                label="Model",
                required=False,
                secret=False,
                example="gemini-2.0-flash",
            ),
        ),
        default_base_url="https://generativelanguage.googleapis.com/v1beta/openai",
        default_model="gemini-2.0-flash",
    ),
    "claude": ProviderSpec(
        provider_id="claude",
        display_name="Anthropic Claude",
        env_fields=(
            ProviderEnvField(
                env_name="ANTHROPIC_API_KEY",
                label="API Key",
                example="sk-ant-xxxxxxxx",
            ),
            ProviderEnvField(
                env_name="ANTHROPIC_MODEL",
                label="Model",
                required=False,
                secret=False,
                example="claude-sonnet-4-20250514",
            ),
        ),
        default_base_url="https://api.anthropic.com/v1",
        default_model="claude-sonnet-4-20250514",
    ),
    "kimi": ProviderSpec(
        provider_id="kimi",
        display_name="Kimi (Moonshot)",
        env_fields=(
            ProviderEnvField(
                env_name="KIMI_API_KEY",
                label="API Key",
                example="sk-xxxxxxxx",
                description="Moonshot 官方 Key；VibeAPI 代理可填其 Key 并改 KIMI_BASE_URL",
            ),
            ProviderEnvField(
                env_name="KIMI_BASE_URL",
                label="Base URL",
                required=False,
                secret=False,
                example="https://api.moonshot.cn/v1",
                description="代理可用 https://www.vibeapi.cn/v1",
            ),
            ProviderEnvField(
                env_name="KIMI_MODEL",
                label="Model",
                required=False,
                secret=False,
                example="kimi-k2.5",
            ),
        ),
        default_base_url="https://api.moonshot.cn/v1",
        default_model="kimi-k2.5",
        notes="历史配置使用 VIBE_API_KEY；新模板统一为 KIMI_*，迁移时二选一即可。",
    ),
    "glm": ProviderSpec(
        provider_id="glm",
        display_name="智谱 GLM",
        env_fields=(
            ProviderEnvField(
                env_name="GLM_API_KEY",
                label="API Key",
                example="xxxxxxxx.xxxxxxxx",
            ),
            ProviderEnvField(
                env_name="GLM_MODEL",
                label="Model",
                required=False,
                secret=False,
                example="glm-4-flash",
            ),
        ),
        default_base_url="https://open.bigmodel.cn/api/paas/v4",
        default_model="glm-4-flash",
    ),
    "minimax": ProviderSpec(
        provider_id="minimax",
        display_name="MiniMax",
        env_fields=(
            ProviderEnvField(
                env_name="MINIMAX_API_KEY",
                label="API Key",
                example="eyJhbGciOi...",
            ),
            ProviderEnvField(
                env_name="MINIMAX_GROUP_ID",
                label="Group ID",
                secret=False,
                example="1234567890",
                description="MiniMax 开放平台 Group Id",
            ),
            ProviderEnvField(
                env_name="MINIMAX_MODEL",
                label="Model",
                required=False,
                secret=False,
                example="abab6.5s-chat",
            ),
        ),
        default_base_url="https://api.minimaxi.com/v1",
        default_model="abab6.5s-chat",
    ),
}

DEFAULT_PROVIDER_ID = "doubao"

SUPPORTED_PROVIDER_IDS: tuple[str, ...] = tuple(PROVIDER_REGISTRY.keys())


def get_provider(provider_id: str) -> ProviderSpec:
    spec = PROVIDER_REGISTRY.get(provider_id)
    if spec is None:
        supported = ", ".join(SUPPORTED_PROVIDER_IDS)
        msg = f"Unknown provider_id {provider_id!r}; supported: {supported}"
        raise ValueError(msg)
    return spec


def all_env_var_names() -> frozenset[str]:
    names: set[str] = set()
    for spec in PROVIDER_REGISTRY.values():
        for field in spec.env_fields:
            names.add(field.env_name)
    return frozenset(names)
