# 纯 LLM 观战模式 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 把现有 React 前端改成纯 LLM 对战观战界面（发言走对话框、技能/投票内嵌事件、可展示 AI 内心推理、逐座位 LLM 配置），后端用 Python 引擎跑、前端只调 `/api/v1`。

**Architecture:** 方案B——Python 引擎后台跑整局并把事件落 `events.jsonl`；新增 `/api/v1/games/{run_id}/view?since=N` 投影接口返回"渲染就绪快照 + 增量事件"；前端增量轮询、玩家表吃快照、对话/技能/内心OS 进本地队列由前端节奏机按 暂停/变速 吐出。逐座位 provider/model/key 由前端 localStorage 存、开局随 body 传、后端仅会话内存用不落盘。

**Tech Stack:** 后端 FastAPI + Pydantic + pytest；前端 React 19 + TypeScript + Zustand + Vite。

参照设计 spec：`docs/superpowers/specs/2026-06-03-pure-llm-frontend-design.md`。

---

## 里程碑总览

- **A. 后端配置 & Key 注入**（A1–A4）：让前端逐座位 model/key/temperature 进引擎，且 key 不落盘。
- **B. 后端事件补字段**（B1）：发言事件带 `private_thought`。
- **C. 后端 roster + 投影接口**（C1–C4）：游戏开始持久化全量 roster；新增 `/view` 投影。
- **D. 前端数据层**（D1–D3）：types / api-keys / store(轮询+队列+节奏机)。
- **E. 前端组件**（E1–E6）：GameSetup 逐座位配置 / SpeechConsole / ControlPanel / CardDeck / App 接线 / Vite 代理。

约定：每个后端任务跑 `cd D:/AI_werewolf/Frontend_6_3/MultiAgent-Werewolf && uv run pytest <path> -v`。每个前端任务跑 `cd D:/AI_werewolf/Frontend_6_3/MultiAgent-Werewolf/frontend && npm run lint`（= `tsc --noEmit`）。每个任务末尾 commit。

---

## Milestone A — 后端配置 & Key 注入

### Task A1: PlayerConfig 增加字面量 `api_key` 与 `temperature`

**Files:**
- Modify: `src/llm_werewolf/game_runtime/config/player_config.py:77-89`（`PlayerConfig` 字段区）
- Test: `tests/config/test_game_config.py`

- [ ] **Step 1: 写失败测试**

在 `tests/config/test_game_config.py` 末尾追加：

```python
def test_player_config_accepts_literal_api_key_and_temperature():
    from llm_werewolf.game_runtime.config.player_config import PlayerConfig

    cfg = PlayerConfig(
        name="P1",
        model="deepseek-chat",
        base_url="https://api.deepseek.com/v1",
        api_key="sk-literal-123",
        temperature=1.1,
    )
    assert cfg.api_key == "sk-literal-123"
    assert cfg.temperature == 1.1
    # api_key_env 仍可单独使用，互不影响
    cfg2 = PlayerConfig(name="P2", model="demo")
    assert cfg2.api_key is None
    assert cfg2.temperature is None
```

- [ ] **Step 2: 运行验证失败**

Run: `uv run pytest tests/config/test_game_config.py::test_player_config_accepts_literal_api_key_and_temperature -v`
Expected: FAIL（`PlayerConfig` 无 `api_key` / `temperature` 字段，`ValidationError` 或 `TypeError`）

- [ ] **Step 3: 实现**

在 `player_config.py` 的 `PlayerConfig` 中，于 `api_key_env` 字段（第 77-82 行）之后、`reasoning_effort` 之前插入：

```python
    api_key: str | None = Field(
        default=None,
        title="Literal API Key",
        description=(
            "Literal API key (web/inline mode only). Takes precedence over "
            "api_key_env. Never written to disk by the engine."
        ),
    )
    temperature: float | None = Field(
        default=None,
        ge=0.0,
        le=2.0,
        title="Sampling Temperature",
        description="Optional per-seat sampling temperature; falls back to engine default.",
    )
```

- [ ] **Step 4: 运行验证通过**

Run: `uv run pytest tests/config/test_game_config.py::test_player_config_accepts_literal_api_key_and_temperature -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/llm_werewolf/game_runtime/config/player_config.py tests/config/test_game_config.py
git commit -m "feat(config): PlayerConfig 支持字面量 api_key 与 temperature"
```

---

### Task A2: factory 优先用字面量 key，并接上 temperature

**Files:**
- Modify: `src/llm_werewolf/agent_team/agents/factory.py:227-253`（`create_react_agent`）
- Test: `tests/agent_team/test_factory.py`

- [ ] **Step 1: 写失败测试**

在 `tests/agent_team/test_factory.py` 末尾追加：

```python
def test_create_react_agent_prefers_literal_api_key_and_sets_temperature(monkeypatch):
    import llm_werewolf.agent_team.agents.factory as factory_mod
    from llm_werewolf.game_runtime.config.player_config import PlayerConfig

    captured = {}

    class _FakeModel:
        def __init__(self, *args, **kwargs):
            captured.update(kwargs)

    monkeypatch.setattr(factory_mod, "OpenAIChatModel", _FakeModel)
    # 即使设置了 env，也应优先用字面量 api_key
    monkeypatch.setenv("SHOULD_NOT_BE_USED", "env-key")

    cfg = PlayerConfig(
        name="P1",
        model="deepseek-chat",
        base_url="https://api.deepseek.com/v1",
        api_key="sk-literal",
        api_key_env="SHOULD_NOT_BE_USED",
        temperature=0.4,
    )
    factory_mod.create_react_agent(cfg, agent_name="P1", sys_prompt="x")

    assert captured["api_key"] == "sk-literal"
    assert captured["generate_kwargs"]["temperature"] == 0.4
```

- [ ] **Step 2: 运行验证失败**

Run: `uv run pytest tests/agent_team/test_factory.py::test_create_react_agent_prefers_literal_api_key_and_sets_temperature -v`
Expected: FAIL（当前 `api_key` 只来自 env；`generate_kwargs` 无 `temperature`）

- [ ] **Step 3: 实现**

在 `factory.py` `create_react_agent` 中，替换第 229-237 行的 key 解析块：

```python
    api_key = config.api_key or (
        os.getenv(config.api_key_env) if config.api_key_env else None
    )
    if not api_key:
        msg = (
            f"API key not found: set literal api_key or env var "
            f"'{config.api_key_env}' for player '{config.name}'"
        )
        raise ValueError(msg)
```

并在第 243-245 行 `generate_kwargs` 块后追加 temperature：

```python
    generate_kwargs: dict[str, Any] = {"max_tokens": 2048}
    if config.reasoning_effort:
        generate_kwargs["reasoning_effort"] = config.reasoning_effort
    if config.temperature is not None:
        generate_kwargs["temperature"] = config.temperature
```

- [ ] **Step 4: 运行验证通过**

Run: `uv run pytest tests/agent_team/test_factory.py::test_create_react_agent_prefers_literal_api_key_and_sets_temperature -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/llm_werewolf/agent_team/agents/factory.py tests/agent_team/test_factory.py
git commit -m "feat(agent): factory 优先用字面量 api_key 并接上 per-seat temperature"
```

---

### Task A3: 开局请求逐座位支持 api_key/temperature

**Files:**
- Modify: `src/llm_werewolf/interface/api/models/actions.py:10-25`（`PlayerRosterDefaults` / `PlayerRosterSlot`）
- Modify: `src/llm_werewolf/interface/api/services/roster_customize.py:10`（`_ROSTER_FIELDS`）
- Test: `tests/interface/test_roster_customize.py`

- [ ] **Step 1: 写失败测试**

在 `tests/interface/test_roster_customize.py` 末尾追加：

```python
def test_roster_slot_applies_api_key_and_temperature():
    from llm_werewolf.game_runtime.config.player_config import PlayerConfig, PlayersConfig
    from llm_werewolf.interface.api.models.actions import PlayerRosterSlot
    from llm_werewolf.interface.api.services.roster_customize import apply_roster_customizations

    base = PlayersConfig(
        language="zh-CN",
        players=[
            PlayerConfig(name=f"P{i}", model="demo") for i in range(1, 7)
        ],
    )
    slots = [
        PlayerRosterSlot(
            model="deepseek-chat",
            base_url="https://api.deepseek.com/v1",
            api_key="sk-seat1",
            temperature=1.1,
        )
    ] + [PlayerRosterSlot() for _ in range(5)]

    result = apply_roster_customizations(base, players=slots)
    assert result.players[0].api_key == "sk-seat1"
    assert result.players[0].temperature == 1.1
    assert result.players[0].model == "deepseek-chat"
```

- [ ] **Step 2: 运行验证失败**

Run: `uv run pytest tests/interface/test_roster_customize.py::test_roster_slot_applies_api_key_and_temperature -v`
Expected: FAIL（`PlayerRosterSlot` 无 `api_key`/`temperature`，且 `_ROSTER_FIELDS` 未覆盖）

- [ ] **Step 3: 实现**

(a) 在 `actions.py` 的 `PlayerRosterDefaults`（第 10-15 行）和 `PlayerRosterSlot`（第 18-24 行）各追加两个字段：

```python
    api_key: str | None = Field(default=None, description="Literal API key (inline mode; not persisted)")
    temperature: float | None = Field(default=None, ge=0.0, le=2.0, description="Per-seat sampling temperature")
```

(b) 在 `roster_customize.py` 第 10 行扩展 `_ROSTER_FIELDS`：

```python
_ROSTER_FIELDS = ("name", "model", "base_url", "api_key_env", "model_env", "plan", "api_key", "temperature")
```

- [ ] **Step 4: 运行验证通过**

