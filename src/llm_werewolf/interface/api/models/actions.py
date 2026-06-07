"""Write-action request/response schemas for frontend POST APIs."""

from __future__ import annotations

from pydantic import Field, BaseModel, field_validator, model_validator

from llm_werewolf.game_runtime.roles.registry import validate_role_names

# Runtime import required (not TYPE_CHECKING): GameStatusResponse and
# ModelCompareResponse use these as pydantic field types; with
# `from __future__ import annotations` they must be resolvable at model-build
# time or instantiation raises PydanticUserError ("not fully defined").
from llm_werewolf.interface.api.models.pages import GameSnapshot, ModelComparePageData


class PlayerRosterDefaults(BaseModel):
    provider: str | None = Field(
        default=None,
        description="Registry provider_id (e.g. doubao, deepseek); resolves base_url/api_key_env/model_env",
    )
    model: str | None = Field(default=None, description="Default model for all non-human seats")
    base_url: str | None = Field(default=None, description="Default API base URL")
    api_key_env: str | None = Field(default=None, description="Env var name for API key")
    model_env: str | None = Field(default=None, description="Env var name for model/endpoint id")
    plan: str | None = Field(default=None, description="AgentScope plan strategy name")


class PlayerRosterSlot(BaseModel):
    provider: str | None = Field(
        default=None,
        description="Registry provider_id for this seat; resolves connection fields from env",
    )
    name: str | None = Field(default=None, description="Seat display name")
    model: str | None = Field(default=None, description="Model name (clears model_env when set)")
    base_url: str | None = Field(default=None, description="API base URL for this seat")
    api_key_env: str | None = Field(default=None, description="Env var name for API key")
    model_env: str | None = Field(default=None, description="Env var name for model/endpoint id")
    plan: str | None = Field(default=None, description="AgentScope plan strategy name")


class HumanSeatSpec(BaseModel):
    seat: int = Field(..., ge=1, le=20, description="1-based seat for the single human player")
    role: str | None = Field(
        default=None,
        description=(
            "Optional fixed role for the human seat (zh display name like '狼人' or English "
            "key like 'Werewolf'); honored via a post-deal role swap when present in the lineup"
        ),
    )


class StartGameRequest(BaseModel):
    config_id: str | None = Field(default=None, description="YAML stem under configs/")
    config_path: str | None = Field(default=None, description="Explicit config path")
    participation: str | None = Field(
        default=None,
        description="Mode participation, e.g. all_agent (used with rules when config_id omitted)",
    )
    rules: str | None = Field(
        default=None,
        description="Mode rules: basic | badge_flow | extended_roles",
    )
    run_label: str | None = Field(default=None, description="Optional run directory prefix")
    player_count: int | None = Field(
        default=None,
        ge=4,
        le=20,
        description="Optional seat count override (4-20); prefer standard-{N}p config_id",
    )
    human_seats: list[int] | None = Field(
        default=None,
        description=(
            "1-based seat numbers for CLI stdin humans (model=human). "
            "For browser play use ``human`` instead."
        ),
    )
    badge_flow: bool | None = Field(
        default=None,
        description="Enable sheriff election after first night (CLI --badge_flow)",
    )
    defaults: PlayerRosterDefaults | None = Field(
        default=None,
        description="Defaults applied to every non-human seat before per-seat overrides",
    )
    players: list[PlayerRosterSlot] | None = Field(
        default=None,
        description="Per-seat overrides by index (sparse list allowed)",
    )
    human: HumanSeatSpec | None = Field(
        default=None,
        description="Single human seat for human-vs-AI; None = pure-LLM spectate",
    )
    track_vote_intentions: bool | None = Field(
        default=None,
        description=(
            "Enable belief matrix + vote-intention collection (Insight dock). "
            "None = use YAML default (usually true)."
        ),
    )
    role_names: list[str] | None = Field(
        default=None,
        description=(
            "Optional fixed role lineup (catalog keys). Overrides auto-deal; "
            "player_count is inferred from length when omitted."
        ),
    )

    @field_validator("role_names")
    @classmethod
    def validate_custom_role_names(cls, v: list[str] | None) -> list[str] | None:
        if v is None:
            return None
        validate_role_names(v)
        return v

    @model_validator(mode="after")
    def align_role_names_and_player_count(self) -> StartGameRequest:
        if self.role_names is None:
            return self
        n = len(self.role_names)
        if self.player_count is None:
            self.player_count = n
        elif self.player_count != n:
            msg = (
                f"role_names length ({n}) must match player_count ({self.player_count})"
            )
            raise ValueError(msg)
        return self

    @field_validator("human_seats")
    @classmethod
    def validate_human_seats(cls, seats: list[int] | None) -> list[int] | None:
        if seats is None:
            return None
        cleaned = sorted(set(seats))
        for seat in cleaned:
            if seat < 1 or seat > 20:
                msg = f"human_seats values must be between 1 and 20, got {seat}"
                raise ValueError(msg)
        return cleaned


class StartGameModeOption(BaseModel):
    participation: str
    rules: str
    config_id: str
    description: str
    player_count: int | None = None


class StartGameModesResponse(BaseModel):
    modes: list[StartGameModeOption]
    default_participation: str = "all_agent"
    default_rules: str = "basic"


class PlayableRoleOption(BaseModel):
    key: str
    display_name: str
    camp: str
    camp_label: str = ""


class BoardPresetOption(BaseModel):
    preset_id: str
    kind: str = Field(description="standard | curated | custom")
    title: str
    description: str = ""
    tags: list[str] = Field(default_factory=list)
    player_count: int
    role_names: list[str]
    role_labels: list[str] = Field(default_factory=list)
    werewolf_count: int = 0
    villager_count: int = 0
    neutral_count: int = 0


class BoardPresetsResponse(BaseModel):
    roles: list[PlayableRoleOption] = Field(default_factory=list)
    presets: list[BoardPresetOption] = Field(default_factory=list)
    default_preset_id: str = ""


class StartGameResponse(BaseModel):
    run_id: str
    source: str = "runs"
    status: str
    config_id: str
    run_dir: str
    game_page_path: str
    status_path: str
    replay_page_path: str
    participation: str | None = None
    rules: str | None = None
    player_count: int | None = None
    human_seats: list[int] = Field(default_factory=list)
    badge_flow: bool = False
    custom_roster: bool = False
    player_token: str | None = None
    stream_path: str | None = None


class HumanInputRequest(BaseModel):
    token: str = Field(..., description="Per-seat token from StartGameResponse.player_token")
    request_id: str = Field(..., description="awaiting_input request id the browser is answering")
    kind: str = Field(..., description="Decision kind: seat|multi|yesno|witch|speech")
    payload: str = Field(..., description="Normalized decision text (bridge contract)")


class HumanInputResponse(BaseModel):
    run_id: str
    accepted: bool
    message: str | None = None


class GameStatusResponse(BaseModel):
    run_id: str
    source: str = "runs"
    status: str
    snapshot: GameSnapshot | None = None
    error: str | None = None
    result_text: str | None = None
    has_post_game: bool = False
    has_replay: bool = False
    post_game_status: str | None = None
    alert_count: int | None = None


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
