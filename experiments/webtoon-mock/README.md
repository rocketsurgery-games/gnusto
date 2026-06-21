# Webtoon panel-stream mock (throwaway)

Spike for **gnusto-4ac5.11**, de-risking the real refactor (`gnusto-4ac5.1` un-pin +
`gnusto-4ac5.7` geometry). Hand-built static `index.html` — no Svelte, no build, no
backend. Two Lurking Horror scenes using real `assets/` art. Open `index.html` in a
browser; press `r` to toggle the role annotations.

`_shot-desktop.png` / `_shot-mobile.png` are reference captures. This whole dir is
disposable once the findings land in `.1`/`.7`.

## What it exercises

Panel roles (the `.5` vocabulary), rendered as pure CSS classes:
establishing · splash · inset · caption · command · speak · sfx · tier-member,
plus both **fallbacks** (`.6`): typographic splash (no art) and caption-inset (missing art).
Webtoon vertical spine (`.7`) mobile-first; desktop-only tier; scene break (`.3`);
command captions (`.8`); palette from a single source (`.9`).

## Confirmed / working

1. **Webtoon vertical spine is a solid responsive base.** Bounded centered column
   (~760px) on desktop, clean mobile-first single-column reflow. No surprises.
2. **Establishing-as-stream-block works** — full-bleed cinematic crop with the location
   label + edge exit hotspots embedded (chrome-less nav) and an optional narrator caption
   overlaying the foot. It needs no pinned header; it can just enter the stream. This is
   the core `.1` bet, and it holds.
3. **Scene break needs no state plumbing.** Extra air + a divider + a soft "page-turn"
   fold-shadow reads as a beat change purely in CSS — supports deleting the transition
   machinery (`.3`).
4. **Tier is a clean progressive enhancement.** A `.tier` wrapper is `display:contents`
   by default (children just flow in the spine = mobile stack) and becomes a CSS grid at
   ≥900px (= desktop row). Zero DOM duplication. The LLM groups blocks; the engine decides
   row-vs-stack. Validates the `.5`/`.7` boundary.
5. **Fallbacks are first-class, not failure states.** The typographic splash ("THE FLOOR
   SHIFTS / SOMETHING BENEATH IS AWAKE") is genuinely dramatic; the caption-inset reads
   fine. `.6` is sound.
6. **Palette single-source is plainly enough.** ~10 CSS vars carry the entire look;
   deriving them from `world :visual-style :palette` (`.9`) is clearly sufficient.

## New concepts the spike shook out

### A. There are TWO compositing classes of art, not one  ← biggest finding
- **Scene art** (rooms / establishing / splash): authored edge-to-edge, already carries a
  baked inked border. Treat **full-bleed**, frame with shadow/outline — do **not**
  double-border it.
- **Subject art** (objects / characters): single-subject on an **opaque, inconsistent**
  background. Despite the recent "black backgrounds" commit, `crowbar` and `hacker` are on
  **white**. Subject art **cannot bleed into the dark gutter**.

  → Insets become framed **"specimen plates"**: a light cream card, `object-fit:contain`,
  `mix-blend-mode:multiply` to drop the white field while keeping the inked subject. This
  is **robust to whatever background the art happens to have** and reads as a deliberate
  field-notes idiom.

  **Implication for the engine:** full-bleed-vs-plate is an engine-owned treatment that
  must be derivable from the art, not guessed per-panel. Cleanest signal is the entity
  *kind* (room → scene/full-bleed; object/character → subject/plate), possibly surfaced as
  a render-kind hint on `:render`. → worth a `gnusto-ntr` / render-manifest note.

### B. Light-on-dark is doing narrative work
The dark immersive world (full-bleed scenes) vs. light "pinned cards" (examined objects)
creates a **dossier / scrapbook** texture that is both attractive and *functional*: live
ground-truth (what you examine and carry) literally looks like artifacts pinned over the
world. This is a gift to `.2` — **the summonable "satchel" is just a spread of these
specimen plates**, which already exist. The inventory question answers itself.

### C. `display:contents` is the tier primitive
Confirmed: the same markup is a mobile stack or a desktop row with no duplication, so the
LLM's "group into a tier" stays a pure semantic wrapper the engine reflows.

### D. Dialogic rhythm from caption alignment
Command captions right-aligned ("you" voice) against left-aligned narrator captions gives
the strip a subtle call-and-response cadence for free (`.8`).

### E. SFX wants a real display font
The onomatopoeia lettering carries the theme but needs a lettering font asset, not just a
weight — confirms the `.5` SFX block + a `.9` theme font (not only colors).

## Decisions to carry into .1 / .7

- **`.1` establishing panel:** full-bleed, cinematic crop (~5:4), shadow-framed (never
  double-bordered), location label + edge exits + optional caption overlay; emitted as an
  ordinary stream block.
- **`.7` spine:** bounded centered column; mobile-first stack; `.tier` via
  `display:contents` → grid at ≥900px; a small set of **per-role × context width tokens**
  (inset-in-spine vs inset-in-tier differ).
- **Treatment split (A)** is engine-owned and should be derived from entity/art kind, not
  authored per panel. Flag a follow-up to tag render assets scene-vs-subject.

## Known rough edges (cosmetic, not blocking)
- Mobile tier-member insets are left-aligned at 56% width — want centering or a per-context
  width token.
- The fixed command dock overlaps stream content in full-page screenshots (capture
  artifact only; fine in a real scrolling viewport).
