from rich.style import Style

CAMP_COLORS = {"werewolf": "red", "villager": "green", "neutral": "yellow"}

STATUS_COLORS = {
    "alive": "green",
    "dead": "grey50",
    "protected": "blue",
    "poisoned": "purple",
    "charmed": "magenta",
    "marked": "orange1",
}

PHASE_COLORS = {
    "setup": "cyan",
    "night": "blue",
    "day_discussion": "yellow",
    "day_voting": "orange1",
    "ended": "red",
}

STYLE_WEREWOLF = Style(color="red", bold=True)
STYLE_VILLAGER = Style(color="green", bold=True)
STYLE_NEUTRAL = Style(color="yellow", bold=True)
STYLE_DEAD = Style(color="grey50", strike=True)
STYLE_SYSTEM = Style(color="cyan", italic=True)
STYLE_ERROR = Style(color="red", bold=True)
STYLE_SUCCESS = Style(color="green", bold=True)
STYLE_WARNING = Style(color="yellow")

TUI_CSS = """
Screen {
    background: $surface;
}

#player_panel {
    width: 25%;
    height: 100%;
    border: solid $primary;
    background: $panel;
}

#game_panel {
    width: 50%;
    height: 50%;
    border: solid $secondary;
    background: $panel;
}

#debug_panel {
    width: 25%;
    height: 100%;
    border: solid $accent;
    background: $panel;
}

#chat_panel {
    width: 50%;
    height: 50%;
    border: solid $success;
    background: $panel;
}

.panel_title {
    text-style: bold;
    background: $boost;
    color: $text;
    padding: 0 1;
}

.alive {
    color: $success;
}

.dead {
    color: $error;
    text-style: strike;
}

.werewolf {
    color: red;
    text-style: bold;
}

.villager {
    color: green;
    text-style: bold;
}

.neutral {
    color: yellow;
    text-style: bold;
}

.night {
    background: #1a1a2e;
    color: #ffffff;
}

.day {
    background: #f0f0f0;
    color: #000000;
}
"""


def get_camp_color(camp: str) -> str:
    """获取阵营对应的颜色。

    Args:
        camp: 阵营名称。

    Returns:
        str: 颜色名称。
    """
    return CAMP_COLORS.get(camp, "white")


def get_status_color(status: str) -> str:
    """获取状态对应的颜色。

    Args:
        status: 状态名称。

    Returns:
        str: 颜色名称。
    """
    return STATUS_COLORS.get(status, "white")


def get_phase_color(phase: str) -> str:
    """获取游戏阶段对应的颜色。

    Args:
        phase: 阶段名称。

    Returns:
        str: 颜色名称。
    """
    return PHASE_COLORS.get(phase, "white")