Run: `uv run pytest tests/interface/test_roster_customize.py::test_roster_slot_applies_api_key_and_temperature -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/llm_werewolf/interface/api/models/actions.py src/llm_werewolf/interface/api/services/roster_customize.py tests/interface/test_roster_customize.py
git commit -m "feat(api): 开局请求逐座位支持 api_key 与 temperature"
```

---

### Task A4: launch_roster.json 落盘前抹掉 api_key（安全）

**Files:**
- Modify: `src/llm_werewolf/interface/api/services/game_sessions.py:146-154`
- Test: `tests/interface/test_api_services.py`

- [ ] **Step 1: 写失败测试**

在 `tests/interface/test_api_services.py` 末尾追加：

```python
def test_launch_roster_never_persists_api_key(tmp_path):
    import json
    from llm_werewolf.game_runtime.config.player_config import PlayerConfig, PlayersConfig
    from llm_werewolf.interface.api.services.game_sessions import _dump_roster_without_secrets

    cfg = PlayersConfig(
        language="zh-CN",
        players=[
            PlayerConfig(name="P1", model="deepseek-chat",
                         base_url="https://api.deepseek.com/v1", api_key="sk-secret"),
            *[PlayerConfig(name=f"P{i}", model="demo") for i in range(2, 7)],
        ],
    )
    dumped = _dump_roster_without_secrets(cfg)
    text = json.dumps(dumped, ensure_ascii=False)
    assert "sk-secret" not in text
    assert all("api_key" not in p for p in dumped["players"])
```

- [ ] **Step 2: 运行验证失败**

Run: `uv run pytest tests/interface/test_api_services.py::test_launch_roster_never_persists_api_key -v`
Expected: FAIL（`_dump_roster_without_secrets` 不存在）

- [ ] **Step 3: 实现**

(a) 在 `game_sessions.py` 顶部函数区（`_has_human_player` 之后）新增：

```python
def _dump_roster_without_secrets(players_config: PlayersConfig) -> dict:
    """Serialize roster for disk, stripping per-seat literal api_key."""
    data = players_config.model_dump(mode="json", exclude={"use_agentscope_backend"})
    for player in data.get("players", []):
        player.pop("api_key", None)
    return data
```

(b) 替换第 146-154 行的 launch_roster 写盘块为：

```python
        if players_config is not None:
            (run_dir / "launch_roster.json").write_text(
                json.dumps(_dump_roster_without_secrets(players_config), ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
```

- [ ] **Step 4: 运行验证通过**

Run: `uv run pytest tests/interface/test_api_services.py::test_launch_roster_never_persists_api_key -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/llm_werewolf/interface/api/services/game_sessions.py tests/interface/test_api_services.py
git commit -m "fix(api): launch_roster 落盘前抹掉字面量 api_key"
```

---

## Milestone B — 后端事件补字段

### Task B1: 发言事件携带 private_thought

**Files:**
- Modify: `src/llm_werewolf/game_runtime/engine/day_phase.py:71-84`（`_log_public_speech`）
- Test: `tests/game_runtime/test_event_formatter.py`（新增独立用例，无需整局）

- [ ] **Step 1: 写失败测试**

新建 `tests/game_runtime/test_speech_event_private_thought.py`：

```python
def test_log_public_speech_includes_private_thought():
    from types import SimpleNamespace
    from llm_werewolf.game_runtime.engine.day_phase import DayPhaseMixin
    from llm_werewolf.strategy.decisions import SpeechDecision

    captured = {}

    class _Engine(DayPhaseMixin):
        def __init__(self):
            self.game_state = object()  # truthy
            self.locale = SimpleNamespace(get=lambda *a, **k: "msg")

        def _log_event(self, event_type, message, data=None, visible_to=None):
            captured["data"] = data

    speaker = SimpleNamespace(player_id="player_3", name="P3")
    decision = SpeechDecision.model_construct(public_speech="我怀疑5号", private_thought="其实更怕3号")
    _Engine()._log_public_speech(speaker, decision)

    assert captured["data"]["speech"] == "我怀疑5号"
    assert captured["data"]["private_thought"] == "其实更怕3号"
```

- [ ] **Step 2: 运行验证失败**

Run: `uv run pytest tests/game_runtime/test_speech_event_private_thought.py -v`
Expected: FAIL（KeyError: 'private_thought'）

- [ ] **Step 3: 实现**

在 `day_phase.py` `_log_public_speech` 的 `data` 字典（第 78-82 行）加入 private_thought：

```python
            data={
                "player_id": speaker.player_id,
                "player_name": speaker.name,
                "speech": decision.public_speech,
                "private_thought": decision.private_thought,
            },
```

- [ ] **Step 4: 运行验证通过**

Run: `uv run pytest tests/game_runtime/test_speech_event_private_thought.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/llm_werewolf/game_runtime/engine/day_phase.py tests/game_runtime/test_speech_event_private_thought.py
git commit -m "feat(engine): 发言事件携带 private_thought 供上帝视角展示"
```

---

## Milestone C — 后端 roster + 投影接口

### Task C1: 游戏开始持久化全量 roster.json

**Files:**
- Modify: `src/llm_werewolf/interface/api/services/game_sessions.py:207-208`（`_run_game` 内 setup 之后）
- Test: `tests/interface/test_api_services.py`

- [ ] **Step 1: 写失败测试**

在 `tests/interface/test_api_services.py` 末尾追加：

```python
def test_write_full_roster_json(tmp_path):
    import json
    from types import SimpleNamespace
    from llm_werewolf.interface.api.services.game_sessions import _write_full_roster

    players = [
        SimpleNamespace(player_id="player_1", name="P1", ai_model="deepseek-chat",
                        get_role_name=lambda: "预言家",
                        role=SimpleNamespace(camp=SimpleNamespace(value="villager"))),
        SimpleNamespace(player_id="player_2", name="P2", ai_model="doubao",
                        get_role_name=lambda: "狼人",
                        role=SimpleNamespace(camp=SimpleNamespace(value="werewolf"))),
    ]
    engine = SimpleNamespace(game_state=SimpleNamespace(players=players))
    _write_full_roster(engine, tmp_path)

    data = json.loads((tmp_path / "roster.json").read_text(encoding="utf-8"))
    assert data["players"][0] == {
        "seat": 1, "player_id": "player_1", "name": "P1",
        "role": "预言家", "camp": "villager", "model": "deepseek-chat",
    }
    assert data["players"][1]["role"] == "狼人"
```

- [ ] **Step 2: 运行验证失败**

Run: `uv run pytest tests/interface/test_api_services.py::test_write_full_roster_json -v`
Expected: FAIL（`_write_full_roster` 不存在）

- [ ] **Step 3: 实现**

(a) 在 `game_sessions.py` 函数区新增：

```python
def _write_full_roster(engine: Any, run_dir: Path) -> None:
    """Persist god-view roster (seat -> role/camp/model) at game start for /view."""
    state = getattr(engine, "game_state", None)
    if state is None:
        return
    players = []
    for player in state.players:
        camp = None
        role = getattr(player, "role", None)
        if role is not None and getattr(role, "camp", None) is not None:
            camp = role.camp.value
        seat = int(player.player_id.rsplit("_", 1)[-1])
        players.append({
            "seat": seat,
            "player_id": player.player_id,
            "name": player.name,
            "role": player.get_role_name(),
            "camp": camp,
            "model": getattr(player, "ai_model", "unknown"),
        })
    players.sort(key=lambda p: p["seat"])
    (run_dir / "roster.json").write_text(
        json.dumps({"players": players}, ensure_ascii=False, indent=2), encoding="utf-8"
    )
```

(b) 在 `_run_game` 中，第 207 行 `engine.setup_game(...)` 之后、`wire_agentscope_after_setup` 之前插入：

```python
            _write_full_roster(engine, session.run_dir)
```

- [ ] **Step 4: 运行验证通过**

Run: `uv run pytest tests/interface/test_api_services.py::test_write_full_roster_json -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/llm_werewolf/interface/api/services/game_sessions.py tests/interface/test_api_services.py
git commit -m "feat(api): 游戏开始持久化全量 roster.json 供上帝视角观战"
```

---

### Task C2: ViewResponse 投影响应模型

**Files:**
- Create: `src/llm_werewolf/interface/api/models/view.py`
- Test: `tests/interface/test_view_models.py`

- [ ] **Step 1: 写失败测试**

新建 `tests/interface/test_view_models.py`：

```python
def test_view_response_roundtrip():
    from llm_werewolf.interface.api.models.view import (
        ViewResponse, ViewSnapshot, ViewPlayer, ViewEvent,
    )

    resp = ViewResponse(
        cursor=2,
        status="running",
        snapshot=ViewSnapshot(
            day=1, phase="day_discussion", phase_label="第1天 · 讨论",
            winner=None, alive_count=6, dead_count=0, sheriff_seat=None,
            players=[ViewPlayer(seat=1, name="P1", role="预言家", camp="villager",
                                is_alive=True, is_sheriff=False, model="deepseek-chat")],
        ),
        events=[ViewEvent(seq=1, type="speech", day=1, phase="day_discussion",
                          text="我怀疑5号", reveal="now", visibility="public")],
    )
    dumped = resp.model_dump()
    assert dumped["cursor"] == 2
    assert dumped["snapshot"]["players"][0]["role"] == "预言家"
    assert dumped["events"][0]["type"] == "speech"
```

- [ ] **Step 2: 运行验证失败**

Run: `uv run pytest tests/interface/test_view_models.py -v`
Expected: FAIL（模块不存在）

- [ ] **Step 3: 实现**

新建 `src/llm_werewolf/interface/api/models/view.py`：

