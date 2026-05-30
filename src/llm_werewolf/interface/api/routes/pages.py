"""Unified page API — one endpoint per frontend screen with full data."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query

from llm_werewolf.interface.api.deps import get_configs_dir, get_eval_runs_dir, get_runs_dir
from llm_werewolf.interface.api.models import ApiResponse
from llm_werewolf.interface.api.models.page_spec import get_page_spec, list_page_specs
from llm_werewolf.interface.api.services.config import compare_models
from llm_werewolf.interface.api.services.pages import (
    build_about_page,
    build_features_page,
    build_game_page,
    build_home_page,
    build_how_to_play_page,
    build_model_detail_page,
    build_models_list_page,
    build_night_phase_page_enriched,
    build_replay_page_enriched,
    build_role_detail_page,
    build_roles_list_page,
    build_share_replay_page_enriched,
    build_strategy_page_enriched,
)
router = APIRouter(prefix="/pages", tags=["pages"])


@router.get("/spec")
def page_specs() -> ApiResponse[list]:
    """返回所有页面的字段说明（前端对接文档）。"""
    return ApiResponse(data=[s.model_dump() for s in list_page_specs()])


@router.get("/spec/{page_key}")
def page_spec_detail(page_key: str) -> ApiResponse[Any]:
    spec = get_page_spec(page_key)
    if spec is None:
        raise HTTPException(status_code=404, detail=f"Unknown page: {page_key}")
    return ApiResponse(data=spec.model_dump())


@router.get("/home")
def page_home(
    runs_dir=Depends(get_runs_dir),
    eval_runs_dir=Depends(get_eval_runs_dir),
    configs_dir=Depends(get_configs_dir),
) -> ApiResponse[Any]:
    """进入页。"""
    return ApiResponse(data=build_home_page(runs_dir, eval_runs_dir, configs_dir).model_dump())


@router.get("/game")
def page_game(
    run_id: str | None = Query(None),
    source: str | None = Query(None, pattern="^(runs|eval)$"),
    config_id: str | None = Query(None),
    runs_dir=Depends(get_runs_dir),
    eval_runs_dir=Depends(get_eval_runs_dir),
) -> ApiResponse[Any]:
    """主游戏页。"""
    data = build_game_page(
        runs_dir, eval_runs_dir, run_id=run_id, source=source, config_id=config_id
    )
    if run_id and data is None:
        raise HTTPException(status_code=404, detail=f"Run not found: {run_id}")
    return ApiResponse(data=(data or build_game_page(runs_dir, eval_runs_dir)).model_dump())


@router.get("/about")
def page_about(configs_dir=Depends(get_configs_dir)) -> ApiResponse[Any]:
    """AI 狼人杀介绍页。"""
    return ApiResponse(data=build_about_page(configs_dir).model_dump())


@router.get("/features")
def page_features() -> ApiResponse[Any]:
    """功能介绍页。"""
    return ApiResponse(data=build_features_page().model_dump())


@router.get("/how-to-play")
def page_how_to_play() -> ApiResponse[Any]:
    """玩法说明页。"""
    return ApiResponse(data=build_how_to_play_page().model_dump())


@router.get("/night-phase")
def page_night_phase() -> ApiResponse[Any]:
    """狼人杀夜晚阶段介绍页。"""
    return ApiResponse(data=build_night_phase_page_enriched().model_dump())


@router.get("/strategy")
def page_strategy() -> ApiResponse[Any]:
    """攻略页。"""
    return ApiResponse(data=build_strategy_page_enriched().model_dump())


@router.get("/roles")
def page_roles() -> ApiResponse[Any]:
    """角色列表页。"""
    return ApiResponse(data=build_roles_list_page().model_dump())


@router.get("/roles/{role_key}")
def page_role_detail(role_key: str) -> ApiResponse[Any]:
    """单个角色详情页。"""
    try:
        return ApiResponse(data=build_role_detail_page(role_key).model_dump())
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=f"Unknown role: {role_key}") from exc


@router.get("/models")
def page_models(
    runs_dir=Depends(get_runs_dir),
    eval_runs_dir=Depends(get_eval_runs_dir),
    configs_dir=Depends(get_configs_dir),
) -> ApiResponse[Any]:
    """AI 模型列表页。"""
    return ApiResponse(data=build_models_list_page(runs_dir, eval_runs_dir, configs_dir).model_dump())


@router.get("/models/compare")
def page_models_compare(
    ids: list[str] = Query(..., min_length=2),
) -> ApiResponse[Any]:
    """AI 模型对比页。"""
    return ApiResponse(data=compare_models(ids).model_dump())


@router.get("/models/{model_id}")
def page_model_detail(
    model_id: str,
    runs_dir=Depends(get_runs_dir),
    eval_runs_dir=Depends(get_eval_runs_dir),
    configs_dir=Depends(get_configs_dir),
) -> ApiResponse[Any]:
    """单个 AI 模型详情页。"""
    return ApiResponse(
        data=build_model_detail_page(model_id, runs_dir, eval_runs_dir, configs_dir).model_dump()
    )


@router.get("/replay")
def page_replay(
    run_id: str = Query(...),
    source: str | None = Query(None, pattern="^(runs|eval)$"),
    runs_dir=Depends(get_runs_dir),
    eval_runs_dir=Depends(get_eval_runs_dir),
) -> ApiResponse[Any]:
    """本局游戏复盘页。"""
    data = build_replay_page_enriched(run_id, runs_dir, eval_runs_dir, source=source)
    if data is None:
        raise HTTPException(status_code=404, detail=f"Replay not found: {run_id}")
    return ApiResponse(data=data.model_dump())


@router.get("/share-replay")
def page_share_replay(
    run_id: str = Query(...),
    source: str | None = Query(None, pattern="^(runs|eval)$"),
    runs_dir=Depends(get_runs_dir),
    eval_runs_dir=Depends(get_eval_runs_dir),
) -> ApiResponse[Any]:
    """分享复盘页。"""
    data = build_share_replay_page_enriched(run_id, runs_dir, eval_runs_dir, source=source)
    if data is None:
        raise HTTPException(status_code=404, detail=f"Replay not found: {run_id}")
    return ApiResponse(data=data.model_dump())
