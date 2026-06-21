---
id: gnusto-4ac5.2
title: 'Comic-idiom live state: summonable satchel, map, locator'
type: feature
priority: 2
created: '2026-06-16T02:17:45Z'
updated: '2026-06-16T02:17:45Z'
depends_on:
- gnusto-8c77
---

Render the LIVE ground-truth side (what's here / where am I / affordances) in comic idiom, mostly summonable rather than pinned. Lean chrome-less, with small floating affordances when appropriate.

- Inventory -> a summonable 'satchel' comic SPREAD: a page of object panels reusing the movable-object single-subject assets (closes the thumbnail question: yes, but as a page, not a pinned list).
- Map / 'where am I' -> a summonable inked MAP PAGE (restyle auto-map gnusto-8c77 as a drawn map, not a node graph) + an optional minimal floating locator.
- Visible objects / characters present -> light comic-idiom cues, not a traditional tray/strip; keep summon affordances small and unobtrusive.
- Keep only what must be persistent (minimal locator + the command input); everything else is summoned.

Depends on gnusto-4ac5.1 (stream) and gnusto-8c77 (auto-map backbone).

---
▸ 2026-06-20T23:45:00Z
HERD STATUS — this is the ONLY un-shorn child of Epic B; everything else (.1 .3 .4 .5 .6 .7 .8 .9 .10 .11) is shorn. BLOCKED: the defining deliverable (summonable inked MAP PAGE + locator) depends on the auto-map (gnusto-8c77 -> gnusto-6ba8), a separate track not in this herd.
CARVE-OUT OPPORTUNITY (for when we revisit): the three parts split cleanly by dependency —
  (a) SATCHEL — summonable inventory comic SPREAD reusing movable-object assets. INDEPENDENT of 8c77, and now cheap: it can reuse the EntityInset 'specimen plate' from .6 (resolveEntityImage) as the per-item panel. Could be a ready child today.
  (b) MAP PAGE + floating locator — needs 8c77. Stays blocked.
  (c) light object/character presence cues — independent, small.
DEFERRED (design judgement, wants a human): (a)/(c) introduce SUMMON-AFFORDANCE UX choices (where the satchel/map buttons live, the spread layout, how unobtrusive) that the design doc flags as open, and the inventory is empty at game start so a satchel can't be visually validated without play. Held back from the unsupervised plow-through for that reason. Suggest: when revisited, carve (a)+(c) into a ready child and build the satchel on EntityInset; leave (b) blocked on 8c77.

---
▸ 2026-06-21T00:30:00Z
DESIGN DISCUSSION (exits / visible objects / inventory, holistically). Treat them by cadence/scope, NOT as one widget.

SETTLED:
- Inventory -> summonable SATCHEL spread (reuse EntityInset specimen-plate). The easy case.
- ONE unified summon affordance = a "journal": satchel now, map later (map UI deferred to gnusto-8c77). Easy open/select/close.
- CLICK-TO-ACT is cut. No action enumeration (leaks internal/easter-egg verbs, kills immersion; the LLM interprets free text). Only QoL click = PREFILL the object's name / `go <dir>` into the input. => delete the behavior-listing UI (EntityPopover / ObjectDetailOverlay action menus; also clears the stale ObjectDetailOverlay svelte-check warning).
- Exits PERSISTENT; visible objects PERSISTENT (neither should scroll away — both are by-definition "always true now").

PROPOSED MODEL (pending user nod): "THE COLUMN vs THE FRAME". Center column = the narrative comic stream (scrolls/paginates/frozen). Surrounding FRAME (margins/gutter) = persistent, live, engine-owned ground-truth: exits as DIRECTIONAL MARGINALIA around the edges; visible objects as a comic PROPS SHELF along a margin; the room locator. Graphic-novel grammar (gutters/marginalia), not desktop panels. Wins: exits+objects are spatial, never scroll off, never duplicated panel-vs-sidebar, and — key — they are NOT stream blocks, so pagination needs no new constraints.

PAGINATION INTERACTION (worked through): IF objects were woven WHOLLY into the stream, the "current-room objects always on the current page / others excluded" guarantee would force: new-room=>flip (have it), no soft break that splits a room's objects (conflicts with continuation breaks), transitional blocks attach to the incoming room. The FRAME model sidesteps all of that: objects are a live ROOM-SCOPED FIXTURE, so the guarantee is automatic and continuation breaks stay free. Narrative focus/reveal panels (with images) remain ADDITIVE drama, not the guarantee mechanism. ONE refinement to keep regardless: transitional/arrival narration should sit on the INCOMING room's page — i.e. the hard scene break snaps back to the turn's COMMAND boundary (command + bridge + establishing on the new page). Folded into gnusto-4ac5.13 (scene-break authority), not the data model.

OPEN QUESTIONS: (1) buy the full frame, or restyle a single edge strip for objects? (2) history pages show objects/exits as-they-were (per-page snapshot) or live-only (lean live-only)? (3) mobile: thin top/bottom strip vs single summon.

LIKELY RESHAPE of .2 once confirmed: children for (a) satchel [ready, independent], (b) the frame: exits marginalia + visible-objects props shelf [live-only], (c) click->prefill + remove action-enumeration UI. Map page stays under .2 but blocked on 8c77.

---
▸ 2026-06-21T00:55:00Z
SHAVING. User confirmed the column-vs-frame model + decisions (history pages hide ALL frame affordances — show only on the live/most-recent page; add a current-room-name locator we currently lack; keep mobile simple for now; delete the old action-menu code). Carved the BLOCKED map page to gnusto-4ac5.2.1 (depends 8c77) so .2 covers the READY parts. Build order in slices:
  SLICE 1 (this) — click->prefill + delete the action-menu experiment.
  SLICE 2 — summonable journal: satchel spread (map tab deferred to .2.1).
  SLICE 3 — the frame: exits marginalia + visible-objects props shelf + room-name locator; visible only on the live page.

SLICE 1 done (pending commit): clicking any entity now just PREFILLS its name into the input (handleEntityClick -> inputPrefill = resolveEntityName; reuses the existing InputBar prefill effect) — no action enumeration. Deleted EntityPopover.svelte, ObjectDetailOverlay.svelte, lib/commands.ts (behavior->command helpers), and the verb-TARGETING flow (enter/complete/cancelTargeting, targeting state + body class, InputBar targetingPrompt/cancel UI). Trimmed the dead behavior store from entities.svelte (updateBehaviors/resolveEntityBehaviors/entityBehaviors) and the dead targeting CSS from global.css. Net: svelte-check 0 errors / 0 warnings (the long-standing ObjectDetailOverlay 'entityId unused' error is gone with the file), build OK, bundle shrank. NOTE: couldn't visual-smoke (local servers were stopped); the prefill path is the pre-existing mechanism, just repointed.

---
▸ 2026-06-21T01:10:00Z
SLICE 2 done (satchel). New SatchelOverlay.svelte: the summonable inventory as a comic SPREAD of EntityInset specimen plates (reuses the .6 primitive; art when available, name-card fallback otherwise), empty-state caption when carrying nothing. Clicking an item prefills its name and closes (slice-1 convention). Opened via a persistent "journal" FAB (small inked stamp, bottom-left, carried-count badge) — the unified journal affordance; the MAP joins as a tab once gnusto-4ac5.2.1 lands. Wired into App's overlay chain (activeOverlay='satchel'), items = currentRoom.inventory. Verified: svelte-check 0/0, build OK. NOTE: no visual smoke (local servers down; inventory is empty at start anyway) — populated spread to be eyeballed on next run. The FAB is always-visible for now; slice 3 gates frame/affordance visibility to the live page.
