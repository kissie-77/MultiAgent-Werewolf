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
    semantic_data_dir: str = Field(
        default="data/semantic_cards",
        description="语义记忆默认 JSON 存储目录。",
    )
    extract_semantic_on_game_end: bool = Field(
        default=False,
        description="局结束时是否启用情景到语义的提炼接口。",
    )
