"""Legacy REST routes kept for backward compatibility."""

from __future__ import annotations

from typing import Annotated

from fastapi import Query, Depends, APIRouter, HTTPException

from llm_werewolf.interface.api.deps import get_runs_dir, get_configs_dir, get_eval_runs_dir
from llm_werewolf.interface.api.models import (
    RunDetail,
    RoleDetail,
    ApiResponse,
    GamePageData,
    HomePageData,
    ReplayPageData,
    ContentPageData,
    RunListPageData,
    RoleListPageData,
    StrategyPageData,
    ModelListPageData,
    NightPhasePageData,
    ModelDetailPageData,
    ShareReplayPageData,
    ModelComparePageData,
)
from llm_werewolf.game_runtime.roles.catalog import get_definition
from llm_werewolf.interface.api.services.runs import paginate_runs, get_run_detail
from llm_werewolf.interface.api.services.pages import build_game_page, build_home_page
from llm_werewolf.interface.api.services.config import (
    compare_models,
    get_model_detail,
    list_models_page,
)
from llm_werewolf.interface.api.services.replay import get_replay_page, get_share_replay_page
from llm_werewolf.interface.api.services.catalog import get_role_detail, list_roles_page
from llm_werewolf.interface.api.services.content import (
    get_about_page,
    get_features_page,
    get_strategy_page,
    get_how_to_play_page,
    get_night_phase_page,
)

home_router = APIRouter(prefix="/home", tags=["pages:home"])
game_router = APIRouter(prefix="/game", tags=["pages:game"])
content_router = APIRouter(prefix="/content", tags=["pages:content"])
roles_router = APIRouter(prefix="/roles", tags=["pages:roles"])
models_router = APIRouter(prefix="/models", tags=["pages:models"])
runs_router = APIRouter(prefix="/runs", tags=["runs"])
replay_router = APIRouter(prefix="/replay", tags=["pages:replay"])

_CONTENT_BUILDERS = {
    "about": get_about_page,
    "features": get_features_page,
    "how-to-play": get_how_to_play_page,
}


@home_router.get("", response_model=ApiResponse[HomePageData])
def get_home_page(
    runs_dir=Depends(get_runs_dir),
    eval_runs_dir=Depends(get_eval_runs_dir),
    configs_dir=Depends(get_configs_dir),
) -> ApiResponse[HomePageData]:
    return ApiResponse(data=build_home_page(runs_dir, eval_runs_dir, configs_dir))


@game_router.get("", response_model=ApiResponse[GamePageData])
def game_page(
    run_id: Annotated[str | None, Query()] = None,
    source: Annotated[str | None, Query(pattern="^(runs|eval)$")] = None,
    config_id: Annotated[str | None, Query()] = None,
    runs_dir=Depends(get_runs_dir),
    eval_runs_dir=Depends(get_eval_runs_dir),
) -> ApiResponse[GamePageData]:
    data = build_game_page(
        runs_dir, eval_runs_dir, run_id=run_id, source=source, config_id=config_id
    )
    if run_id and data is None:
        raise HTTPException(status_code=404, detail=f"Run not found: {run_id}")
    if data is None:
        data = build_game_page(runs_dir, eval_runs_dir)
    return ApiResponse(data=data)


@content_router.get("/about", response_model=ApiResponse[ContentPageData])
def about_page() -> ApiResponse[ContentPageData]:
    return ApiResponse(data=get_about_page())


@content_router.get("/features", response_model=ApiResponse[ContentPageData])
def features_page() -> ApiResponse[ContentPageData]:
    return ApiResponse(data=get_features_page())


@content_router.get("/how-to-play", response_model=ApiResponse[ContentPageData])
def how_to_play_page() -> ApiResponse[ContentPageData]:
    return ApiResponse(data=get_how_to_play_page())


@content_router.get("/night-phase", response_model=ApiResponse[NightPhasePageData])
def night_phase_page() -> ApiResponse[NightPhasePageData]:
    return ApiResponse(data=get_night_phase_page())


@content_router.get("/strategy", response_model=ApiResponse[StrategyPageData])
def strategy_page() -> ApiResponse[StrategyPageData]:
    return ApiResponse(data=get_strategy_page())


