# codi

A modern Discord bot with two pluggable **personalities**. Run them as a single
process or as two independent bots.

| Personality | Purpose | Trigger style |
|---|---|---|
| **CODI** | Crypto price lookups and forecast charts, backed by [crypto-predictions](https://github.com/Omni-Analytics-Group/crypto-predictions). | `!` prefix commands |
| **Wooloo** | Pokemon lookups, uplifting messages, and an optional Claude-powered chat mode. | `@mention` + `!` prefix commands |

## Architecture

```
src/codi
├── config.py              # Pydantic settings, all env-driven
├── bot.py                 # CodiBot subclass + run_single / run_all
├── __main__.py            # `python -m codi` CLI
├── personalities/         # Pluggable personality plugins
│   ├── base.py            # Personality ABC
│   ├── codi.py            # CODI personality
│   └── wooloo.py          # Wooloo personality
├── cogs/                  # discord.py cogs
│   ├── crypto.py          # CODI commands
│   └── wooloo.py          # Wooloo commands + on_message listener
├── services/              # Thin async clients
│   ├── crypto_api.py      # Crypto Predictions API
│   ├── pokemon_api.py     # PokeAPI
│   └── anthropic_ai.py    # Claude wrapper for Wooloo AI mode
└── data/uplift_quotes.py  # Hand-written uplift mode responses
```

Adding another personality is a matter of dropping a new file under
`personalities/` and registering it in `personalities/__init__.py`.

## Setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
cp .env.example .env   # then fill in your tokens
```

In the [Discord Developer Portal](https://discord.com/developers/applications):

1. Create two applications (one for CODI, one for Wooloo) and turn each into a bot.
2. Under **Bot → Privileged Gateway Intents**, enable **Message Content Intent** for both.
3. Copy each bot token into `.env` as `CODI_BOT_TOKEN` and `WOOLOO_BOT_TOKEN`.
4. Generate an OAuth2 URL with scopes `bot` and `applications.commands` plus the
   permissions `Send Messages`, `Embed Links`, `Attach Files`, `Read Message
   History`. Invite each bot to its server.

For Wooloo's AI mode, put your Anthropic API key into `ANTHROPIC_API_KEY`.

## Running

```bash
# Run every personality that has a token configured, in one process.
codi

# Or just one at a time (useful in production, one container per bot).
codi --personality codi
codi --personality wooloo
```

## Commands

### CODI (`!` prefix)

| Command | Description |
|---|---|
| `!price <coin>` | Latest USD price. `coin` is a ticker (`btc`, `eth`) or CoinGecko ID (`bitcoin`). |
| `!predict <coin> [short\|long]` | Latest forecast chart. Defaults to short-term. |
| `!collage <coin>` | Grid comparing every model's latest prediction. |
| `!models` | List supported forecasting models. |
| `!coins` | List popular coins the API knows about. |
| `!return <coin> price \| predictions [longterm\|shortterm]` | Legacy syntax, kept for back-compat. Aliases the modern commands. |
| `!help` | discord.py's built-in help. |

Examples:

```
!price btc
!predict eth long
!collage solana

# Legacy form (still works):
!return BTC price
!return BTC predictions
!return BTC predictions longterm
```

### Wooloo (`@mention` + `!` prefix)

`@Wooloo` mentions are the primary UX — the text after the mention decides what
happens:

| Mention input | Behavior |
|---|---|
| `@Wooloo hello there` | Replies using the current mode (`uplift` or `ai`). |
| `@Wooloo mode` | Shows current mode. |
| `@Wooloo mode ai` / `@Wooloo mode uplift` | Switches mode for this server. |
| `@Wooloo pokemon <name>` | Pokemon info card. |
| `@Wooloo help` | Help embed. |

Prefix commands are also available: `!mode`, `!mode ai`, `!mode uplift`,
`!pokemon <name>`, `!uplift`.

**Modes**

- **`uplift`** — replies are chosen at random from a curated list in
  `src/codi/data/uplift_quotes.py`. Edit that file to add your own.
- **`ai`** — sends the user's message to Claude with a short Wooloo-in-character
  system prompt. Requires `ANTHROPIC_API_KEY`.

## Development

```bash
pytest            # run the test suite
ruff check .      # lint
ruff format .     # format
```

Tests use `pytest-httpx` to stub HTTP calls for the crypto and Pokemon clients,
so nothing hits the network.

## Extending

Adding a new command to an existing personality: drop it in the matching cog
under `src/codi/cogs/`.

Adding a new personality:

1. Write `src/codi/personalities/<name>.py` that subclasses `Personality`.
2. Register it in `src/codi/personalities/__init__.py`.
3. Add a `<NAME>_BOT_TOKEN` to `Settings` and to `configured_personalities()`.
4. Update the CLI's `--personality` choices.

## License

MIT — see [LICENSE](LICENSE) if present; otherwise the license is declared in
`pyproject.toml`.
