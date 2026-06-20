---
id: gnusto-ntr.23
title: :visual-style :swatches — structured palette swatches (single source for art
  + chrome)
type: feature
priority: 2
created: '2026-06-20T20:39:44Z'
updated: '2026-06-20T20:45:13Z'
---

Add an optional :swatches keyword-map (token -> hex) to (world :visual-style), so the game's color identity is declared ONCE and both the generated art (filfre brief) and the web chrome (CSS --game-* vars) derive from it — they can't drift. :prompt/:palette prose stay as stylistic guidance. Parsing: nested keyword-map needs explicit handling in _parse_world (generic parse_properties/sexpr_to_value flattens nested maps to lists). Backend injects swatches as CSS vars via a websocket 'theme' message; filfre appends the hexes to the style preamble. Powers the gnusto-4ac5.9 palette-single-source goal. NOTE (generalization opportunity): nested keyword-maps not parsing as dicts in parse_properties is a broader language gap — handled locally here; revisit generalizing parse_properties (carefully, ntr.22 keyword/string semantics are sensitive).

---
▸ 2026-06-20T20:45:13Z
SHORN. Added :visual-style :swatches (nested keyword-map token->hex). Parser: _parse_world parses swatches as a dict explicitly (generic parse_properties flattens nested maps to lists). filfre: assemble_style appends 'Anchor the palette to these colors: <hexes>' so art is keyed to the same swatches. Backend: send_initial_state emits a 'theme' websocket message with the swatches. Frontend: App.svelte applyTheme sets --game-<token> on :root; tokens.css derives all semantic tokens from --game-*. TLH: added :swatches to lurkinghorror.grue. Tests: swatches parse-as-dict + assemble_style anchoring (tests/grue/test_render.py). Docs: grue.md + render.md. Verified end-to-end via server smoke (inline --game-* props confirmed set from the theme message). 734 pytest pass. NOTE: nested-keyword-map-as-dict remains a local handling; generalizing parse_properties is still an open ntr idea (kept on the gnusto-ntr note).