@content_router.get("/{page_key}", response_model=ApiResponse[ContentPageData])
def generic_content_page(page_key: str) -> ApiResponse[ContentPageData]:
    builder = _CONTENT_BUILDERS.get(page_key)
    if builder is None:
        raise HTTPException(status_code=404, detail=f"Unknown content page: {page_key}")
    return ApiResponse(data=builder())


@roles_router.get("", response_model=ApiResponse[RoleListPageData])
def roles_list_page() -> ApiResponse[RoleListPageData]:
    return ApiResponse(data=list_roles_page())


@roles_router.get("/{role_key}", response_model=ApiResponse[RoleDetail])
def role_detail_page(role_key: str) -> ApiResponse[RoleDetail]:
    try:
        get_definition(role_key)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=f"Unknown role: {role_key}") from exc
    return ApiResponse(data=get_role_detail(role_key))


@models_router.get("", response_model=ApiResponse[ModelListPageData])
def models_list_page(configs_dir=Depends(get_configs_dir)) -> ApiResponse[ModelListPageData]:
    return ApiResponse(data=list_models_page(configs_dir))


@models_router.get("/compare", response_model=ApiResponse[ModelComparePageData])
def models_compare_page(
    ids: Annotated[list[str], Query(min_length=2)],
) -> ApiResponse[ModelComparePageData]:
    return ApiResponse(data=compare_models(ids))


@models_router.get("/{model_id}", response_model=ApiResponse[ModelDetailPageData])
def model_detail_page(
    model_id: str,
    configs_dir=Depends(get_configs_dir),
) -> ApiResponse[ModelDetailPageData]:
    return ApiResponse(data=get_model_detail(model_id, configs_dir))


@runs_router.get("", response_model=ApiResponse[RunListPageData])
def list_runs(
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
    source: Annotated[str | None, Query(pattern="^(runs|eval)$")] = None,
    runs_dir=Depends(get_runs_dir),
    eval_runs_dir=Depends(get_eval_runs_dir),
) -> ApiResponse[RunListPageData]:
    return ApiResponse(
        data=RunListPageData(
            runs=paginate_runs(
                runs_dir,
                eval_runs_dir,
                page=page,
                page_size=page_size,
                source=source,
            )
        )
    )


@runs_router.get("/{run_id}", response_model=ApiResponse[RunDetail])
def get_run(
    run_id: str,
    source: Annotated[str | None, Query(pattern="^(runs|eval)$")] = None,
    runs_dir=Depends(get_runs_dir),
    eval_runs_dir=Depends(get_eval_runs_dir),
) -> ApiResponse[RunDetail]:
    detail = get_run_detail(run_id, runs_dir, eval_runs_dir, source=source)
    if detail is None:
        raise HTTPException(status_code=404, detail=f"Run not found: {run_id}")
    return ApiResponse(data=detail)


@replay_router.get("/{run_id}", response_model=ApiResponse[ReplayPageData])
def replay_page(
    run_id: str,
    source: Annotated[str | None, Query(pattern="^(runs|eval)$")] = None,
    view: Annotated[str, Query(pattern="^(public|god)$")] = "public",
    viewer_id: Annotated[str | None, Query()] = None,
    runs_dir=Depends(get_runs_dir),
    eval_runs_dir=Depends(get_eval_runs_dir),
) -> ApiResponse[ReplayPageData]:
    page = get_replay_page(
        run_id,
        runs_dir,
        eval_runs_dir,
        source=source,
        view=view,
        viewer_id=viewer_id,
    )
    if page is None:
        raise HTTPException(status_code=404, detail=f"Replay not found: {run_id}")
    return ApiResponse(data=page)


@replay_router.get("/{run_id}/share", response_model=ApiResponse[ShareReplayPageData])
def share_replay_page(
    run_id: str,
    source: Annotated[str | None, Query(pattern="^(runs|eval)$")] = None,
    runs_dir=Depends(get_runs_dir),
    eval_runs_dir=Depends(get_eval_runs_dir),
) -> ApiResponse[ShareReplayPageData]:
    page = get_share_replay_page(run_id, runs_dir, eval_runs_dir, source=source)
    if page is None:
        raise HTTPException(status_code=404, detail=f"Replay not found: {run_id}")
    return ApiResponse(data=page)