```python
"""Render-ready projection models for the pure-LLM spectate frontend."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

RevealMode = Literal["now", "on_death", "on_game_end"]
Visibility = Literal["public", "wolf", "god"]
ViewEventType = Literal[
    "speech", "skill", "vote", "death", "phase", "system", "belief", "vote_intention"
]


class ViewPlayer(BaseModel):
    seat: int
    name: str
    role: str | None = None          # god-view truth; frontend masks per reveal
    camp: str | None = None
    is_alive: bool = True
    is_sheriff: bool = False
    model: str | None = None
    provider: str | None = None
    death: dict[str, Any] | None = None  # {day, phase, cause, reveal}


class ViewSnapshot(BaseModel):
    day: int = 0
    phase: str = "setup"
    phase_label: str = ""
    winner: str | None = None
    alive_count: int = 0
    dead_count: int = 0
    sheriff_seat: int | None = None
    players: list[ViewPlayer] = Field(default_factory=list)
    vote_tally: dict[str, Any] | None = None


class ViewEvent(BaseModel):
    seq: int
    type: ViewEventType
    day: int = 0
    phase: str = ""
    text: str = ""
    speaker: dict[str, Any] | None = None
    public_text: str | None = None
    private_thought: str | None = None
    skill: dict[str, Any] | None = None
    vote: dict[str, Any] | None = None
    death: dict[str, Any] | None = None
    reveal: RevealMode = "now"
    visibility: Visibility = "public"


class ViewResponse(BaseModel):
    cursor: int
    status: str                       # running | ended | cancelled | error
    error: str | None = None
    snapshot: ViewSnapshot
    events: list[ViewEvent] = Field(default_factory=list)
```

- [ ] **Step 4: 运行验证通过**

Run: `uv run pytest tests/interface/test_view_models.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/llm_werewolf/interface/api/models/view.py tests/interface/test_view_models.py
git commit -m "feat(api): 新增 ViewResponse 投影响应模型"
```

---

### Task C3: 投影服务 view.py（事件映射 + 快照）

**Files:**
- Create: `src/llm_werewolf/interface/api/services/view.py`
- Test: `tests/interface/test_view_service.py`

- [ ] **Step 1: 写失败测试**

新建 `tests/interface/test_view_service.py`：

```python
import json
from pathlib import Path

from llm_werewolf.interface.api.services.view import build_view


def _seed_run(tmp_path: Path) -> Path:
    run_dir = tmp_path / "run1"
    run_dir.mkdir()
    (run_dir / "roster.json").write_text(json.dumps({"players": [
        {"seat": 1, "player_id": "player_1", "name": "P1", "role": "预言家", "camp": "villager", "model": "deepseek-chat"},
        {"seat": 2, "player_id": "player_2", "name": "P2", "role": "狼人", "camp": "werewolf", "model": "doubao"},
    ]}), encoding="utf-8")
    rows = [
        {"event_type": "phase_changed", "round_number": 1, "phase": "day_discussion", "message": "第1天 讨论", "data": {"phase": "day_discussion", "round": 1}},
        {"event_type": "player_speech", "round_number": 1, "phase": "day_discussion", "message": "P1: 我怀疑2号",
         "data": {"player_id": "player_1", "player_name": "P1", "speech": "我怀疑2号", "private_thought": "其实2号像狼"}},
        {"event_type": "seer_checked", "round_number": 1, "phase": "night", "message": "预言家查验2号→查杀",
         "data": {"player_id": "player_1", "target_id": "player_2", "result": "werewolf"}},
        {"event_type": "player_eliminated", "round_number": 1, "phase": "day_voting", "message": "2号被放逐",
         "data": {"player_id": "player_2", "player_name": "P2"}},
    ]
    (run_dir / "events.jsonl").write_text(
        "\n".join(json.dumps(r, ensure_ascii=False) for r in rows) + "\n", encoding="utf-8"
    )
    return run_dir


def test_build_view_cursor_and_event_mapping(tmp_path):
    run_dir = _seed_run(tmp_path)
    view = build_view(run_dir, since=0, status="running")
    assert view.cursor == 4
    types = [e.type for e in view.events]
    assert types == ["phase", "speech", "skill", "vote_or_death"][: -1] + ["death"] or types == ["phase", "speech", "skill", "death"]
    speech = next(e for e in view.events if e.type == "speech")
    assert speech.private_thought == "其实2号像狼"
    skill = next(e for e in view.events if e.type == "skill")
    assert skill.visibility == "god"
    assert skill.reveal == "on_game_end"


def test_build_view_since_returns_only_new(tmp_path):
    run_dir = _seed_run(tmp_path)
    view = build_view(run_dir, since=3, status="running")
    assert view.cursor == 4
    assert len(view.events) == 1
    assert view.events[0].seq == 3  # 0-based index of 4th row


def test_build_view_snapshot_alive_and_role(tmp_path):
    run_dir = _seed_run(tmp_path)
    view = build_view(run_dir, since=0, status="running")
    snap = view.snapshot
    assert snap.alive_count == 1   # player_2 eliminated
    assert snap.dead_count == 1
    p2 = next(p for p in snap.players if p.seat == 2)
    assert p2.role == "狼人"
    assert p2.is_alive is False
```

- [ ] **Step 2: 运行验证失败**

Run: `uv run pytest tests/interface/test_view_service.py -v`
Expected: FAIL（模块不存在）

- [ ] **Step 3: 实现**

新建 `src/llm_werewolf/interface/api/services/view.py`：

```python
"""Project events.jsonl + roster.json into render-ready ViewResponse (方案B)."""

from __future__ import annotations

import json
from pathlib import Path

from llm_werewolf.interface.api.models.view import (
    ViewEvent, ViewPlayer, ViewResponse, ViewSnapshot,
)

# --- event_type -> UI classification ------------------------------------
_SPEECH_TYPES = {"player_speech", "player_discussion", "sheriff_candidate_speech"}
_DEATH_TYPES = {"player_died", "player_eliminated", "lover_died"}
_VOTE_TYPES = {"vote_cast", "vote_result", "sheriff_vote_cast"}
_SKILL_TYPES = {
    "werewolf_killed", "witch_saved", "witch_poisoned", "seer_checked",
    "guard_protected", "graveyard_keeper_check", "hunter_revenge",
    "sheriff_badge_transferred", "role_acting",
}
_PHASE_TYPES = {"phase_changed", "round_started"}
_NIGHT_PHASES = {"night", "setup"}

_PHASE_LABELS = {
    "setup": "准备", "night": "夜晚", "sheriff_election": "警长竞选",
    "day_discussion": "白天讨论", "day_voting": "放逐投票", "ended": "对局结束",
}

_SKILL_KIND = {
    "werewolf_killed": "wolf_kill", "witch_saved": "witch_save",
    "witch_poisoned": "witch_poison", "seer_checked": "seer_check",
    "guard_protected": "guard", "hunter_revenge": "hunter_shoot",
    "sheriff_badge_transferred": "badge_transfer",
}


def _seat_of(player_id: str | None) -> int | None:
    if not player_id:
        return None
    try:
        return int(str(player_id).rsplit("_", 1)[-1])
    except (ValueError, IndexError):
        return None


def _read_jsonl(path: Path) -> list[dict]:
    if not path.is_file():
        return []
    rows: list[dict] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(row, dict):
            rows.append(row)
    return rows


def _classify(event_type: str) -> str:
    if event_type in _SPEECH_TYPES:
        return "speech"
    if event_type in _DEATH_TYPES:
        return "death"
    if event_type in _VOTE_TYPES:
        return "vote"
    if event_type in _SKILL_TYPES:
        return "skill"
    if event_type in _PHASE_TYPES:
        return "phase"
    if event_type == "belief_snapshot":
        return "belief"
    if event_type == "vote_intention_snapshot":
        return "vote_intention"
    return "system"


def _reveal_visibility(event_type: str, phase: str) -> tuple[str, str]:
    ui = _classify(event_type)
    if ui in {"skill", "belief", "vote_intention"} or phase in _NIGHT_PHASES:
        if ui == "speech" or event_type in _VOTE_TYPES or ui == "death":
            return "now", "public"
        return "on_game_end", "god"
    return "now", "public"


def _map_event(seq: int, row: dict) -> ViewEvent:
    event_type = str(row.get("event_type", ""))
    phase = str(row.get("phase", ""))
    data = row.get("data") or {}
    ui = _classify(event_type)
    reveal, visibility = _reveal_visibility(event_type, phase)

    ev = ViewEvent(
        seq=seq, type=ui, day=int(row.get("round_number", 0)), phase=phase,
        text=str(row.get("message", "")), reveal=reveal, visibility=visibility,
    )
    if ui == "speech":
        ev.speaker = {"seat": _seat_of(data.get("player_id")), "name": data.get("player_name")}
        ev.public_text = data.get("speech")
        ev.private_thought = data.get("private_thought")
    elif ui == "skill":
        ev.skill = {
            "kind": _SKILL_KIND.get(event_type, event_type),
            "actor": {"seat": _seat_of(data.get("player_id"))},
            "target": {"seat": _seat_of(data.get("target_id"))},
            "result": data.get("result"),
        }
    elif ui == "vote":
        ev.vote = {
            "voter": {"seat": _seat_of(data.get("voter_id") or data.get("player_id"))},
            "target": {"seat": _seat_of(data.get("target_id"))},
        }
    elif ui == "death":
        ev.death = {"seat": _seat_of(data.get("player_id")), "name": data.get("player_name"),
                    "cause": data.get("cause")}
    return ev


def _build_snapshot(run_dir: Path, rows: list[dict], status: str) -> ViewSnapshot:
    roster_raw = {}
    roster_path = run_dir / "roster.json"
    if roster_path.is_file():
        try:
            roster_raw = json.loads(roster_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            roster_raw = {}
    roster = roster_raw.get("players", [])

    dead_ids: set[str] = set()
    sheriff_seat = None
    winner = None
    last_phase = "setup"
    last_round = 0
    for row in rows:
        etype = str(row.get("event_type", ""))
        data = row.get("data") or {}
        last_phase = str(row.get("phase", last_phase)) or last_phase
        last_round = int(row.get("round_number", last_round) or last_round)
        if etype in _DEATH_TYPES and data.get("player_id"):
            dead_ids.add(str(data["player_id"]))
        if etype == "sheriff_elected":
            sheriff_seat = _seat_of(data.get("player_id"))
        if etype == "game_ended":
            winner = data.get("winner_camp")

    players: list[ViewPlayer] = []
    for entry in roster:
        pid = entry.get("player_id", "")
        is_alive = pid not in dead_ids
        players.append(ViewPlayer(
            seat=int(entry.get("seat", 0)), name=entry.get("name", ""),
            role=entry.get("role"), camp=entry.get("camp"),
            is_alive=is_alive, is_sheriff=(_seat_of(pid) == sheriff_seat),
            model=entry.get("model"),
            death=None if is_alive else {"reveal": "now"},
        ))
    players.sort(key=lambda p: p.seat)

    return ViewSnapshot(
        day=last_round, phase=last_phase,
        phase_label=f"第{last_round}天 · {_PHASE_LABELS.get(last_phase, last_phase)}",
        winner=winner, alive_count=len(players) - len(dead_ids),
        dead_count=len(dead_ids), sheriff_seat=sheriff_seat, players=players,
    )


def build_view(run_dir: Path, *, since: int = 0, status: str = "running",
               error: str | None = None) -> ViewResponse:
    rows = _read_jsonl(run_dir / "events.jsonl")
    new_events = [_map_event(idx, row) for idx, row in enumerate(rows) if idx >= since]
    snapshot = _build_snapshot(run_dir, rows, status)
    return ViewResponse(cursor=len(rows), status=status, error=error,
                        snapshot=snapshot, events=new_events)
```

