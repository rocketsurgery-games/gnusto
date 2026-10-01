# Gnusto — Obvious Agent Guide

LLM-powered interactive fiction research project: keep a formal, analyzable world model
(the **Grue** language) at the center of a text adventure; the LLM only parses player
input and narrates results. Single-developer codebase — prefer hard cutovers to
migrations (see `AGENTS.md`).

## Stack

- **Python** >=3.11, pinned `3.11.13` (`.python-version`); dependency manager **uv** (`uv.lock`)
- **Backend/API:** FastAPI + uvicorn (`src/gnusto/web.py`); the game runs over WebSocket `/ws`
- **Web UI:** Svelte 5 + Vite 7 + TypeScript (`src/gnusto/webui/`), built output served by the backend
- **LLM:** litellm, default model `anthropic/claude-sonnet-4-5-20250929`
- **Tests:** pytest (Python) + `grue-test` (Grue-native game suites)
- No Docker/Compose, no database or cache services. Only external services are LLM APIs.

## Commands

| What | Command |
|---|---|
| Install deps | `uv sync` (creates `.venv` with Python 3.11.13) |
| Web UI deps | `cd src/gnusto/webui && npm ci` |
| Python tests | `uv run python -m pytest tests/` |
| Grue game tests | `uv run grue-test games/lurkinghorror/ -v` (`-q` for quiet) |
| Static analysis | `uv run frotz analyze games/testgame --walkthrough`; `uv run frotz reach --to "@key@player" games/testgame` |
| Web UI typecheck | `cd src/gnusto/webui && npm run check` (svelte-check) |
| Web UI build | `cd src/gnusto/webui && npm run build` → `src/gnusto/webui/dist/` |
| Web UI hot reload | `cd src/gnusto/webui && npm run dev` (Vite proxies to the Python backend) |
| Run app (web) | `uv run python -m gnusto games/lurkinghorror/ --web --host 127.0.0.1 --port 8000` |
| Run app (terminal) | `uv run gnusto games/lurkinghorror/` |
| REPL (no LLM) | `uv run grue-repl games/testgame/` |
| ZIL converter | `uv run zilch <zil-dir>/ -d out/` |

Canonical serve command (from `serve.json`):
`uv run python -m gnusto games/lurkinghorror/ --web --host 0.0.0.0 --port 8000`
— serves the built web UI on port **8000** (`--port`, default 8000; `--host`, default 127.0.0.1).
The backend serves `src/gnusto/webui/dist/`; without a build, `GET /` returns a JSON "Web UI not built" error.

## Environment variables

| Var | Required | Purpose |
|---|---|---|
| `GRUE_LLM_MODEL` | no | litellm model ID (default `anthropic/claude-sonnet-4-5-20250929`) |
| `GRUE_LLM_TEMPERATURE` / `GRUE_LLM_MAX_TOKENS` | no | generation knobs |
| `GRUE_LLM_API_BASE` | no | OpenAI-compatible endpoint for local/custom models |
| `OPENAI_API_KEY` | no | dummy value OK when `GRUE_LLM_API_BASE` is set (auto-set to `not-needed`) |
| `ANTHROPIC_OAUTH_TOKEN` | no | alternative Anthropic auth (`sk-ant-oat…`) |
| `GEMINI_API_KEY` / `GOOGLE_API_KEY` | no | `filfre` image generation only (extra: `uv sync --extra render`) |

No `.env` file is needed to build, test, or serve. Natural-language gameplay turns
require real LLM credentials (Anthropic key via litellm); everything else — web UI,
engine, slash commands, full test suite — runs without any API key.

## Codebase map

See [codebase-map.md](codebase-map.md).

## Local verification (proven during onboarding, 2026-10-01)

- `uv run python -m pytest tests/` → **855 passed, 6 skipped**
- `uv run grue-test games/lurkinghorror/ -q` → **480 passed**
- `npm run check` → **0 errors, 0 warnings**; `npm run build` → success
- Web app up on port 8000; primary flow verified end-to-end over WebSocket
  (initial state, `/help`, `/save`, `get-state`) and in headless Chromium
  (screenshots at `/tmp/gnusto_webui_initial.png`, `/tmp/gnusto_webui_help.png`;
  browser console clean, no page errors)

## Sandbox snapshot

- **snapshotId:** `td13uq4qbxqksaw5h6bl:default`
- **Captured:** 2026-10-01T20:48:47.125Z
- State baked in: uv with Python 3.11.13 `.venv`, webui `node_modules` + `dist` build,
  Gnusto web server running on port 8000 (tmux session `gnusto`, log `/tmp/gnusto-web.log`)

## Conventions

- Read `AGENTS.md` before working here. Key rules: keep all side effects in the formal
  effects system and keep `src/frotz/effects.py` in sync with `EffectInterpreter.MUTATIONS`
  in `src/grue/expr.py` (enforced by `tests/frotz/test_effects_completeness.py`);
  LISP/Clojure-faithful truthiness; declare every property you touch (`frotz lint <game>`);
  update `docs/*.md` when changing language or behavior.
- Task tracking via **Yaks** (`.yaks/`): shave a yak before coding, shear it right after committing.
- ZIL→Grue conversion conventions: `.agents/skills/translate-zil/SKILL.md` and `games/notes.md`.
