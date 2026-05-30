"""Shared API response schemas."""

from __future__ import annotations

from typing import Any, Generic, TypeVar

from pydantic import BaseModel, Field

T = TypeVar("T")


class ApiResponse(BaseModel, Generic[T]):
    """Standard envelope for frontend consumption."""

    success: bool = True
    data: T
    message: str | None = None


class PageMeta(BaseModel):
    """Pagination metadata."""

    page: int = 1
    page_size: int = 20
    total: int = 0


class PaginatedList(BaseModel, Generic[T]):
    items: list[T] = Field(default_factory=list)
    meta: PageMeta = Field(default_factory=PageMeta)


class NavLink(BaseModel):
    key: str
    title: str
    path: str
    description: str | None = None


class ArtifactRef(BaseModel):
    name: str
    path: str
    kind: str = "file"


class PlayerBrief(BaseModel):
    player_id: str
    player_name: str
    role_name: str | None = None
    camp: str | None = None
    ai_model: str | None = None
    is_alive: bool | None = None


class RunSummary(BaseModel):
    run_id: str
    source: str  # runs | eval
    path: str
    created_at: str | None = None
    player_count: int | None = None
    winner_camp: str | None = None
    has_post_game: bool = False
    has_replay: bool = False


class RunDetail(RunSummary):
    roster: list[PlayerBrief] = Field(default_factory=list)
    game_result_text: str | None = None
    artifacts: list[ArtifactRef] = Field(default_factory=list)
    extra: dict[str, Any] = Field(default_factory=dict)