> 注：第一个测试里的 `types ==` 断言写得啰嗦，实际期望是 `["phase", "speech", "skill", "death"]`。若该断言因写法不稳定而失败，请把它改成：`assert types == ["phase", "speech", "skill", "death"]`。

- [ ] **Step 4: 运行验证通过**

先把测试里第一个断言改清楚：将 `test_build_view_cursor_and_event_mapping` 的 `assert types == ...` 那一行替换为 `assert types == ["phase", "speech", "skill", "death"]`。
Run: `uv run pytest tests/interface/test_view_service.py -v`
Expected: PASS（3 个用例全过）

- [ ] **Step 5: Commit**

```bash
git add src/llm_werewolf/interface/api/services/view.py tests/interface/test_view_service.py
git commit -m "feat(api): 新增 view 投影服务（事件映射 + 上帝视角快照）"
```

---

### Task C4: 暴露 GET /games/{run_id}/view

**Files:**
- Modify: `src/llm_werewolf/interface/api/services/game_sessions.py`（新增 `get_view` 方法）
- Modify: `src/llm_werewolf/interface/api/routes/actions.py`（新增路由）
- Test: `tests/interface/test_api_actions.py`

- [ ] **Step 1: 写失败测试**

在 `tests/interface/test_api_actions.py` 末尾追加（沿用该文件已有的 TestClient/app fixture；若 fixture 名不同，按文件现有用例的写法取用 client）：

```python
def test_view_endpoint_returns_projection(tmp_path, monkeypatch):
    import json
    from fastapi.testclient import TestClient
    from llm_werewolf.interface.api.app import create_app
    from llm_werewolf.interface.api import deps

    run_dir = tmp_path / "runs" / "demo-1"
    run_dir.mkdir(parents=True)
    (run_dir / "roster.json").write_text(json.dumps({"players": [
        {"seat": 1, "player_id": "player_1", "name": "P1", "role": "预言家", "camp": "villager", "model": "demo"},
    ]}), encoding="utf-8")
    (run_dir / "events.jsonl").write_text(
        json.dumps({"event_type": "player_speech", "round_number": 1, "phase": "day_discussion",
                    "message": "P1: hi", "data": {"player_id": "player_1", "player_name": "P1", "speech": "hi"}}) + "\n",
        encoding="utf-8")
    (run_dir / "run_meta.json").write_text(json.dumps({"status": "running"}), encoding="utf-8")

    app = create_app()
    app.dependency_overrides[deps.get_runs_dir] = lambda: tmp_path / "runs"
    client = TestClient(app)

    res = client.get("/api/v1/games/demo-1/view?since=0")
    assert res.status_code == 200
    body = res.json()["data"] if "data" in res.json() else res.json()
    assert body["cursor"] == 1
    assert body["events"][0]["type"] == "speech"
    assert body["snapshot"]["players"][0]["role"] == "预言家"
```

- [ ] **Step 2: 运行验证失败**

Run: `uv run pytest tests/interface/test_api_actions.py::test_view_endpoint_returns_projection -v`
Expected: FAIL（404，路由不存在）

- [ ] **Step 3: 实现**

(a) 在 `game_sessions.py` `GameSessionManager` 内（`get_status` 之后）新增：

```python
    def get_view(
        self, run_id: str, *, runs_dir: Path, eval_runs_dir: Path,
        since: int = 0, source: str | None = None,
    ) -> "ViewResponse | None":
        from llm_werewolf.interface.api.services.view import build_view

        session = self._sessions.get(run_id)
        if session is not None:
            run_dir = session.run_dir
            status_map = {
                GameSessionStatus.RUNNING: "running", GameSessionStatus.PENDING: "running",
                GameSessionStatus.COMPLETED: "ended", GameSessionStatus.CANCELLED: "cancelled",
                GameSessionStatus.FAILED: "error",
            }
            status = status_map.get(session.status, "running")
            error = session.error
        else:
            detail = get_run_detail(run_id, runs_dir, eval_runs_dir, source=source or "runs")
            if detail is None:
                return None
            run_dir = Path(detail.path)
            status, error = "ended", None
        if not run_dir.is_dir():
            return None
        return build_view(run_dir, since=since, status=status, error=error)
```

并在文件顶部 `if TYPE_CHECKING:` 区（或直接顶部 import 区）补：`from llm_werewolf.interface.api.models.view import ViewResponse`（放进一个 `from typing import TYPE_CHECKING` 守卫块，避免循环导入；若已有该守卫块则并入）。

(b) 在 `routes/actions.py` 的 `game_status` 路由之后新增：

```python
@router.get("/games/{run_id}/view")
def game_view(
    run_id: str,
    since: int = Query(0, ge=0),
    source: str | None = Query(None, pattern="^(runs|eval)$"),
    runs_dir=Depends(get_runs_dir),
    eval_runs_dir=Depends(get_eval_runs_dir),
) -> ApiResponse:
    data = game_session_manager.get_view(
        run_id, runs_dir=runs_dir, eval_runs_dir=eval_runs_dir, since=since, source=source,
    )
    if data is None:
        raise HTTPException(status_code=404, detail=f"Run not found: {run_id}")
    return ApiResponse(data=data)
```

(`ApiResponse` 已在该文件 import；`Query/Depends/HTTPException` 亦已 import。)

- [ ] **Step 4: 运行验证通过**

Run: `uv run pytest tests/interface/test_api_actions.py::test_view_endpoint_returns_projection -v`
Expected: PASS

- [ ] **Step 5: 回归 + Commit**

Run: `uv run pytest tests/interface tests/config tests/agent_team/test_factory.py tests/game_runtime/test_speech_event_private_thought.py -q`
Expected: 全绿

```bash
git add src/llm_werewolf/interface/api/services/game_sessions.py src/llm_werewolf/interface/api/routes/actions.py tests/interface/test_api_actions.py
git commit -m "feat(api): 暴露 GET /games/{run_id}/view 投影接口"
```

---

## Milestone D — 前端数据层

### Task D1: 新 types.ts（对齐 /view 契约）

**Files:**
- Modify: `frontend/src/types.ts`（整体替换）

- [ ] **Step 1: 整体替换 `frontend/src/types.ts`**

```typescript
// ===== /api/v1/games/{run_id}/view 的前端镜像类型 =====

export type ViewEventType =
  | "speech" | "skill" | "vote" | "death" | "phase" | "system" | "belief" | "vote_intention";
export type RevealMode = "now" | "on_death" | "on_game_end";
export type Visibility = "public" | "wolf" | "god";

export interface ViewPlayer {
  seat: number;
  name: string;
  role: string | null;
  camp: string | null;
  is_alive: boolean;
  is_sheriff: boolean;
  model: string | null;
  provider?: string | null;
  death?: { day?: number; phase?: string; cause?: string; reveal?: RevealMode } | null;
}

export interface ViewSnapshot {
  day: number;
  phase: string;
  phase_label: string;
  winner: string | null;
  alive_count: number;
  dead_count: number;
  sheriff_seat: number | null;
  players: ViewPlayer[];
  vote_tally?: { round?: number; counts?: Record<string, number>; result?: any } | null;
}

export interface ViewEvent {
  seq: number;
  type: ViewEventType;
  day: number;
  phase: string;
  text: string;
  speaker?: { seat: number | null; name?: string | null } | null;
  public_text?: string | null;
  private_thought?: string | null;
  skill?: { kind: string; actor?: { seat: number | null }; target?: { seat: number | null }; result?: any } | null;
  vote?: { voter?: { seat: number | null }; target?: { seat: number | null } } | null;
  death?: { seat: number | null; name?: string | null; cause?: string | null } | null;
  reveal: RevealMode;
  visibility: Visibility;
}

export interface ViewResponse {
  cursor: number;
  status: "running" | "ended" | "cancelled" | "error";
  error: string | null;
  snapshot: ViewSnapshot;
  events: ViewEvent[];
}

// ===== 逐座位 LLM 配置（开局用，参照 wolfcha ModelRef）=====

export interface SeatConfig {
  seat: number;
  name: string;
  provider: string;     // 仅前端分组；后端以 base_url 为准
  model: string;
  base_url: string;
  temperature?: number;
}

export interface ProviderPreset {
  id: string;
  label: string;
  base_url: string;
  models: string[];
}

// ===== 前端本地展示用的渲染日志条目 =====

export interface RenderLog {
  seq: number;
  kind: ViewEventType;
  day: number;
  speakerSeat: number | null;
  speakerName: string;
  text: string;            // 已揭示/遮挡处理后的展示文本
  privateThought?: string | null;
  visibility: Visibility;
}
```

