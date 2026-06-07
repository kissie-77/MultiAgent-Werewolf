"""Server settings routes (browser-managed .env API keys)."""

from __future__ import annotations

import os
from typing import Annotated

from fastapi import Header, Request, APIRouter, HTTPException, Depends

from llm_werewolf.interface.api.deps import get_env_file_path
from llm_werewolf.interface.api.models import ApiResponse
from llm_werewolf.game_runtime.config.provider_registry import DEFAULT_PROVIDER_ID
from llm_werewolf.interface.api.models.settings import (
    ApiKeySlotStatus,
    ProviderSchema,
    UpdateApiKeysRequest,
    ApiKeysStatusResponse,
    UpdateApiKeysResponse,
    ProvidersListResponse,
    ProviderFieldSchema,
    AvailableModelOption,
    AvailableModelsResponse,
)
from llm_werewolf.interface.api.services.env_store import (
    read_api_key_status,
    read_provider_env_status,
    build_providers_schema,
    build_available_models,
    upsert_api_keys,
    slot_updates_from_request,
)

router = APIRouter(tags=["settings"])

_LOCAL_HOSTS = frozenset({"127.0.0.1", "::1", "localhost", "testclient", "0.0.0.0"})


def _is_local_client(host: str) -> bool:
    """Accept loopback and IPv4-mapped loopback (common on Windows)."""
    normalized = (host or "").strip().lower()
    if not normalized:
        return False
    if normalized in _LOCAL_HOSTS:
        return True
    if normalized.startswith("::ffff:"):
        return normalized.removeprefix("::ffff:") in {"127.0.0.1", "localhost"}
    return False


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
    if not _is_local_client(host):
        raise HTTPException(
            status_code=403,
            detail="Settings API is restricted to localhost; set WEREWOLF_SETTINGS_TOKEN for remote access",
        )


@router.get("/settings/providers")
def list_providers(
    _access: Annotated[None, Depends(verify_settings_access)],
) -> ApiResponse[ProvidersListResponse]:
    providers = [
        ProviderSchema(
            provider_id=item["provider_id"],
            display_name=item["display_name"],
            fields=[ProviderFieldSchema(**field) for field in item["fields"]],
        )
        for item in build_providers_schema()
    ]
    return ApiResponse(
        data=ProvidersListResponse(
            providers=providers,
            default_provider_id=DEFAULT_PROVIDER_ID,
        )
    )


@router.get("/settings/available-models")
def list_available_models(
    _access: Annotated[None, Depends(verify_settings_access)],
    env_path=Depends(get_env_file_path),
) -> ApiResponse[AvailableModelsResponse]:
    raw = build_available_models(env_path=env_path)
    models = [AvailableModelOption(**item) for item in raw]
    return ApiResponse(
        data=AvailableModelsResponse(
            models=models,
            default_provider_id=DEFAULT_PROVIDER_ID,
        )
    )


@router.get("/settings/api-keys")
def get_api_keys_status(
    _access: Annotated[None, Depends(verify_settings_access)],
    env_path=Depends(get_env_file_path),
) -> ApiResponse[ApiKeysStatusResponse]:
    raw = read_api_key_status(env_path=env_path)
    keys = {slot: ApiKeySlotStatus(**status) for slot, status in raw.items()}
    env_raw = read_provider_env_status(env_path=env_path)
    env_fields = {name: ApiKeySlotStatus(**status) for name, status in env_raw.items()}
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
            env_fields=env_fields,
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
    updates = slot_updates_from_request(body.model_dump(exclude_none=True))
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
