"""Settings API schemas (browser -> server .env for LLM keys)."""

from __future__ import annotations

from pydantic import Field, BaseModel


class ApiKeySlotStatus(BaseModel):
    env_name: str
    configured: bool
    masked: str | None = None


class ApiKeysStatusResponse(BaseModel):
    keys: dict[str, ApiKeySlotStatus]
    env_file: str
    writable: bool = True


class UpdateApiKeysRequest(BaseModel):
    deepseek: str | None = Field(default=None, description="DeepSeek API key")
    openai: str | None = Field(default=None, description="OpenAI API key")
    gemini: str | None = Field(default=None, description="Gemini API key")
    claude: str | None = Field(default=None, description="Anthropic Claude API key")
    doubao: str | None = Field(default=None, description="Volcengine Ark / Doubao API key")


class UpdateApiKeysResponse(BaseModel):
    updated_env_names: list[str]
    keys: dict[str, ApiKeySlotStatus]
    message: str = "API keys saved to server .env"