- [ ] **Step 2: 类型检查**

Run: `cd frontend && npm run lint`
Expected: PASS（store/组件此刻仍引用旧类型会报错——这是预期的，后续任务修复；本步只确认 types.ts 本身语法正确，可暂时容忍依赖它的文件报错，下一任务即修 store）

> 若希望每步都全绿，可把 D1–D3 视作一个原子提交：先完成 D1、D2、D3 的文件后再统一 `npm run lint`。推荐按 D1→D2→D3 顺序写完再 lint。

- [ ] **Step 3: Commit**

```bash
git add frontend/src/types.ts
git commit -m "feat(fe): types 对齐 /view 契约与逐座位配置"
```

---

### Task D2: api-keys.ts（localStorage 管理，借鉴 wolfcha）

**Files:**
- Create: `frontend/src/lib/api-keys.ts`

- [ ] **Step 1: 新建 `frontend/src/lib/api-keys.ts`**

```typescript
import { ProviderPreset } from "../types";

// 项目自有 provider 预设（base_url 与 configs/*.yaml 对齐，可按需增减）
export const PROVIDER_PRESETS: ProviderPreset[] = [
  { id: "deepseek", label: "DeepSeek", base_url: "https://api.deepseek.com/v1",
    models: ["deepseek-chat", "deepseek-reasoner"] },
  { id: "doubao", label: "豆包 Doubao", base_url: "https://ark.cn-beijing.volces.com/api/v3",
    models: ["doubao-pro-32k", "doubao-lite-32k"] },
  { id: "siliconflow", label: "SiliconFlow", base_url: "https://api.siliconflow.cn/v1",
    models: ["Qwen/Qwen2.5-72B-Instruct", "deepseek-ai/DeepSeek-V3"] },
  { id: "openai", label: "OpenAI 兼容", base_url: "https://api.openai.com/v1",
    models: ["gpt-4o-mini", "gpt-4o"] },
];

const KEY_PREFIX = "werewolf.apikey.";

export function getApiKey(provider: string): string {
  try {
    return localStorage.getItem(KEY_PREFIX + provider) || "";
  } catch {
    return "";
  }
}

export function setApiKey(provider: string, key: string): void {
  try {
    if (key) localStorage.setItem(KEY_PREFIX + provider, key);
    else localStorage.removeItem(KEY_PREFIX + provider);
  } catch {
    /* ignore quota/private-mode errors */
  }
}

export function providerById(id: string): ProviderPreset | undefined {
  return PROVIDER_PRESETS.find((p) => p.id === id);
}
```

- [ ] **Step 2: Commit**

```bash
git add frontend/src/lib/api-keys.ts
git commit -m "feat(fe): localStorage 管理逐 provider API Key"
```

---

### Task D3: store.ts 重写（轮询 + 渲染队列 + 节奏机）

**Files:**
- Modify: `frontend/src/store.ts`（整体替换）

- [ ] **Step 1: 整体替换 `frontend/src/store.ts`**

```typescript
import { create } from "zustand";
import { ViewResponse, ViewSnapshot, ViewEvent, RenderLog, SeatConfig } from "./types";
import { getApiKey, providerById } from "./lib/api-keys";

const API = "/api/v1";
const POLL_MS = 1000;

type Speed = 1 | 2 | 999; // 999 = 瞬间
type RevealView = "god" | "suspense";

interface GameStore {
  runId: string | null;
  status: ViewResponse["status"] | "idle";
  snapshot: ViewSnapshot | null;
  logs: RenderLog[];
  cursor: number;
  queue: ViewEvent[];
  isPlaying: boolean;
  speed: Speed;
  revealView: RevealView;
  error: string | null;

  startGame: (seats: SeatConfig[], opts?: { language?: string; enableSheriff?: boolean }) => Promise<void>;
  cancelGame: () => Promise<void>;
  togglePlay: () => void;
  setSpeed: (s: Speed) => void;
  setRevealView: (v: RevealView) => void;
  exitToSetup: () => void;
  _poll: () => Promise<void>;
  _drain: () => void;
}

let pollTimer: ReturnType<typeof setInterval> | null = null;
let drainTimer: ReturnType<typeof setInterval> | null = null;

function unwrap<T>(json: any): T {
  return (json && typeof json === "object" && "data" in json ? json.data : json) as T;
}

// 是否对该事件做悬念遮挡（仅前端）
function shouldMask(ev: ViewEvent, view: RevealView): boolean {
  if (view === "god") return false;
  return ev.reveal !== "now"; // suspense: on_death / on_game_end 暂时遮挡
}

function toRenderLog(ev: ViewEvent, view: RevealView): RenderLog {
  const masked = shouldMask(ev, view);
  let text = ev.text;
  if (ev.type === "speech") {
    text = ev.public_text || ev.text;
  } else if (masked) {
    text = ev.type === "skill" ? "🌙 夜间有角色行动了…" : ev.text;
  }
  return {
    seq: ev.seq,
    kind: ev.type,
    day: ev.day,
    speakerSeat: ev.speaker?.seat ?? null,
    speakerName: ev.speaker?.name ?? "",
    text,
    privateThought: view === "god" ? ev.private_thought ?? null : null,
    visibility: ev.visibility,
  };
}

export const useGameStore = create<GameStore>((set, get) => ({
  runId: null,
  status: "idle",
  snapshot: null,
  logs: [],
  cursor: 0,
  queue: [],
  isPlaying: true,
  speed: 1,
  revealView: "god",
  error: null,

  startGame: async (seats, opts) => {
    set({ status: "running", logs: [], cursor: 0, queue: [], snapshot: null, error: null, isPlaying: true });
    const players = seats.map((s) => ({
      name: s.name,
      model: s.model,
      base_url: s.base_url || providerById(s.provider)?.base_url,
      api_key: getApiKey(s.provider),
      temperature: s.temperature,
    }));
    try {
      const res = await fetch(`${API}/games/start`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          participation: "all_agent",
          rules: opts?.enableSheriff ? "badge_flow" : "basic",
          player_count: seats.length,
          badge_flow: !!opts?.enableSheriff,
          players,
        }),
      });
      const data = unwrap<{ run_id: string }>(await res.json());
      set({ runId: data.run_id });
      if (pollTimer) clearInterval(pollTimer);
      if (drainTimer) clearInterval(drainTimer);
      pollTimer = setInterval(() => get()._poll(), POLL_MS);
      drainTimer = setInterval(() => get()._drain(), 220);
      get()._poll();
    } catch (err) {
      console.error("startGame failed", err);
      set({ status: "error", error: String(err) });
    }
  },

  _poll: async () => {
    const { runId, cursor } = get();
    if (!runId) return;
    try {
      const res = await fetch(`${API}/games/${runId}/view?since=${cursor}`);
      if (!res.ok) return;
      const view = unwrap<ViewResponse>(await res.json());
      set((st) => ({
        snapshot: view.snapshot,
        cursor: view.cursor,
        status: view.status,
        error: view.error,
        queue: [...st.queue, ...view.events],
      }));
      if (view.status === "ended" || view.status === "cancelled" || view.status === "error") {
        if (pollTimer) { clearInterval(pollTimer); pollTimer = null; }
      }
    } catch (err) {
      console.error("poll failed", err);
    }
  },

  _drain: () => {
    const { isPlaying, queue, speed, revealView } = get();
    if (!isPlaying || queue.length === 0) return;
    const take = speed === 999 ? queue.length : speed;
    const batch = queue.slice(0, take);
    const rest = queue.slice(take);
    set((st) => ({
      queue: rest,
      logs: [...st.logs, ...batch.map((ev) => toRenderLog(ev, revealView))],
    }));
  },

  cancelGame: async () => {
    const { runId } = get();
    if (runId) {
      try { await fetch(`${API}/games/${runId}/cancel`, { method: "POST" }); } catch { /* ignore */ }
    }
    if (pollTimer) { clearInterval(pollTimer); pollTimer = null; }
    set({ status: "cancelled", isPlaying: false });
  },

  togglePlay: () => set((st) => ({ isPlaying: !st.isPlaying })),
  setSpeed: (s) => set({ speed: s }),
  setRevealView: (v) => set({ revealView: v }),

  exitToSetup: () => {
    if (pollTimer) { clearInterval(pollTimer); pollTimer = null; }
    if (drainTimer) { clearInterval(drainTimer); drainTimer = null; }
    set({ runId: null, status: "idle", snapshot: null, logs: [], cursor: 0, queue: [], error: null });
  },
}));
```

- [ ] **Step 2: 类型检查**

Run: `cd frontend && npm run lint`
Expected: store.ts 本身无错（依赖它的旧组件仍会报错，E1–E5 修复）。

- [ ] **Step 3: Commit**

```bash
git add frontend/src/store.ts
git commit -m "feat(fe): store 重写为轮询 + 渲染队列 + 播放节奏机"
```

---

## Milestone E — 前端组件

### Task E1: GameSetup 逐座位 LLM 配置

