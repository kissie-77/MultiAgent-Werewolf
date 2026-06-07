# Match configs

## Standard boards (official)

All web and CLI matches should use one of these five files. Roles are auto-dealt from the seat count; only the LLM roster is defined in YAML.

| File | Players | Typical use |
|------|---------|-------------|
| `standard-4p.yaml` | 4 | Quick mini board |
| `standard-6p.yaml` | 6 | Default / human-vs-AI |
| `standard-8p.yaml` | 8 | Mid-size |
| `standard-12p.yaml` | 12 | Badge-flow default |
| `standard-16p.yaml` | 16 | Extended roles |

All standard boards use **Volcengine Ark / Doubao** via `ARK_API_KEY` and endpoint id `ARK_EP` in `.env`.

For all 8 supported vendors (DS / 豆包 / GPT / Gemini / Claude / Kimi / GLM / MiniMax) and env naming rules, see [docs/interface/PROVIDERS.md](../docs/interface/PROVIDERS.md) and `.env.example`.

## Other files

| File | Purpose |
|------|---------|
| `example.yaml` | Template for custom configs (copy & edit) |
| `observability.yaml` | Alert/observability settings (not a game board) |
| `archive/` | Retired configs kept for reference |

## API / frontend

- `POST /api/v1/games/start` with `config_id: "standard-6p"` (etc.)
- Frontend `GameSetup` maps player count `4/6/8/12/16` → `standard-{N}p`
