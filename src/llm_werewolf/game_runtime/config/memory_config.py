"""Memory framework configuration."""

from pydantic import Field, BaseModel


class MemoryConfig(BaseModel):
    """Central switches for the agent memory framework."""

    enabled: bool = Field(default=True, description="Enable the memory framework.")
    enable_working_memory: bool = Field(
        default=True,
        description=(
            "Enable prompt-scoped working memory. When disabled, semantic and procedural "
            "memory are not injected into decision prompts."
        ),
    )
    enable_episodic_memory: bool = Field(default=True, description="Enable episodic memory.")
    enable_semantic_memory: bool = Field(
        default=True,
        description="Enable semantic skill retrieval, weight updates, and cross-game extraction.",
    )
    working_max_rounds: int = Field(
        default=5, ge=1, description="Number of historical round summaries kept in working memory."
    )
    working_max_dynamic_items: int = Field(
        default=20, ge=1, description="Maximum dynamic memory items retained per round."
    )
    working_max_persistent_chars: int = Field(
        default=4000, ge=100, description="Maximum total characters in persistent memory zone."
    )
    semantic_top_k: int = Field(
        default=3, ge=0, description="Number of role skill cards injected at game start."
    )
    semantic_max_cards_good: int = Field(
        default=8, ge=1, description="Maximum semantic cards retained for non-werewolf roles."
    )
    semantic_max_cards_wolf: int = Field(
        default=10, ge=1, description="Maximum semantic cards retained for werewolf roles."
    )
    extract_semantic_on_game_end: bool = Field(
        default=False,
        description="Extract semantic skill candidates from episodic memory at game end.",
    )
    enable_llm_working_compression: bool = Field(
        default=True,
        description="Use LLM for working memory compression. Falls back to rule-based if unavailable.",
    )
    working_compression_base_url: str = Field(
        default="", description="OpenAI-compatible base URL for working memory LLM compression."
    )
    working_compression_api_key: str = Field(
        default="", description="API key for working memory LLM compression."
    )
    working_compression_model: str = Field(
        default="default", description="Model name for working memory LLM compression."
    )
    working_compression_timeout: float = Field(
        default=30.0, description="Timeout in seconds for LLM compression API calls."
    )
    enable_llm_semantic_extraction: bool = Field(
        default=False,
        description="Use LLM to extract semantic skill candidates before rule fallback.",
    )