**Files:**
- Modify: `frontend/src/components/GameSetup.tsx`

- [ ] **Step 1: 替换 import 与状态**

把第 1-4 行 import 与第 6-30 行的组件头改为（保留文件后续的 UI 外壳；删掉 role/gameMode 相关、改 startMatch）：

```tsx
import React, { useState, useEffect } from "react";
import { useGameStore } from "../store";
import { motion, AnimatePresence } from "motion/react";
import { Cpu, ChevronLeft, Flame, Play } from "lucide-react";
import { PROVIDER_PRESETS, getApiKey, setApiKey, providerById } from "../lib/api-keys";
import { SeatConfig } from "../types";

export default function GameSetup() {
  const startGame = useGameStore((state) => state.startGame);
  const status = useGameStore((state) => state.status);

  const [isConfiguring, setIsConfiguring] = useState(false);
  const [playerCount, setPlayerCount] = useState<number>(6);
  const [enableSheriff, setEnableSheriff] = useState(false);
  const [defaultProvider, setDefaultProvider] = useState<string>(PROVIDER_PRESETS[0].id);
  const [defaultModel, setDefaultModel] = useState<string>(PROVIDER_PRESETS[0].models[0]);
  const [seats, setSeats] = useState<SeatConfig[]>([]);
  // 每个 provider 的 key 输入（受控）
  const [keys, setKeys] = useState<Record<string, string>>(() =>
    Object.fromEntries(PROVIDER_PRESETS.map((p) => [p.id, getApiKey(p.id)]))
  );

  // 人数变化时同步座位列表，套用默认 provider/model
  useEffect(() => {
    setSeats((prev) => {
      const next: SeatConfig[] = [];
      for (let i = 0; i < playerCount; i++) {
        next.push(prev[i] || {
          seat: i + 1, name: `Player${i + 1}`,
          provider: defaultProvider, model: defaultModel,
          base_url: providerById(defaultProvider)?.base_url || "",
        });
      }
      return next;
    });
  }, [playerCount, defaultProvider, defaultModel]);

  const updateSeat = (idx: number, patch: Partial<SeatConfig>) =>
    setSeats((s) => s.map((seat, i) => (i === idx ? { ...seat, ...patch } : seat)));

  const saveKey = (provider: string, val: string) => {
    setKeys((k) => ({ ...k, [provider]: val }));
    setApiKey(provider, val);
  };

  const startMatch = async () => {
    await startGame(seats, { enableSheriff });
  };
```

- [ ] **Step 2: 用配置面板替换"对决模式 + 角色选择"两段**

删除原 `SEC 1: GAME MODE SELECTOR`（约 190-247 行）与 `SEC 3: CHOOSE ROLE`（约 320-397 行）整段，替换为以下 **provider 默认 + per-seat 列表 + key 输入** 面板（放在 `SEC 2 人数` 之后）：

```tsx
              {/* SEC: 默认模型 + 警长流 */}
              <div className="flex flex-col gap-1.5">
                <span className="font-mono text-[11px] text-yellow-500 font-bold uppercase tracking-widest">Ⅰ. 默认模型 (Default Model)</span>
                <div className="flex flex-wrap items-center gap-2">
                  <select value={defaultProvider}
                    onChange={(e) => { const p = e.target.value; setDefaultProvider(p); setDefaultModel(providerById(p)!.models[0]); }}
                    className="bg-black border border-zinc-800 text-zinc-200 px-2 py-1 text-xs rounded">
                    {PROVIDER_PRESETS.map((p) => <option key={p.id} value={p.id}>{p.label}</option>)}
                  </select>
                  <select value={defaultModel} onChange={(e) => setDefaultModel(e.target.value)}
                    className="bg-black border border-zinc-800 text-zinc-200 px-2 py-1 text-xs rounded">
                    {providerById(defaultProvider)!.models.map((m) => <option key={m} value={m}>{m}</option>)}
                  </select>
                  <label className="flex items-center gap-1.5 text-xs text-zinc-300 font-mono ml-2">
                    <input type="checkbox" checked={enableSheriff} onChange={(e) => setEnableSheriff(e.target.checked)} className="accent-yellow-500" />
                    警长·警徽流
                  </label>
                </div>
              </div>

              {/* SEC: 各 provider 的 API Key */}
              <div className="flex flex-col gap-1.5">
                <span className="font-mono text-[11px] text-yellow-500 font-bold uppercase tracking-widest">Ⅱ. API Key (存于本地 localStorage)</span>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
                  {PROVIDER_PRESETS.map((p) => (
                    <div key={p.id} className="flex items-center gap-2">
                      <span className="text-[10px] text-zinc-400 font-mono w-24 shrink-0">{p.label}</span>
                      <input type="password" value={keys[p.id] || ""} placeholder="sk-..."
                        onChange={(e) => saveKey(p.id, e.target.value)}
                        className="flex-grow bg-zinc-950/40 border border-zinc-800 text-zinc-200 px-2 py-1 text-xs rounded font-mono" />
                    </div>
                  ))}
                </div>
              </div>

              {/* SEC: 逐座位配置 */}
              <div className="flex flex-col gap-1.5">
                <span className="font-mono text-[11px] text-yellow-500 font-bold uppercase tracking-widest flex items-center gap-2">
                  <Cpu className="w-3 h-3" /> Ⅲ. 逐座位模型 (Per-seat)
                </span>
                <div className="max-h-56 overflow-y-auto flex flex-col gap-1.5 pr-1">
                  {seats.map((seat, idx) => (
                    <div key={idx} className="flex items-center gap-2 bg-zinc-950/30 border border-zinc-900/60 rounded px-2 py-1">
                      <span className="text-yellow-500 font-mono text-[11px] w-8 shrink-0">#{seat.seat}</span>
                      <input value={seat.name} onChange={(e) => updateSeat(idx, { name: e.target.value })}
                        className="w-24 bg-black border border-zinc-800 text-zinc-200 px-1.5 py-0.5 text-[11px] rounded" />
                      <select value={seat.provider}
                        onChange={(e) => { const p = e.target.value; updateSeat(idx, { provider: p, model: providerById(p)!.models[0], base_url: providerById(p)!.base_url }); }}
                        className="bg-black border border-zinc-800 text-zinc-300 px-1.5 py-0.5 text-[11px] rounded">
                        {PROVIDER_PRESETS.map((p) => <option key={p.id} value={p.id}>{p.label}</option>)}
                      </select>
                      <select value={seat.model} onChange={(e) => updateSeat(idx, { model: e.target.value })}
                        className="flex-grow bg-black border border-zinc-800 text-zinc-300 px-1.5 py-0.5 text-[11px] rounded">
                        {providerById(seat.provider)!.models.map((m) => <option key={m} value={m}>{m}</option>)}
                      </select>
                    </div>
                  ))}
                </div>
              </div>
```

- [ ] **Step 3: 调整人数上限到 6–20，并清理无用引用**

把 `handlePlayerCountChange`（约 81-97 行）替换为：

```tsx
  const handlePlayerCountChange = (val: number) => {
    setPlayerCount(Math.max(6, Math.min(20, val)));
  };
```

并删除 `getRolesDescription` / `roleDetails` / `setSetupCount` 相关代码与对应 JSX（角色描述块、3D 重置 effect）。把开始按钮 `disabled={isLoading}` 改为 `disabled={status === "running"}`，`onClick={startMatch}`。预设徽章数组改为 `[6, 8, 9, 12, 16]`。

- [ ] **Step 4: 类型检查**

Run: `cd frontend && npm run lint`
Expected: GameSetup 无类型错误。

- [ ] **Step 5: Commit**

```bash
git add frontend/src/components/GameSetup.tsx
git commit -m "feat(fe): GameSetup 改为逐座位 LLM 配置 + API Key + 警长流"
```

---

### Task E2: SpeechConsole 渲染发言/技能/内心OS

**Files:**
- Modify: `frontend/src/components/SpeechConsole.tsx`（整体替换 body）

- [ ] **Step 1: 整体替换 `frontend/src/components/SpeechConsole.tsx`**

