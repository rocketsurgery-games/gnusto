---
id: gnusto-4ac5.4
title: Bounded comic pages + paged navigation
type: feature
priority: 2
created: '2026-06-16T02:18:06Z'
updated: '2026-06-20T14:53:09Z'
depends_on:
- gnusto-4ac5.1
---

Solve infinite-scroll: bound the stream into navigable comic PAGES that are a VIEW over the existing turn history (no new store).

- Page = a bounded set of panels: target a panel budget per page, but SNAP breaks to natural boundaries (room change first, then turn boundary). An establishing panel always starts a page; overflow within a long room-stay spills to continuation pages.
- Navigation: paged, not infinite scroll. Default = latest page ('now'); page BACKWARD through history; page FORWARD to return to now. (Your 'N before/after' = previous/next page.)
- Back the pages with the persisted turn history (knowledge graph / journal, gnusto-dae1) — pagination is rendering logic, not a parallel data model.
- Perf: mount only current page +/- neighbors; frozen panels render identically on every revisit.
- Open question to settle during impl: does the current room accrete panels into one LIVE page until a scene break commits it (leaning yes), vs every turn committing a page?

Depends on gnusto-4ac5.1.

---
▸ 2026-06-20T14:53:09Z
DESIGN EXPLORATION (page-break determination). Key reframe: pagination is a NON-DESTRUCTIVE VIEW over the fully-persisted turn log — a break never drops content (unlike the old header-swap that discarded bridging narration and needed the _build_preamble salvage hack). Invariant: a break only chooses where to draw a chunk line over an already-continuous stream. Consequence: a wrong break is UGLY, not BROKEN — it is a pacing choice, not a correctness one. So start simple/programmatic, add smarter authority only if it looks bad.

TWO KINDS OF BREAK:
- SCENE break (hard): opens a fresh ESTABLISHING panel + scene-break styling. The 'new room / new beat' cut. This is where judgment lives.
- CONTINUATION break (soft): same scene spilling over the panel budget; NO establishing panel, subtle 'cont.' treatment. Purely programmatic (budget + snap). This is the 'break within a room' case — deterministic, low-stakes.

WHO DECIDES THE HARD (SCENE) BREAK — layered, deterministic-first fallback chain:
1. Programmatic baseline: room change is a CANDIDATE. But room-change != scene-change leaks BOTH ways (contiguous spaces should not break; cutscenes/flashbacks/reveals should break with NO room change). Insufficient alone.
2. Grue (success ...) hints: author authority for set-pieces. Rides the existing _parse_terminator_kwargs -> context['render'] channel (eaec/ntr); add :scene/:beat plus a SUPPRESS form for contiguous moves. Author already knows the alchemy ritual is a scene; should not depend on the LLM noticing. (Language side tracked on gnusto-ntr.)
3. LLM intent (optional/later, part of 4ac5.5 vocab): may PROMOTE a soft boundary to hard or add emphasis, but must NEVER be sole owner — else pagination stops being deterministically re-derivable from the persisted log (revisits could re-paginate) and we pay tokens every turn.

Programmatic refinement to try BEFORE reaching for the LLM: declared room REGIONS/ZONES in Grue (intra-zone moves don't break). Captures 'contiguous space' with zero per-turn authoring, no LLM. gnusto-ntr territory; dovetails with the room-global-axes note.

SNAPPING RULES (keep breaks off mid-beat): budget is a SOFT trigger with hysteresis — honor at next turn boundary after overflow, snap to nearest STRONG panel (establishing/reveal/splash), never mid-inset; NEVER break inside a bound tier/group (atomic for pagination).

LEAN: ship .1/.7 as a single unbounded live stream; implement .4 with programmatic candidates (room change + budget/snap) + Grue scene hints; DEFER LLM-promotion until proven necessary. Authority stays with engine + author; LLM is an optional later signal.

---
▸ 2026-06-20T23:35:00Z
SHORN (LEAN client-side slice). Bounded comic PAGES now sit over the panel stream. Implemented exactly the design note's lean path: programmatic candidates only (room-change + budget/snap), Grue scene hints + LLM promotion deferred.
- lib/pagination.ts: pure paginate(blocks, budget=8) -> Page[]. SCENE break (hard): a room_enter always opens a fresh page. CONTINUATION break (soft): once a same-scene page exceeds the budget, snap to the next TURN boundary (a `command` caption) — never mid-beat; tiers stay atomic for free (tier members are never command/room_enter). Non-destructive view: deterministically re-derivable from the stream order, a break never drops content (a wrong break is UGLY not BROKEN — pacing, not correctness).
- PagedStream.svelte: shows ONE page; pageIndex=null = LIVE/follow (tracks the latest page + new panels), paging back pins until "Now". Slim sticky pager (chrome-less): ‹ Older / position (+ 'cont.' on continuation pages) / ● live | Newer › + Now ⤓. FAIL-SAFE: degenerate pagination falls back to the full unbounded stream, never blank.
- NarrativeStream: added autoscroll prop (false on history pages so the viewport isn't yanked to the page foot); PagedStream scrolls to top on back-nav.
- App.svelte: PagedStream replaces NarrativeStream (blocks array unchanged).
LIVE-VERIFIED on the :8000 server against lurkinghorror: initial load paginates to Page 2/2 — prologue narration = page 1, room establishing = live page 2 (a nice intro/now split; prologue preserved, reachable via Older). Older/Newer/Now + live indicator all work; no console errors from our code. (One transient /game/theme.css 404 is just the still-running OLD backend lacking the .9 route — gone on server restart; the <link> degrades harmlessly regardless.) svelte-check clean on touched files, vite build OK.
DEFERRED (noted): (1) back pages by the PERSISTED turn log (gnusto-dae1 journal) instead of the in-memory array — same pagination logic, swap the source; the lean note explicitly endorsed shipping the in-memory version first. (2) mount current ± neighbor pages (perf only matters once log-backed; in-memory renders one page cheaply). (3) Grue (success :scene/:beat ...) hard-break hints + region/zone suppression (gnusto-ntr) and optional LLM promotion — the authority chain's later tiers.
