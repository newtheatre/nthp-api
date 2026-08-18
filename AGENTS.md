# AGENTS.md

Generates a JSON API from the [history-project](https://github.com/newtheatre/history-project) content repo, via a sqlite database. Two steps: `load` (content → sqlite) then `dump` (sqlite → JSON).

## Docs

Start at [docs/00-Docs.md](docs/00-Docs.md) — index of plans, reviews and task write-ups. See [README.md](README.md) for setup and usage.

## Commands

- `uv sync` — install dependencies
- `./nthp load` / `./nthp dump` / `./nthp build` — run the generator
- `uv run pytest` — tests
- `prek install` — lint and format git hooks (ruff), `prek run --all-files` to run them

## Conventions

- British English for naming and prose.
- Prefer self-documenting code over comments.
