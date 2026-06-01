"""Write-action request/response schemas for frontend POST APIs."""

from __future__ import annotations

from pydantic import BaseModel, Field

from llm_werewolf.interface.api.models.pages import GameSnapshot, ModelComparePageData


class StartGameRequest(BaseModel):
    config_id: str | None = Field(default=None, description="YAML stem under configs/")
    config_path: str | None = Field(default=None, description="Explicit config path")
    participation: str | None = Field(default=None, description="Entry mode key, e.g. all_agent")
    rules: str | None = Field(default=None, description="Entry rules key, e.g. basic")
    run_label: str | None = Field(default=None, description="Optional run directory prefix")


class StartGameResponse(BaseModel):
    run_id: str
    source: str = "runs"
    status: str
    config_id: str
    run_dir: str
    game_page_path: str
    status_path: str
    replay_page_path: str


class GameStatusResponse(BaseModel):
    run_id: str
    source: str = "runs"
    status: str
    snapshot: GameSnapshot | None = None
    error: str | None = None
    result_text: str | None = None
    has_post_game: bool = False
    has_replay: bool = False


class CancelGameResponse(BaseModel):
    run_id: str
    status: str
    message: str | None = None


class ModelCompareRequest(BaseModel):
    ids: list[str] = Field(..., min_length=2, max_length=8)


class ModelCompareResponse(BaseModel):
    compare: ModelComparePageData


class TriggerPostGameRequest(BaseModel):
    source: str | None = Field(default=None, pattern="^(runs|eval)$")
    force: bool = False


class TriggerPostGameResponse(BaseModel):
    run_id: str
    status: str
    message: str | None = None
    artifacts: list[str] = Field(default_factory=list)


class PageActionSpec(BaseModel):
    page_key: str
    frontend_route: str
    action: str
    method: str
    api_path: str
    description: str
    request_model: str | None = None
    response_model: str | None = None


class ActionSpecResponse(BaseModel):
    actions: list[PageActionSpec]
