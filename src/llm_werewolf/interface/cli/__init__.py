"""Command-line entrypoints for running werewolf games."""

__all__ = ["entry", "main"]


def __getattr__(name: str):
    if name == "entry":
        from llm_werewolf.interface.cli.entry import entry

        return entry
    if name == "main":
        from llm_werewolf.interface.cli.entry import main

        return main
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
