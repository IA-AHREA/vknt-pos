# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

A Discord bot (Python, `discord.py`) for an EVE Online corp that tracks rent payment status for
player-owned Outposts ("POS"). Data lives in PostgreSQL via `prisma-client-py`. Deployed on Railway
from the included `Dockerfile`.

## Commands

```bash
pip install -r requirements.txt

# After any change to prisma/schema.prisma:
python -m prisma generate

# Create + apply a new migration during development:
python -m prisma migrate dev --name <description>

# Apply existing migrations only (what the Docker CMD runs in production):
python -m prisma migrate deploy

# Run the bot locally (needs DISCORD_TOKEN, CEO_ROLE_ID, DATABASE_URL in .env):
python -m bot.main

# One-time import of the legacy eve_pos.db (sqlite) into Postgres — idempotent (upsert):
DATABASE_URL="postgresql://..." python3 scripts/migrate_from_sqlite.py eve_pos.db
```

There is no automated test suite and no configured linter. To validate changes, load the bot's
extensions against a real Postgres and exercise `bot.db.db` (the Prisma client) directly in a
throwaway script — the Cog/command functions are thin wrappers around plain async calls, so this
covers the business logic without needing a live Discord gateway connection.

## Architecture

- **`bot/main.py`** — entrypoint. `MyBot.setup_hook` connects Prisma, loads every module listed in
  `EXTENSIONS`, then syncs the command tree. A global `bot.tree.error` handler turns
  `app_commands.CheckFailure` into a plain "No autorizado" and logs everything else instead of
  leaking exceptions to users — commands should let errors propagate rather than catching broadly.
- **`bot/db.py`** — a single `db = Prisma()` instance imported everywhere; its connect/disconnect
  lifecycle is owned by `main.py`, not by individual commands.
- **`bot/config.py`** — fail-fast env var loading (`DISCORD_TOKEN`, `CEO_ROLE_ID`, `DATABASE_URL`).
- **`bot/checks.py`** — `es_ceo()`, the permission gate used by every admin command. Authorization is
  a single `CEO_ROLE_ID` for one guild by design (no multi-guild/multi-role support).
- **`bot/utils.py`** — all month arithmetic lives here (`sumar_meses`, `a_total_meses`, `es_moroso`,
  `estado_texto`). This is the one place that encodes the payment state machine: a POS tracks
  `pagado_hasta_mes` (0 means "Pendiente", never paid) + `anio_vencimiento`. Any new command that
  touches payment state should reuse these helpers instead of reimplementing the month math.
- **`bot/ui.py`** — two reusable `discord.ui.View`s:
  - `PaginadorView` pages through either `list[str]` or `list[discord.Embed]` with Anterior/Siguiente
    buttons, restricted to the user who invoked the command. Use `await view.enviar_inicial(interaction)`
    to send the first page instead of manually calling `send_message`.
  - `SelectorPosView` is a dropdown used to disambiguate when a Discord user owns more than one POS
    (used by both the "Pagar Outpost" context menu and `/buscar`).
- **`bot/commands/*.py`** — one `commands.Cog` per file, each exposing an async `setup(bot)` that
  `main.py` loads via the `EXTENSIONS` tuple. Adding a new command module means adding it there.
  - `sistemas.py` — the EVE system catalog is dynamic (`/sistema-agregar` etc.), not hardcoded. Exposes
    `sistema_autocomplete()`, reused by `outposts.py`.
  - `outposts.py` — POS CRUD, `/reporte` (Embeds, status filter, sorted by urgency — most overdue
    first), `/buscar` + `EditarPosModal`. POS ids are **auto-assigned** (first free slot in the
    100-999 range, refilling gaps left by deletions) — never add a command parameter asking the user
    to type an `id_num`.
  - `pagos.py` — `PagoModal` (payment amount is an optional ISK float), the "Pagar Outpost" context
    menu (opens `SelectorPosView` when the target user has more than one POS), `/corregir-pago`,
    `/historial-pos`.
  - `recordatorios.py` — `/recordar-mora` takes no parameters; it always evaluates against
    `datetime.now()`. Do not reintroduce a manual month/year parameter here.
- **Audit trail convention**: every write that changes payment status (`PagoModal`, `/corregir-pago`,
  `EditarPosModal`) updates the `Outpost` row *and* inserts a `Pago` row inside the same
  `async with db.tx()` block — `tipo` (`PAGO`/`CORRECCION`), the `meses` delta, and a
  `mes_resultante`/`anio_resultante` snapshot. Keep this pairing for any new command that changes
  payment state.
- **Data model** (`prisma/schema.prisma`): `Sistema` 1—N `Outpost` 1—N `Pago`. `Outpost.discord_id`
  is a plain string (Discord snowflake) and intentionally **not unique** — one user can own multiple
  POS. `Sistema` deletion is `ON DELETE RESTRICT` (can't delete a system still assigned to a POS);
  `Pago` rows cascade-delete when their `Outpost` is deleted.
- **Deployment**: Railway builds the `Dockerfile` directly (no Nixpacks). The image installs
  `nodejs` and `libatomic1` because `prisma-client-py` downloads its own portable Node.js to run
  `prisma generate`/`migrate deploy`, and that binary needs `libatomic.so.1`, which
  `python:3.11-slim` doesn't ship — don't remove that apt package. The container `CMD` runs
  `prisma migrate deploy` before starting the bot on every boot.
- If a Postgres database ever gets its schema applied outside of Prisma (e.g. by hand via `psql`),
  `migrate deploy` will fail with `P3005` ("schema is not empty"). Baseline it once with
  `prisma migrate resolve --applied <migration_folder_name> --schema=prisma/schema.prisma` before
  it will proceed normally on subsequent deploys.
