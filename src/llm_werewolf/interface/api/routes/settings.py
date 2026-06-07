"""Server settings routes (browser-managed .env API keys)."""

from __future__ import annotations

import os
from typing import Annotated

from fastapi import Header, Request, APIRouter, HTTPException, Depends

from llm_werewolf.interface.api.deps import get_env_file_path
from llm_werewolf.interface.api.models import ApiResponse
from llm_werewolf.interface.api.models.settings import (
    ApiKeySlotStatus,
    UpdateApiKeysRequest,
    ApiKeysStatusResponse,
    UpdateApiKeysResponse,
)
from llm_werewolf.interface.api.services.env_store import (
    read_api_key_status,
    upsert_api_keys,
    slot_updates_from_request,
)

router = APIRouter(tags=["settings"])

_LOCAL_HOSTS = frozenset({"127.0.0.1", "::1", "localhost", "testclient"})


def _settings_token_configured() -> str | None:
    token = os.environ.get("WEREWOLF_SETTINGS_TOKEN", "").strip()
    return token or None


def _client_host(request: Request) -> str:
    if request.client is None:
        return ""
    return request.client.host or ""


def verify_settings_access(
    request: Request,
    x_settings_token: Annotated[str | None, Header()] = None,
) -> None:
    """Gate writes/reads of secrets.

    * When ``WEREWOLF_SETTINGS_TOKEN`` is set, the matching ``X-Settings-Token``
      header is always required.
    * Otherwise only loopback clients may access the endpoint.
    """
    configured = _settings_token_configured()
    if configured:
        if not x_settings_token or x_settings_token != configured:
            raise HTTPException(status_code=403, detail="Invalid or missing X-Settings-Token")
        return
    host = _client_host(request)
    if host not in _LOCAL_HOSTS:
        raise HTTPException(
            status_code=403,
            detail="Settings API is restricted to localhost; set WEREWOLF_SETTINGS_TOKEN for remote access",
        )


@router.get("/settings/api-keys")
def get_api_keys_status(
    _access: Annotated[None, Depends(verify_settings_access)],
    env_path=Depends(get_env_file_path),
) -> ApiResponse[ApiKeysStatusResponse]:
    raw = read_api_key_status(env_path=env_path)
    keys = {slot: ApiKeySlotStatus(**status) for slot, status in raw.items()}
    writable = True
    try:
        env_path.parent.mkdir(parents=True, exist_ok=True)
        probe = env_path.parent / ".settings_write_probe"
        probe.write_text("ok", encoding="utf-8")
        probe.unlink(missing_ok=True)
    except OSError:
        writable = False
    return ApiResponse(
        data=ApiKeysStatusResponse(
            keys=keys,
            env_file=str(env_path.as_posix()),
            writable=writable,
        )
    )


@router.post("/settings/api-keys")
def update_api_keys(
    body: UpdateApiKeysRequest,
    _access: Annotated[None, Depends(verify_settings_access)],
    env_path=Depends(get_env_file_path),
) -> ApiResponse[UpdateApiKeysResponse]:
    updates = slot_updates_from_request(body.model_dump())
    if not updates:
        raise HTTPException(status_code=400, detail="No API keys provided to save")
    try:
        written = upsert_api_keys(updates, env_path=env_path)
    except OSError as exc:
        raise HTTPException(status_code=500, detail=f"Failed to write .env: {exc}") from exc
    raw = read_api_key_status(env_path=env_path)
    keys = {slot: ApiKeySlotStatus(**status) for slot, status in raw.items()}
    return ApiResponse(
        data=UpdateApiKeysResponse(
            updated_env_names=written,
            keys=keys,
        )
    )
