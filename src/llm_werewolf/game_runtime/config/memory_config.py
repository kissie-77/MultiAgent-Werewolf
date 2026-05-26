"""记忆框架配置。"""

from pydantic import BaseModel, Field


class MemoryConfig(BaseModel):
    """统一控制记忆框架行为的配置。"""

    enabled: bool = Field(default=True, description="是否启用记忆框架。")
    enable_working_memory: bool = Field(default=True, description="是否启用工作记忆。")
    enable_episodic_memory: bool = Field(default=True, description="是否启用情景记忆。")
    enable_semantic_memory: bool = Field(default=True, description="是否启用语义记忆。")
    working_max_rounds: int = Field(default=5, ge=1, description="工作记忆保留的历史轮数。")
    working_max_dynamic_items: int = Field(
        default=20,
        ge=1,
        description="每轮动态记忆最多保留条数。",
    )
    semantic_top_k: int = Field(default=3, ge=0, description="每局注入的跨局经验卡片数量。")
    extract_semantic_on_game_end: bool = Field(
        default=False,
        description="局结束时是否启用情景到语义的提炼接口。",
    )

    # ── ReMe 集成 ──────────────────────────────────────────────
    reme_enabled: bool = Field(default=True, description="是否启用 ReMe 向量存储后端。")
    reme_llm_base_url: str = Field(default="", description="ReMe LLM 的 OpenAI 兼容端点。")
    reme_llm_api_key: str = Field(default="", description="ReMe LLM 的 API Key。")
    reme_embedding_base_url: str = Field(default="", description="ReMe Embedding 的 OpenAI 兼容端点。")
    reme_embedding_api_key: str = Field(default="", description="ReMe Embedding 的 API Key。")
    reme_embedding_model: str = Field(default="BAAI/bge-m3", description="ReMe Embedding 模型名称。")
    reme_working_dir: str = Field(default=".reme", description="ReMe 本地数据存储目录。")
    reme_compress_working_memory: bool = Field(
        default=False,
        description="是否用 LLM 语义压缩替代工作记忆的规则式压缩。",
    )
