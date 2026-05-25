# TUI Startup And Human Input Design

## Goal

Make the TUI a first-class play surface: it always opens with a setup screen, then runs
either all-agent games or human-vs-LLM games with in-app human input.

## Startup Flow

The TUI entrypoint always launches a setup screen. Command-line arguments are treated as
defaults for that screen, not as an automatic start bypass.

The setup screen exposes:

- Participation mode: all-agent or human-vs-LLM.
- Player count: 6-20.
- Sheriff/badge flow toggle.
- Agent raw output toggle.
- Start game command.

When the user starts the game, the app resolves the mode to a config file, applies the
selected count and sheriff toggle, creates the engine, wires AgentScope with the raw-output
flag, and switches to the game view.

## Human Input

Human-vs-LLM TUI games use a `TextualHumanInputProvider` that implements the existing
`HumanInputProvider` protocol. It shows the current prompt and options in the game view,
enables the input box, awaits a submitted value, validates it, and retries with feedback
when the value is invalid.

Required input rules stay the same as CLI:

- Skills, targets, and votes accept only numbers.
- Speeches accept plain non-empty text.

## Visibility

All-agent games use observer view and show the full event stream. Human-vs-LLM games use
the single human player's view and filter events through the existing event visibility
rules before displaying them in the chat panel.

## Architecture

- `llm_werewolf.interface.tui_runtime` owns runtime settings and engine creation.
- `llm_werewolf.ui.tui_human_input` owns Textual-backed human input parsing.
- `llm_werewolf.ui.tui_app.WerewolfTUI` owns setup widgets, view switching, event routing,
  and input box lifecycle.
- CLI behavior remains unchanged.

## Tests

Add focused tests for:

- TUI runtime applies player count and sheriff settings.
- TUI entrypoint passes command-line values as startup defaults.
- Textual human input provider retries invalid numeric input and accepts speeches.
- The TUI app records human viewer id for human-vs-LLM games and filters chat events
  through the existing chat panel path.
