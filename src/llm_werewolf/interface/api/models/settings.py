"""Settings API schemas (browser -> server .env for LLM keys)."""

from __future__ import annotations

from pydantic import Field, BaseModel


class ApiKeySlotStatus(BaseModel):
    env_name: str
    configured: bool
    masked: str | None = None


class ApiKeysStatusResponse(BaseModel):
    keys: dict[str, ApiKeySlotStatus]
    env_fields: dict[str, ApiKeySlotStatus] = Field(default_factory=dict)
    env_file: str
    writable: bool = True


class UpdateApiKeysRequest(BaseModel):
    deepseek: str | None = Field(default=None, description="DeepSeek API key")
    openai: str | None = Field(default=None, description="OpenAI API key")
    gemini: str | None = Field(default=None, description="Gemini API key")
    claude: str | None = Field(default=None, description="Anthropic Claude API key")
    doubao: str | None = Field(default=None, description="Volcengine Ark / Doubao API key")
    fields: dict[str, str] | None = Field(
        default=None,
        description="Generic env_name -> value map (provider form)",
    )


class ProviderFieldSchema(BaseModel):
    env_name: str
    label: str
    required: bool = True
    secret: bool = True
    example: str = ""
    description: str = ""


class ProviderSchema(BaseModel):
    provider_id: str
    display_name: str
    fields: list[ProviderFieldSchema]


class ProvidersListResponse(BaseModel):
    providers: list[ProviderSchema]
    default_provider_id: str = "doubao"


class UpdateApiKeysResponse(BaseModel):
    updated_env_names: list[str]
    keys: dict[str, ApiKeySlotStatus]
    message: str = "API keys saved to server .env"


class AvailableModelOption(BaseModel):
    provider_id: str
    provider_label: str
    display_name: str


class AvailableModelsResponse(BaseModel):
    models: list[AvailableModelOption]
    default_provider_id: str = "doubao"
