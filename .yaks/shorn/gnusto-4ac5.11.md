---
id: gnusto-4ac5.11
title: 'Spike: throwaway webtoon panel mock (experiments/)'
type: task
priority: 2
created: '2026-06-20T15:23:04Z'
updated: '2026-06-20T20:05:15Z'
---

Throwaway, hand-built static HTML/CSS mock to settle panel-stream GEOMETRY and the ESTABLISHING-PANEL look BEFORE refactoring the real Svelte UI (de-risks gnusto-4ac5.1 + .7). Build 2-3 hand-built Lurking Horror scenes using real assets/ art.

Goals:
- Webtoon vertical spine (mobile-first reflow) as the base geometry.
- Establishing panel + scene-break treatment (full-bleed, 'page turn' feel).
- Exercise panel ROLES from the .5 vocabulary: establishing | splash | inset | caption | tier-member.
- Desktop-only multi-panel TIER as progressive enhancement on the vertical spine.
- Player-command CAPTION panels in the stream (.8).
- Typographic FALLBACK: a splash/inset with no art degrades to typographic/caption panel (.6).
- Palette derived from world :visual-style :palette (dark blues / sickly greens) as CSS vars (.9 single-source).
- Lean on the new black-background object art for compositing insets into dark gutters.

NON-goal: no Svelte, no build, no backend wiring — pure static mock for visual iteration. Outcome: screenshots + a written list of concepts/decisions (and anything new it shakes out) to carry into .1/.7. Delete or archive after.

---
▸ 2026-06-20T15:30:16Z
Mock built + iterated (experiments/webtoon-mock/, uncommitted throwaway). Two TLH scenes, all panel roles + both fallbacks, desktop + mobile verified by screenshot. Full findings in that dir's README.md.

CONFIRMED: webtoon vertical spine is a solid responsive base; establishing-as-stream-block works (full-bleed crop + embedded location label/exits + caption overlay, no pinned header needed); scene break needs no state plumbing (CSS air+divider+page-turn); tier = display:contents -> grid@900px (mobile stack / desktop row, zero DOM dup); typographic + caption-inset fallbacks are first-class; palette single-source (~10 vars) is plainly enough.

BIGGEST NEW FINDING (A): there are TWO compositing classes of art, not one. Scene art (rooms) is full-bleed with a baked inked border (don't double-frame). Subject art (objects/characters) is single-subject on an OPAQUE, INCONSISTENT bg — crowbar & hacker are on WHITE despite the 'black backgrounds' commit — so it can't bleed into the gutter. Insets become framed 'specimen plates' (light cream card, object-fit:contain, multiply drops the white field). Robust + reads as an intentional field-notes idiom. Engine must OWN this treatment split, derivable from entity/art kind (room->scene, object->subject). Flagged on gnusto-ntr.

(B) the dark-world / light-pinned-card contrast is functional: the summonable satchel (.2) is just a spread of these specimen plates — inventory question answers itself. (C) display:contents is the tier primitive. (D) command-right / narrator-left gives dialogic rhythm. (E) SFX needs a lettering FONT asset (.9), not just colors.

DECISIONS for .1/.7 captured in README. Keeping this yak shaving pending review; expect possibly a 3rd scene or satchel-spread mock next.
