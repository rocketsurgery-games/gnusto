# Gnusto — Codebase Map

Folder-level overview (depth cap 2). Entry points: `src/gnusto/__main__.py` (player CLI),
`src/grue/repl.py`, `src/grue/test.py`, `src/frotz/cli.py`, `src/filfre/cli.py`.

| Path | What lives there |
|---|---|
| `src/grue/` | The Grue language: parser, runtime, effects system (`expr.py`), stdlib (`builtins.grue`), lint, save, render, map graph, ZIL converter |
| `src/gnusto/` | The LLM player: agent loop, litellm interface (`llm.py`), state/knowledge tracking, Rich TUI, FastAPI web backend (`web.py`) |
| `src/gnusto/webui/` | Svelte 5 + Vite web UI (source + config; built to `dist/`, which the backend serves) |
| `src/gnusto/webui/src/` | UI source: `App.svelte`, `components/` (narrative blocks, sidebar, input bar, overlays) |
| `src/frotz/` | Static analysis over the effects system: reachability, winnability, differential testing, CLI |
| `src/filfre/` | Scene illustration CLI (NanoBanana / Gemini 2.5 Flash Image) |
| `src/zil/` | ZIL tokenizer/parser/AST/loader/extractor for the conversion pipeline |
| `games/` | Game worlds: `lurkinghorror/` (lead conversion), `testgame/` (test fixture), `zork1/`, `enchanter/`, `amfv/`, `bureaucracy/` (staged) |
| `docs/` | Language reference and tool docs: `grue.md`, `grue_notes.md`, `gnusto.md`, `frotz.md`, `filfre.md`, `render.md`, `ui.md` |
| `experiments/` | Archived art/composition/layout R&D and art-sourcing research |
| `scripts/` | `make_transcript.py` (play a game, produce a human-readable transcript) |
| `tests/` | pytest suites mirroring `src/` (`grue/`, `gnusto/`, `frotz/`, `zil/`, `filfre/`) + `test_walkthrough.py` |
| `.agents/skills/` | Project skills: `translate-zil`, `grue-testing`, `play-grue` |
| `.yaks/` | Yaks task-tracker data (hairy/shaving/shorn) |
| `.sightmap/` | Sightmap UI component map for the web UI (selectors, views, WS route) |
