import random
from typing import TYPE_CHECKING, Any
from pathlib import Path

from rich.console import Console

from llm_werewolf.core.types import Event, EventType, GamePhase, RoleProtocol, AgentProtocol
from llm_werewolf.core.config import GameConfig
from llm_werewolf.core.events import EventLogger
from llm_werewolf.core.locale import Locale
from llm_werewolf.core.observation import ObservationBuilder
from llm_werewolf.adapter.information_hub import InformationHub
from llm_werewolf.core.event_visibility import HUB_DIALOGUE_EVENT_TYPES, resolve_visible_to
from llm_werewolf.core.phase_interaction import PhaseInteraction
from llm_werewolf.core.types import Camp
from llm_werewolf.core.player import Player
from llm_werewolf.core.victory import VictoryChecker
from llm_werewolf.core.game_state import GameState
from llm_werewolf.core.serialization import load_game_state, save_game_state
from llm_werewolf.core.event_formatter import EventFormatter

if TYPE_CHECKING:
    from collections.abc import Callable

console = Console()


class GameEngineBase:
    """Base game engine class with core functionality."""

    def __init__(self, config: GameConfig | None = None, language: str = "en-US") -> None:
        """Initialize the game engine.

        Args:
            config: Game configuration.
            language: Language code for localization (en-US, zh-TW, zh-CN).
        """
        self.config = config
        self.game_state: GameState | None = None
        self.event_logger = EventLogger()
        self.victory_checker: VictoryChecker | None = None
        self.locale = Locale(language)
        self.observation_builder = ObservationBuilder()
        self._last_phase: str = ""  # Track phase changes for separators

        self.information_hub = InformationHub()
        self.phase_interaction = PhaseInteraction(self.information_hub)

        self.on_event: Callable[[Event], None] = self._default_print_event

    def _default_print_event(self, event: Event) -> None:
        """Default event handler that prints to console.

        This can be overridden by TUI or other interfaces.

        Args:
            event: The game event to display.
        """
        # Print phase separator when phase changes
        if event.phase != self._last_phase and event.event_type == EventType.PHASE_CHANGED:
            if "night" in event.phase.lower():
                console.print(f"\n{self.locale.get('night_separator')}")
            elif "sheriff" in event.phase.lower():
                console.print("\n" + "=" * 60)
                console.print("        🎖️  SHERIFF ELECTION PHASE  🎖️")
                console.print("=" * 60 + "\n")
            elif "day" in event.phase.lower():
                console.print(f"\n{self.locale.get('day_separator')}")
            self._last_phase = event.phase

        # Use the centralized event formatter (without timestamp for CLI)
        formatted_text = EventFormatter.format_event(event, include_timestamp=False)
        console.print(formatted_text)

    def setup_game(self, players: list[AgentProtocol], roles: list[RoleProtocol]) -> None:
        """Initialize the game with players and roles.

        Args:
            players: List of agent instances with name and model attributes.
            roles: List of role instances to assign.
        """
        if len(players) != len(roles):
            msg = f"Number of players ({len(players)}) must match number of roles ({len(roles)})"
            raise ValueError(msg)

        shuffled_roles = roles.copy()
        random.shuffle(shuffled_roles)

        player_objects = []
        for idx, (agent, role_class) in enumerate(
            zip(players, shuffled_roles, strict=False), start=1
        ):
            player_id = f"player_{idx}"
            name = agent.name
            ai_model = agent.model
            player = Player(
                player_id=player_id, name=name, role=role_class, agent=agent, ai_model=ai_model
            )
            if hasattr(agent, "bind_role"):
                agent.bind_role(role_class, seat_number=idx)  # type: ignore[attr-defined]
            player_objects.append(player)

        self.game_state = GameState(player_objects)
        self.game_state.information_hub = self.information_hub
        self.game_state.phase_interaction = self.phase_interaction
        self.victory_checker = VictoryChecker(self.game_state)
        self.information_hub.set_context_provider(
            build_observation=lambda player: self.build_player_observation(
                player, for_agent_decision=True
            ),
            get_alive_players=lambda: self.game_state.get_alive_players()
            if self.game_state
            else [],
        )

        self._log_event(
            EventType.GAME_STARTED,
            self.locale.get("game_started", player_count=len(player_objects)),
            data={"player_count": len(player_objects)},
        )

    def assign_roles(self) -> dict[str, str]:
        """Assign roles to players (already done in setup_game).

        Returns:
            dict[str, str]: Mapping of player_id to role_name.
        """
        if not self.game_state:
            msg = "Game not initialized"
            raise RuntimeError(msg)

        return {p.player_id: p.get_role_name() for p in self.game_state.players}

    def check_victory(self) -> bool:
        """Check if any victory condition is met.

        Returns:
            bool: True if the game has ended.
        """
        if not self.victory_checker:
            return False

        result = self.victory_checker.check_victory()

        if result.has_winner:
            if self.game_state:
                self.game_state.set_phase(GamePhase.ENDED)
                self.game_state.winner = result.winner_camp

            self._log_event(
                EventType.GAME_ENDED,
                self.locale.get("game_ended", winner=result.winner_camp, reason=result.reason),
                data={
                    "winner_camp": result.winner_camp,
                    "winner_ids": result.winner_ids,
                    "reason": result.reason,
                },
            )

            return True

        return False

    def _log_event(
        self,
        event_type: EventType,
        message: str,
        data: dict | None = None,
        visible_to: list[str] | None = None,
    ) -> None:
        """Log an event and notify listeners.

        Args:
            event_type: Type of the event.
            message: Event message.
            data: Additional event data.
            visible_to: List of player IDs who can see this event.
        """
        if not self.game_state:
            return

        if visible_to is None:
            wolf_ids = [
                p.player_id
                for p in self.game_state.get_players_by_camp(Camp.WEREWOLF)
                if p.is_alive()
            ]
            visible_to = resolve_visible_to(
                event_type, data, wolf_player_ids=wolf_ids
            )

        event = self.event_logger.create_event(
            event_type=event_type,
            round_number=self.game_state.round_number,
            phase=self.game_state.phase.value,
            message=message,
            data=data,
            visible_to=visible_to,
        )

        self.on_event(event)

    def build_player_observation(
        self,
        player: Player,
        include_visible_events: bool = True,
        include_private_notes: bool = True,
        exclude_event_types: frozenset | None = None,
        *,
        for_agent_decision: bool = False,
    ) -> str:
        """Build a filtered prompt context for a single player.

        When ``for_agent_decision`` is True, dialogue events are omitted from the
        event block; speeches are expected in MsgHub / ReAct memory instead.
        """
        if not self.game_state:
            return ""

        merged_exclude = exclude_event_types
        if for_agent_decision:
            merged_exclude = (merged_exclude or frozenset()) | HUB_DIALOGUE_EVENT_TYPES

        public_state = self.game_state.get_public_info()
        visible_events = self.event_logger.get_events_for_player(player.player_id)
        if merged_exclude:
            visible_events = [
                event
                for event in visible_events
                if event.event_type not in merged_exclude
            ]
        private_notes = player.get_private_notes(self.game_state)
        observation = self.observation_builder.build(
            player=player,
            game_state=public_state,
            all_players=self.game_state.players,
            visible_events=visible_events,
            private_notes=private_notes,
        )
        return self.observation_builder.format_for_prompt(
            observation,
            include_visible_events=include_visible_events,
            include_private_notes=include_private_notes,
        )

    def build_shared_observation(
        self,
        players: list[Player],
        additional_notes: list[str] | None = None,
        include_visible_events: bool = True,
        exclude_event_types: frozenset | None = None,
        *,
        for_agent_decision: bool = False,
    ) -> str:
        """Build filtered context that is safe to share across a player group."""
        if not self.game_state or not players:
            return ""

        shared_events = self.event_logger.get_events_for_players([player.player_id for player in players])
        merged_exclude = exclude_event_types
        if for_agent_decision:
            merged_exclude = (merged_exclude or frozenset()) | HUB_DIALOGUE_EVENT_TYPES
        if merged_exclude:
            shared_events = [
                event
                for event in shared_events
                if event.event_type not in merged_exclude
            ]
        from llm_werewolf.core.observation import flatten_private_notes

        private_notes = flatten_private_notes(list(additional_notes or []))
        observation = self.observation_builder.build(
            player=players[0],
            game_state=self.game_state.get_public_info(),
            all_players=self.game_state.players,
            visible_events=shared_events,
            private_notes=private_notes,
        )
        return self.observation_builder.format_for_prompt(
            observation,
            include_visible_events=include_visible_events,
            include_private_notes=bool(private_notes),
        )

    def get_game_state(self) -> GameState | None:
        """Get the current game state.

        Returns:
            GameState | None: The game state.
        """
        return self.game_state

    def get_events(self) -> list[Event]:
        """Get all game events.

        Returns:
            list[Event]: List of events.
        """
        return self.event_logger.events

    async def play_game(self) -> str:
        """Run the main game loop.

        Returns:
            str: The final game result.
        """
        if not self.game_state:
            return "Game not initialized"

        while not self.check_victory():
            self.game_state.reset_deaths()

            await self.run_night_phase()

            if self.check_victory():
                break

            # Sheriff election (only on first day)
            if self.game_state.round_number == 1 and not self.game_state.sheriff_election_done:
                self.game_state.next_phase()  # Move to SHERIFF_ELECTION
                await self.execute_sheriff_election()

            if self.check_victory():
                break

            self.game_state.next_phase()  # Move to DAY_DISCUSSION
            await self.run_day_phase()

            self.game_state.next_phase()  # Move to DAY_VOTING
            await self.run_voting_phase()

            if self.check_victory():
                break

            self.game_state.next_phase()  # Move to next NIGHT

        if self.game_state.winner:
            return self.locale.get("game_over", winner=self.game_state.winner)

        return self.locale.get("game_ended", winner="unknown", reason="")

    async def step(self) -> list[str]:
        """Execute one step of the game (one phase)."""
        if not self.game_state:
            return ["Game not initialized"]

        if self.check_victory():
            return [f"Game Over! {self.game_state.winner} camp wins!"]

        phase_messages = []
        current_phase = self.game_state.get_phase()

        if current_phase == GamePhase.SETUP:
            self.game_state.next_phase()
            phase_messages = [
                "Game initialized! Press 'n' to start the first night phase.",
                f"Round {self.game_state.round_number} begins.",
            ]
        elif current_phase == GamePhase.NIGHT:
            phase_messages = await self.run_night_phase()
            if not self.check_victory():
                self.game_state.next_phase()
        elif current_phase == GamePhase.SHERIFF_ELECTION:
            await self.execute_sheriff_election()
            self.game_state.next_phase()
            phase_messages = ["Sheriff election completed."]
        elif current_phase == GamePhase.DAY_DISCUSSION:
            phase_messages = await self.run_day_phase()
            self.game_state.next_phase()
        elif current_phase == GamePhase.DAY_VOTING:
            phase_messages = await self.run_voting_phase()
            if not self.check_victory():
                self.game_state.next_phase()

        return phase_messages

    def save_game(self, file_path: str | Path) -> None:
        """Save the current game state to a file.

        Args:
            file_path: Path to save the game state.

        Raises:
            RuntimeError: If game is not initialized.
        """
        if not self.game_state:
            msg = "Game not initialized"
            raise RuntimeError(msg)

        save_game_state(self.game_state, file_path)

    def load_game(
        self, file_path: str | Path, agent_factory: dict[str, Any] | None = None
    ) -> None:
        """Load a game state from a file.

        Args:
            file_path: Path to load the game state from.
            agent_factory: Optional dictionary mapping player_id to agent instances.
                          If not provided, players will have no agents.

        Note:
            Agents cannot be serialized, so they must be recreated manually.
            Pass a dictionary mapping player_id to agent instances to restore agents.
        """
        self.game_state = load_game_state(file_path, agent_factory)
        self.victory_checker = VictoryChecker(self.game_state)