```tsx
import React, { useEffect, useRef } from "react";
import { MessageSquare, Scroll, Brain } from "lucide-react";
import { useGameStore } from "../store";
import { RenderLog } from "../types";

interface SpeechConsoleProps {
  isExpanded?: boolean;
  onToggle?: () => void;
}

function EventRow({ log }: { log: RenderLog }) {
  // 非发言事件：居中系统行
  if (log.kind !== "speech") {
    const tone =
      log.kind === "death" ? "text-red-400 border-red-900/60"
      : log.kind === "vote" ? "text-yellow-400 border-yellow-900/50"
      : log.kind === "skill" ? "text-fuchsia-300 border-fuchsia-900/50"
      : log.kind === "phase" ? "text-zinc-300 border-zinc-700"
      : "text-zinc-400 border-zinc-800";
    return (
      <div className="flex justify-center my-2">
        <div className={`bg-black/70 border px-3 py-1 rounded text-center max-w-[85%] ${tone}`}>
          <p className="font-mono text-[11px] font-bold">{log.text}</p>
        </div>
      </div>
    );
  }
  // 发言气泡 + 内心 OS
  return (
    <div className="flex gap-3 max-w-[90%] mr-auto">
      <div className="w-10 h-10 rounded shrink-0 flex flex-col items-center justify-center font-mono font-black text-xs shadow-md bg-black border-2 border-zinc-800 text-zinc-300">
        <span className="text-[10px] opacity-60">P</span>
        <span className="text-sm -mt-1">{log.speakerSeat ?? "?"}</span>
      </div>
      <div className="relative px-7 py-4 rounded-lg border-2 shadow-2xl parchment font-serif max-w-lg rounded-tl-none">
        <div className="flex items-center justify-between gap-6 border-b border-black/20 pb-1.5 mb-2 font-mono text-[9px] font-black uppercase tracking-wider text-black">
          <span className="text-blue-900">{log.speakerName || `玩家 ${log.speakerSeat}`}</span>
          <span className="text-zinc-700 tracking-widest">DAY {log.day}</span>
        </div>
        <p className="text-[12.5px] leading-relaxed font-sans font-extrabold whitespace-pre-wrap text-[#1a1a1a]">
          {log.text}
        </p>
        {log.privateThought && (
          <div className="mt-2 pt-2 border-t border-dashed border-black/30 bg-fuchsia-950/10 -mx-3 px-3 rounded">
            <span className="flex items-center gap-1 font-mono text-[8px] uppercase tracking-widest text-fuchsia-800 font-black mb-0.5">
              <Brain className="w-3 h-3" /> 内心 OS（上帝视角）
            </span>
            <p className="text-[11px] italic text-fuchsia-950/90 whitespace-pre-wrap">{log.privateThought}</p>
          </div>
        )}
      </div>
    </div>
  );
}

export default function SpeechConsole({ isExpanded = true, onToggle }: SpeechConsoleProps) {
  const logs = useGameStore((s) => s.logs);
  const snapshot = useGameStore((s) => s.snapshot);
  const listEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (isExpanded) listEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [logs, isExpanded]);

  const narration = snapshot?.phase_label || "幽暗城堡的丧钟敲响，AI 们各就各位...";

  return (
    <div className="flex flex-col flex-grow bg-transparent overflow-hidden relative z-10">
      <div className="flex items-center justify-between bg-transparent px-4 py-1.5 border-b border-zinc-900/50 select-none">
        <div className="flex items-center gap-2">
          <Scroll className="w-4 h-4 text-red-600 animate-pulse" />
          <span className="font-sans font-black text-xs tracking-widest text-zinc-100 uppercase ink-shadow">⚖ AI 审判会议实录 ⚖</span>
        </div>
        <div className="flex items-center gap-3">
          <div className="hidden sm:flex items-center gap-1.5 font-mono text-[9px] text-[#e0e0e0]/70">
            <MessageSquare className="w-3.5 h-3.5 text-yellow-500" />
            <span>共 {logs.length} 条</span>
          </div>
          {onToggle && (
            <button onClick={onToggle} className="flex items-center gap-1.5 px-2.5 py-1 bg-black/30 hover:bg-black/60 border border-zinc-800 rounded text-[10px] text-zinc-300 font-mono font-black uppercase tracking-widest cursor-pointer">
              {isExpanded ? "收起 ▼" : "展开 ▲"}
            </button>
          )}
        </div>
      </div>

      <div className="bg-transparent p-3 border-b border-zinc-900/30 flex gap-3 items-start">
        <div className="w-8 h-8 rounded shrink-0 bg-red-950/40 border border-red-800/60 flex items-center justify-center text-red-500 font-serif font-black text-sm animate-pulse">☠</div>
        <p className="font-sans text-xs text-[#e0e0e0] leading-relaxed font-black font-serif">{narration}</p>
      </div>

      <div className="flex-grow overflow-y-auto px-4 py-4 space-y-3 font-sans select-text bg-transparent">
        {logs.length === 0 ? (
          <div className="h-full flex flex-col items-center justify-center text-zinc-600 gap-2 py-8">
            <span className="font-serif text-4xl text-zinc-800 animate-pulse">☠</span>
            <span className="font-mono text-xs tracking-widest text-zinc-700 uppercase font-black">等待 AI 入场…</span>
          </div>
        ) : (
          logs.map((log) => <EventRow key={log.seq} log={log} />)
        )}
        <div ref={listEndRef} />
      </div>
    </div>
  );
}
```

- [ ] **Step 2: 类型检查**

Run: `cd frontend && npm run lint`
Expected: SpeechConsole 无类型错误。

- [ ] **Step 3: Commit**

```bash
git add frontend/src/components/SpeechConsole.tsx
git commit -m "feat(fe): SpeechConsole 渲染发言气泡 + 技能事件 + 内心OS"
```

---

### Task E3: ControlPanel 改为播放控制台

**Files:**
- Modify: `frontend/src/components/ControlPanel.tsx`（整体替换）

- [ ] **Step 1: 整体替换 `frontend/src/components/ControlPanel.tsx`**

