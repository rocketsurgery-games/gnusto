# Experiments

Throwaway R&D and archived prototypes related to rendering and visual style.
Code here is **not** part of the live system, **not** maintained, and may have
stale imports. The durable design decisions distilled from this work live in
[`../docs/render.md`](../docs/render.md).

| Dir / file | What it is |
|------------|------------|
| [`dynamic-composition/`](dynamic-composition/) | **Archived** runtime scene-composition system (retired). `scene_renderer.py`, `render_cache.py`, and a `README.md` post-mortem of what worked / didn't. Imports are stale (the Grue render API it depended on was simplified). |
| [`composition/`](composition/) | Transparent-overlay & stepwise composition experiments (`overlay.py`) with findings in `REPORT.md` — empty stages, stepwise > single-shot, spatial-text framing. |
| [`layout/`](layout/) | Standalone graphic-novel **layout** prototype (HTML/CSS/JS) plus `compose.py` and Lurking Horror scenarios. Seeded the content-block vocabulary now in the real UI. |
| [`art-sourcing-research.md`](art-sourcing-research.md) | Notes on finding contract artists for hand-drawn reference art. |

## Why these are kept

The dynamic-composition architecture was sound; it was limited by current
image-model capabilities for multi-reference conditioning. We retired it in favor
of a **static** pipeline (single-subject generation + UI-layer composition; see
`../docs/render.md`). These dirs preserve the research so we can revisit the
aspirational dynamic approach if/when models improve, without re-deriving the
findings.
