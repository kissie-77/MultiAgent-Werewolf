"""Game config and AI model registry service."""

from __future__ import annotations

import re
from pathlib import Path

import yaml

from llm_werewolf.interface.api.models.pages import (
    ModelCompareItem,
    ModelComparePageData,
    ModelConfigBrief,
    ModelDetailPageData,
    ModelListPageData,
    ModelUsageStat,
)
from llm_werewolf.interface.api.services.runs import aggregate_model_usage


def _infer_provider(config_path: Path, models: list[str]) -> str | None:
    name = config_path.stem.lower()
    if "doubao" in name or "ark" in name:
        return "volcengine_ark"
    if "deepseek" in name:
        return "deepseek"
    if "openai" in name:
        return "openai"
    if "gemini" in name:
        return "google"
    if "demo" in name or "human" in name:
        return "local"
    for model in models:
        low = model.lower()
        if "gpt" in low:
            return "openai"
        if "doubao" in low or "seed" in low:
            return "volcengine_ark"
        if "deepseek" in low:
            return "deepseek"
    return None


def _label_from_path(path: Path) -> str:
    return path.stem.replace("-", " ").replace("_", " ")


def _safe_load_config(path: Path) -> dict | None:
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else None
    except (OSError, yaml.YAMLError):
        return None


def _models_from_config(data: dict) -> list[str]:
    players = data.get("players") or []
    models: list[str] = []
    for player in players:
        if not isinstance(player, dict):
            continue
        model = player.get("model")
        if model:
            models.append(str(model))
        elif player.get("model_env"):
            models.append(f"${player['model_env']}")
    return models


def list_config_files(configs_dir: Path) -> list[Path]:
    if not configs_dir.is_dir():
        return []
    return sorted(configs_dir.glob("*.yaml"))


def parse_config_brief(path: Path) -> ModelConfigBrief | None:
    data = _safe_load_config(path)
    if data is None:
        return None
    models = _models_from_config(data)
    players = data.get("players") or []
    return ModelConfigBrief(
        config_id=path.stem,
        config_path=str(path.as_posix()),
        label=_label_from_path(path),
        provider=_infer_provider(path, models),
        player_count=len(players) if isinstance(players, list) else 0,
        models=models,
        agent_backend=str(data.get("agent_backend")) if data.get("agent_backend") else None,
        language=str(data.get("language")) if data.get("language") else None,
    )


def list_models_page(configs_dir: Path) -> ModelListPageData:
    configs: list[ModelConfigBrief] = []
    for path in list_config_files(configs_dir):
        brief = parse_config_brief(path)
        if brief is not None:
            configs.append(brief)
    usage = aggregate_model_usage()
    return ModelListPageData(title="AI 模型", configs=configs, usage_stats=usage)


def _normalize_model_id(raw: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9._$-]+", "_", raw.strip())
    return slug or "unknown"


def get_model_detail(model_id: str, configs_dir: Path) -> ModelDetailPageData:
    usage_map = {u.model_id: u for u in aggregate_model_usage()}
    matching_configs: list[ModelConfigBrief] = []
    display_name = model_id

    for path in list_config_files(configs_dir):
        brief = parse_config_brief(path)
        if brief is None:
            continue
        for model in brief.models:
            if _normalize_model_id(model) == model_id or model == model_id:
                matching_configs.append(brief)
                display_name = model
                break
        if brief.config_id == model_id:
            matching_configs.append(brief)
            display_name = brief.label

    usage = usage_map.get(model_id)
    all_ids = list(usage_map.keys())
    compare_with = [mid for mid in all_ids if mid != model_id][:5]

    return ModelDetailPageData(
        model_id=model_id,
        display_name=display_name,
        configs=matching_configs,
        usage=usage,
        compare_with=compare_with,
        notes=[
            "模型 ID 来自配置文件或历史对局 roster 中的 ai_model 字段。",
            "密钥与 endpoint 通过环境变量注入，API 不会返回任何 secret。",
        ],
    )


def compare_models(model_ids: list[str]) -> ModelComparePageData:
    usage_map = {u.model_id: u for u in aggregate_model_usage()}
    items: list[ModelCompareItem] = []
    for mid in model_ids:
        stat = usage_map.get(mid)
        if stat is None:
            items.append(ModelCompareItem(model_id=mid, display_name=mid, run_count=0))
        else:
            items.append(
                ModelCompareItem(
                    model_id=stat.model_id,
                    display_name=stat.display_name,
                    run_count=stat.run_count,
                    win_rate=stat.win_rate,
                    avg_mvp=stat.avg_mvp,
                )
            )
    return ModelComparePageData(
        models=items,
        metric_labels={
            "run_count": "参与局数",
            "win_rate": "胜率（粗略）",
            "avg_mvp": "平均 MVP 分",
        },
    )