```tsx
import React from "react";
import { useGameStore } from "../store";
import { Play, Pause, Square, Eye, EyeOff, Gauge } from "lucide-react";

export default function ControlPanel() {
  const status = useGameStore((s) => s.status);
  const isPlaying = useGameStore((s) => s.isPlaying);
  const speed = useGameStore((s) => s.speed);
  const revealView = useGameStore((s) => s.revealView);
  const togglePlay = useGameStore((s) => s.togglePlay);
  const setSpeed = useGameStore((s) => s.setSpeed);
  const setRevealView = useGameStore((s) => s.setRevealView);
  const cancelGame = useGameStore((s) => s.cancelGame);

  const ended = status === "ended" || status === "cancelled" || status === "error";

  return (
    <div className="bg-transparent border-t border-zinc-900/35 px-6 py-3 flex flex-wrap items-center justify-center gap-4 relative z-10 shrink-0 select-none min-h-[64px]">
      <button onClick={togglePlay} disabled={ended}
        className={`stone-btn px-5 py-2.5 font-sans font-black text-[#f5f5f5] uppercase tracking-widest rounded shadow-lg flex items-center gap-2 ${ended ? "opacity-40 cursor-not-allowed" : "hover:scale-105 active:translate-y-1"}`}>
        {isPlaying ? <Pause className="w-4 h-4 text-yellow-500" /> : <Play className="w-4 h-4 text-emerald-500" />}
        {isPlaying ? "暂停" : "继续"}
      </button>

      <div className="flex items-center gap-1.5 bg-zinc-950/30 px-3 py-1.5 rounded border border-zinc-900/50">
        <Gauge className="w-3.5 h-3.5 text-zinc-400" />
        {[1, 2, 999].map((s) => (
          <button key={s} onClick={() => setSpeed(s as 1 | 2 | 999)}
            className={`px-2 py-0.5 text-[11px] font-mono font-bold rounded ${speed === s ? "bg-yellow-500/20 text-yellow-400 border border-yellow-500" : "text-zinc-400 border border-zinc-800 hover:text-zinc-200"}`}>
            {s === 999 ? "瞬间" : `${s}x`}
          </button>
        ))}
      </div>

      <button onClick={() => setRevealView(revealView === "god" ? "suspense" : "god")}
        className="flex items-center gap-1.5 px-3 py-1.5 rounded border border-zinc-800 bg-zinc-950/30 text-[11px] font-mono font-bold text-zinc-300 hover:text-white">
        {revealView === "god" ? <Eye className="w-3.5 h-3.5 text-yellow-500" /> : <EyeOff className="w-3.5 h-3.5 text-zinc-400" />}
        {revealView === "god" ? "上帝视角" : "悬念模式"}
      </button>

      <button onClick={cancelGame} disabled={ended}
        className={`px-4 py-2 rounded border-2 border-red-950 bg-red-900 text-red-100 font-sans font-black text-xs uppercase tracking-widest flex items-center gap-2 ${ended ? "opacity-40 cursor-not-allowed" : "hover:bg-red-700"}`}>
        <Square className="w-3.5 h-3.5" /> 停止
      </button>

      {ended && <span className="font-mono text-[11px] text-zinc-400 uppercase tracking-widest">对局已结束</span>}
    </div>
  );
}
```

- [ ] **Step 2: 类型检查**

Run: `cd frontend && npm run lint`
Expected: ControlPanel 无类型错误（注意：它不再 import SkillBar）。

- [ ] **Step 3: Commit**

```bash
git add frontend/src/components/ControlPanel.tsx
git commit -m "feat(fe): ControlPanel 改为 播放/暂停/变速/视角/停止 控制台"
```

---

### Task E4: CardDeck 只读 + 悬念遮挡

**Files:**
- Modify: `frontend/src/components/CardDeck.tsx`

- [ ] **Step 1: 替换 `CardDeck` 主组件（第 131-280 行），保留顶部 `RoleIllustration`**

```tsx
export default function CardDeck() {
  const snapshot = useGameStore((s) => s.snapshot);
  const revealView = useGameStore((s) => s.revealView);
  const players = snapshot?.players || [];

  return (
    <div className="flex flex-col h-full w-full max-w-[280px] bg-[#050505]/75 backdrop-blur-md px-3 py-4 select-none relative z-10 shrink-0 shadow-2xl overflow-y-auto woodcut-texture">
      <div className="border-b-4 border-black pb-3 mb-4 text-center">
        <h2 className="font-sans font-extrabold tracking-widest text-red-600 text-lg uppercase ink-shadow">⚔ 席位卡牌 ⚔</h2>
        <p className="font-mono text-[9px] text-[#e0e0e0]/70 tracking-widest uppercase mt-1">
          {revealView === "god" ? "God View" : "Suspense"}
        </p>
      </div>

      <div className="flex flex-col gap-4">
        {players.map((p) => {
          // 上帝视角：始终亮身份；悬念模式：仅死亡或终局亮身份
          const isExposed = revealView === "god" || !p.is_alive || !!snapshot?.winner;
          const roleStr = p.role || "未知";
          let roleColor = "text-zinc-400";
          if (isExposed) {
            if (roleStr.includes("狼")) roleColor = "text-red-500 font-bold ink-shadow";
            else if (roleStr.includes("预言")) roleColor = "text-[#c084fc] font-bold ink-shadow";
            else if (roleStr.includes("女巫")) roleColor = "text-[#eab308] font-bold ink-shadow";
            else if (roleStr.includes("猎人")) roleColor = "text-[#3b82f6] font-bold ink-shadow";
            else roleColor = "text-[#10b981] font-bold ink-shadow";
          }

          return (
            <div key={p.seat}
              className={`group flex items-center bg-[#111] transition-all duration-300 rounded ${
                !p.is_alive ? "opacity-55 border-black/80 scale-95 border-2"
                : p.is_sheriff ? "border-yellow-500 border-2 ring-1 ring-yellow-500/50"
                : "manga-border"
              }`}>
              <div className="p-2 flex flex-col justify-center items-center h-full border-r border-black w-10 text-center bg-black text-[#e0e0e0]/50">
                <span className="font-mono text-xs font-bold">{p.seat}</span>
                {p.is_sheriff && <span className="text-[8px] text-yellow-500 font-bold mt-0.5">警</span>}
              </div>

              <div className="w-16 h-20 shrink-0 overflow-hidden relative border-r border-[#222]">
                <RoleIllustration roleColor={roleColor} role={isExposed ? roleStr : ""} isExposed={isExposed} />
                {!p.is_alive && (
                  <div className="absolute inset-0 bg-black/80 flex items-center justify-center">
                    <span className="text-[10px] text-red-600 font-extrabold tracking-widest border-2 border-red-700/80 px-1 py-0.5 uppercase bg-black rotate-12">出局</span>
                  </div>
                )}
              </div>

              <div className="p-2 flex-grow min-w-0">
                <h3 className="font-sans font-black text-xs truncate text-[#e0e0e0]">{p.name}</h3>
                <p className="font-mono text-[9px] mt-1 text-[#e0e0e0]/70 truncate">
                  役：<span className={roleColor}>{isExposed ? roleStr : "未知秘匿"}</span>
                </p>
                {p.model && (
                  <p className="font-mono text-[8px] text-zinc-500 mt-0.5 truncate">🤖 {p.model}</p>
                )}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
```

并删除文件顶部不再使用的 `import { Player } from "../types";`（`RoleIllustration` 的 `role: string` 入参保留不变）。

- [ ] **Step 2: 类型检查**

Run: `cd frontend && npm run lint`
Expected: CardDeck 无类型错误。

- [ ] **Step 3: Commit**

```bash
git add frontend/src/components/CardDeck.tsx
git commit -m "feat(fe): CardDeck 只读化 + 上帝/悬念身份遮挡 + 模型标签"
```

---

### Task E5: App / TopHeader / GameOverPanel 接线，移除 SkillBar

**Files:**
- Modify: `frontend/src/App.tsx`
- Modify: `frontend/src/components/TopHeader.tsx`
- Modify: `frontend/src/components/GameOverPanel.tsx`

- [ ] **Step 1: App.tsx 接线**

(a) 替换第 14-26 行的 store 取值与初始化逻辑为：

```tsx
  const snapshot = useGameStore((state) => state.snapshot);
  const status = useGameStore((state) => state.status);
  const exitToSetup = useGameStore((state) => state.exitToSetup);
  const [isSpeechExpanded, setIsSpeechExpanded] = useState(true);
  const [speechHeight, setSpeechHeight] = useState(210);
  const [isDragging, setIsDragging] = useState(false);
  const [isSidebarExpanded, setIsSidebarExpanded] = useState(true);

  // 未开局（idle）显示开局配置页
  const inSetup = status === "idle" || (!snapshot && status !== "running");
```

(b) 替换第 28-50 行（旧 loading / START_SCREEN 分支）为：

```tsx
  if (inSetup) {
    return (
      <div className="relative w-screen h-screen flex flex-col items-center justify-center bg-[#0b0914] text-zinc-100 overflow-hidden font-sans select-none antialiased">
        <ThreeCanvas />
        <GameSetup />
        <div className="absolute inset-0 pointer-events-none border-4 border-zinc-950/80 z-50 rounded" />
      </div>
    );
  }
```

(c) 第 113-115 行 GameOver 覆盖层改为依据 snapshot.winner：

```tsx
      {snapshot?.winner && (
        <GameOverPanel winner={snapshot.winner} onExit={exitToSetup} />
      )}
```

(d) 删除第 53-104 行的 `startResizing*` 中对 `gameState` 的依赖无影响（保留拖拽逻辑原样）；删除第 154-166 行旧的 `gameState?.winner` 提示块（已由 GameOverPanel 接管），或将 `gameState` 替换为 `snapshot`。确保整个文件不再引用 `gameState/fetchState/resetGame/exitGame/state.phase`。

- [ ] **Step 2: TopHeader.tsx 改吃 snapshot**

把组件内对 `state.dayNumber/phase` 等的读取改为：

```tsx
  const snapshot = useGameStore((s) => s.snapshot);
  const day = snapshot?.day ?? 0;
  const phaseLabel = snapshot?.phase_label ?? "";
  const alive = snapshot?.alive_count ?? 0;
```

并把模板里展示天数/阶段/存活数的地方替换为 `day` / `phaseLabel` / `alive`（保留原有样式 class）。

- [ ] **Step 3: GameOverPanel.tsx 改签名**

把 props 改为 `{ winner, onExit }`：

```tsx
export default function GameOverPanel({ winner, onExit }: { winner: string; onExit: () => void }) {
  const label = winner.includes("狼") || winner === "werewolf" ? "狼人阵营胜利" : "好人阵营胜利";
  // ... 用 label 渲染；底部按钮 onClick={onExit} 文案"返回配置"
```

保留其余视觉样式；删除对旧 `gameState/onRestart` 的引用。

- [ ] **Step 4: 类型检查**

Run: `cd frontend && npm run lint`
Expected: 全绿（此时整个前端应无类型错误；`SkillBar.tsx` 文件保留在仓库但无人引用）。

- [ ] **Step 5: Commit**

```bash
git add frontend/src/App.tsx frontend/src/components/TopHeader.tsx frontend/src/components/GameOverPanel.tsx
git commit -m "feat(fe): App/TopHeader/GameOverPanel 接 snapshot，移除人类交互入口"
```

---

### Task E6: Vite 代理到 Python + 启动脚本

**Files:**
- Modify: `frontend/vite.config.ts`
- Modify: `frontend/package.json`

- [ ] **Step 1: 给 vite.config.ts 加代理**

在 `defineConfig({...})` 的配置对象里加入（与现有 plugins 同级）：

```typescript
  server: {
    port: 5173,
    proxy: {
      "/api/v1": {
        target: "http://127.0.0.1:8000",
        changeOrigin: true,
      },
    },
  },
```

（前端用相对路径 `/api/v1`，由 Vite 代理到 Python，免 CORS。）

- [ ] **Step 2: package.json 加纯前端启动脚本**

在 `scripts` 中加入：

```json
    "dev:spectate": "vite",
```

（保留原 `dev: tsx server.ts`；纯 LLM 观战模式用 `npm run dev:spectate`。）

- [ ] **Step 3: 端到端手测**

终端 1（后端）：`cd D:/AI_werewolf/Frontend_6_3/MultiAgent-Werewolf && uv run werewolf-api`
终端 2（前端）：`cd D:/AI_werewolf/Frontend_6_3/MultiAgent-Werewolf/frontend && npm run dev:spectate`
浏览器开 `http://localhost:5173`，验证：
1. 开局页能逐座位选 provider/model、填 key（刷新后 key 仍在 = localStorage 生效）。
2. 至少配 1 个真实可用 provider/key（其余可设 demo——把某座位 provider 选成会失败的也行，引擎有随机兜底），点开始。
3. 对话框逐条出现 AI 发言（打字/逐条），技能/投票/出局以系统行出现。
4. 暂停/继续/变速生效；上帝视角能看到内心 OS 与全部身份，悬念模式遮挡未揭示项。
5. 停止后对局结束、可返回配置再开一局。

- [ ] **Step 4: Commit**

```bash
git add frontend/vite.config.ts frontend/package.json
git commit -m "chore(fe): Vite 代理 /api/v1 到 Python + dev:spectate 脚本"
```

---

## Self-Review（计划自查）

- **Spec 覆盖**：决策 1（Python 大脑/前端调 API）→ 全部任务；2（增量轮询）→ C2/C3/C4/D3；3（上帝视角+reveal+悬念开关）→ C3 `_reveal_visibility`、D3 `shouldMask`、E3/E4 视角开关；4（逐座位配置）→ A1/A3/E1/D2；5（技能内嵌事件）→ C3 `_classify`、E2；6（播放控制）→ D3 节奏机、E3；7（范围=配置页+主界面）→ E1–E6；8（key 不落盘）→ A4 + D2/D3 随 body 传；9（private_thought）→ B1、C3、E2；10（方案B 投影）→ C2/C3。
- **占位符扫描**：无 TBD/TODO；C3 测试里一个啰嗦断言已在步骤中明确要求改成确定形式。
- **类型一致性**：后端 `build_view(run_dir, *, since, status, error)` 在 C3 定义、C4 调用一致；`ViewResponse/ViewSnapshot/ViewPlayer/ViewEvent` 字段在 C2 定义、C3 构造、D1 镜像、E2/E4 消费一致；前端 `SeatConfig`（D1）在 D2/D3/E1 一致；store 暴露 `startGame/cancelGame/togglePlay/setSpeed/setRevealView/exitToSetup/snapshot/logs/status/isPlaying/speed/revealView` 在 E1–E5 按此消费。
- **已知风险**：`tests/interface/test_api_actions.py` 的 app/deps fixture 名称以该文件现有用例为准（若 `deps.get_runs_dir` 覆盖方式不同，按文件既有 pattern 调整）；夜间技能事件的 `data` 字段名（target_id/result）以 `action_processor.py` 实际为准，C3 已用宽松取值（取不到则为 None，不报错）。
