"""FastAPI application factory."""

from __future__ import annotations

import os

import fire
import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from llm_werewolf.observability.health import check_readiness
from llm_werewolf.paths import ARTIFACTS_DIR
from llm_werewolf.interface.api.routes import (
    actions_router,
    content_router,
    game_router,
    home_router,
    models_router,
    pages_router,
    replay_router,
    roles_router,
    runs_router,
)

API_PREFIX = "/api/v1"

PAGE_ROUTE_MAP = {
    "home": f"{API_PREFIX}/pages/home",
    "game": f"{API_PREFIX}/pages/game",
    "night_phase": f"{API_PREFIX}/pages/night-phase",
    "about": f"{API_PREFIX}/pages/about",
    "features": f"{API_PREFIX}/pages/features",
    "how_to_play": f"{API_PREFIX}/pages/how-to-play",
    "replay": f"{API_PREFIX}/pages/replay?run_id={{run_id}}",
    "share_replay": f"{API_PREFIX}/pages/share-replay?run_id={{run_id}}",
    "strategy": f"{API_PREFIX}/pages/strategy",
    "roles": f"{API_PREFIX}/pages/roles",
    "role_detail": f"{API_PREFIX}/pages/roles/{{role_key}}",
    "models": f"{API_PREFIX}/pages/models",
    "model_detail": f"{API_PREFIX}/pages/models/{{model_id}}",
    "model_compare": f"{API_PREFIX}/pages/models/compare?ids=a&ids=b",
    "page_spec": f"{API_PREFIX}/pages/spec",
    "actions_spec": f"{API_PREFIX}/actions/spec",
    "start_modes": f"{API_PREFIX}/games/modes",
    "start_game": f"{API_PREFIX}/games/start",
    "game_status": f"{API_PREFIX}/games/{{run_id}}/status",
    "cancel_game": f"{API_PREFIX}/games/{{run_id}}/cancel",
    "trigger_post_game": f"{API_PREFIX}/runs/{{run_id}}/post-game",
    "compare_models_post": f"{API_PREFIX}/models/compare",
}


def create_app() -> FastAPI:
    app = FastAPI(
        title="LLM Werewolf API",
        description="Frontend-facing HTTP API for AI Werewolf pages.",
        version="0.1.0",
    )
    allowed_origins = [
        origin.strip()
        for origin in os.environ.get(
            "WEREWOLF_CORS_ORIGINS",
            "http://localhost:3000,http://localhost:5173",
        ).split(",")
        if origin.strip()
    ]
    app.add_middleware(
        CORSMiddleware,
        allow_origins=allowed_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/ready")
    def ready() -> JSONResponse:
        require_llm = os.environ.get("OBS_READY_REQUIRE_LLM", os.environ.get("OBS_READY_REQUIRE_ARK", "1")) != "0"
        payload = check_readiness(artifacts_dir=ARTIFACTS_DIR, require_llm_key=require_llm)
        status_code = 200 if payload.get("status") == "ready" else 503
        return JSONResponse(content=payload, status_code=status_code)

    @app.get(f"{API_PREFIX}/pages")
    def page_route_index() -> dict[str, str]:
        """前端页面 → API 路径索引。"""
        return PAGE_ROUTE_MAP

    app.include_router(pages_router, prefix=API_PREFIX)
    app.include_router(actions_router, prefix=API_PREFIX)
    app.include_router(home_router, prefix=API_PREFIX)
    app.include_router(content_router, prefix=API_PREFIX)
    app.include_router(game_router, prefix=API_PREFIX)
    app.include_router(roles_router, prefix=API_PREFIX)
    app.include_router(models_router, prefix=API_PREFIX)
    app.include_router(runs_router, prefix=API_PREFIX)
    app.include_router(replay_router, prefix=API_PREFIX)

    return app


def entry(host: str = "127.0.0.1", port: int = 8000, reload: bool = False) -> None:
    """Start API server: ``werewolf-api`` or ``python -m llm_werewolf.interface.api.app``."""
    uvicorn.run(
        "llm_werewolf.interface.api.app:create_app",
        factory=True,
        host=host,
        port=port,
        reload=reload,
    )


def main() -> None:
    fire.Fire(entry)


if __name__ == "__main__":
    main()
