---
id: gnusto-4ac5.13
title: Smarter scene-break authority (Grue scene hints + optional LLM promotion)
type: feature
priority: 3
created: '2026-06-21T00:10:00Z'
updated: '2026-06-21T00:10:00Z'
---

Follow-on from gnusto-4ac5.4. The shipped pagination uses PROGRAMMATIC candidates
only: a room_enter is a hard scene break; budget+turn-boundary is a soft
continuation break. The .4 design note lays out a layered, deterministic-first
authority chain whose later tiers are deferred:

1. (DONE) Programmatic baseline — room change + budget/snap.
2. Grue (success ...) SCENE HINTS: author authority for set-pieces. Rides the
   existing _parse_terminator_kwargs -> context['render'] channel (eaec/ntr);
   add :scene / :beat plus a SUPPRESS form for contiguous moves (so the alchemy
   ritual breaks as a scene without the LLM noticing, and adjacent spaces don't
   wrongly break). Language side tracked on gnusto-ntr.
3. Optional LLM PROMOTION (part of the .5 vocab): may promote a soft boundary to
   hard or add emphasis, but NEVER sole owner — else pages stop being
   deterministically re-derivable from the log and we pay tokens every turn.

Also worth trying BEFORE the LLM: declared room REGIONS/ZONES in Grue (intra-zone
moves don't break) — captures "contiguous space" with zero per-turn authoring
(gnusto-ntr territory; dovetails with the room-global-axes note).

Constraint throughout: a wrong break is UGLY, not BROKEN (pacing, not
correctness), so only add authority that visibly improves pacing.
