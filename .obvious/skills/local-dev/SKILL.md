---
name: local-dev
description: How to get the Gnusto dev environment running locally — proven end-to-end during onboarding (2026-10-01)
---

# Local Dev — Gnusto

## One-time setup

1. Install **uv** (`pip install uv`). The sandbox snapshot already ships uv 0.12.21 and a
   ready `.venv`, so this is only needed from a fresh clone.
2. `uv sync` — creates `.venv` with Python 3.11.13 (from `.python-version`; uv downloads it
   if missing) and installs everything from `uv.lock`. Fast (~5s warm, <2min cold).
3. Web UI: `cd src/gnusto/webui && npm ci && npm run build`. The Python backend serves
   `src/gnusto/webui/dist/`; without a build, `GET /` returns
   `{"error": "Web UI not built. Run: cd src/gnusto/webui && npm run build"}`.

## Run the app

- Canonical (web): `uv run python -m gnusto games/lurkinghorror/ --web --host 127.0.0.1 --port 8000`
  (`serve.json` uses `--host 0.0.0.0 --port 8000`).
- Port comes from `--port` (default 8000), host from `--host` (default 127.0.0.1). Confirm
  from startup output: "Open http://127.0.0.1:8000 in your browser".
- Web UI hot-reload during frontend work: `npm run dev` in `src/gnusto/webui/` (Vite
  proxies to the Python backend).
- Terminal UI: `uv run gnusto games/lurkinghorror/`.

## Verify

- `uv run python -m pytest tests/` — 855 passed, 6 skipped at onboarding time.
- `uv run grue-test games/lurkinghorror/ -q` — 480 passed. Other suites:
  `games/testgame/` (fixture), `games/lurkinghorror/` (lead conversion).
- `cd src/gnusto/webui && npm run check` — svelte-check, 0 errors.

## Primary user flow (proven 2026-10-01)

1. `GET /` → 200, Gnusto HTML (built webui).
2. Connect WS `/ws` → server pushes `theme`, `scene_context`, `blocks`, `turn_complete`.
3. Send `{"type":"command","text":"/help"}` → system block + `turn_complete`
   (slash commands are handled locally, no LLM). `/save smoke-test` also works keyless.
4. Send `{"type":"get-state"}` → `state-context` debug dump.
5. Headless Chromium loads the page, WS connects ("Connected to game server"), no console
   errors. Screenshots: `/tmp/gnusto_webui_initial.png`, `/tmp/gnusto_webui_help.png`.

## Gotchas

- **LLM credentials:** non-slash commands go through litellm and need a real LLM key
  (default `anthropic/claude-sonnet-4-5-20250929`; override with `GRUE_LLM_MODEL` /
  `GRUE_LLM_API_BASE`). UI, engine, slash commands, and all tests run without any key —
  don't assume the stack is broken when a natural-language turn fails with an auth error.
- `--model local` (MLX) expects an OpenAI-compatible server at `localhost:8800/v1`;
  `OPENAI_API_KEY=not-needed` is auto-set for it.
- `filfre` needs `GEMINI_API_KEY` (or `GOOGLE_API_KEY`) and the optional extra:
  `uv sync --extra render`.
- No lock files to clean before starting the server; no Docker/Compose services.
- For screenshots in this sandbox: system `pip install playwright` +
  `python -m playwright install --with-deps chromium-headless-shell` (already baked into the snapshot).
