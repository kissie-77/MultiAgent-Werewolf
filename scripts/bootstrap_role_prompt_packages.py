"""One-time migration helper: legacy v2 bundle -> per-role v1 packages (completed).

Per-role packages now live under strategy/prompts/roles/<role>/v1/.
The legacy strategy/prompts/v2/ bundle has been removed.
"""

from __future__ import annotations


def main() -> None:
    print(
        "Bootstrap already completed. Edit strategy/prompts/roles/<role>/<version>/ directly "
        "or use role_prompt_registry.copy_role_prompt_package() for evolution bumps."
    )


if __name__ == "__main__":
    main()
