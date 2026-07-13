---
name: play-grue
description: Play a Grue interactive-fiction game as a natural-language agent and produce a human-readable, player-facing transcript. Use when asked to play through a game, demonstrate that the natural-language parser works reliably, or generate a transcript of a session.
---

# Playing a Grue game naturally

Your job is to play a Grue game the way a curious human would — issuing
**natural-language** intents, reacting to what the game says, making the
occasional mistake, and recovering — and to capture a clean transcript of the
session.

Two things matter:

- **(a) A real transcript.** The output should read like a session a human
  player would see: natural commands in, the game's own authored prose out.
- **(b) A parser demonstration.** The game's parse-only harness turns each
  natural command into concrete engine actions. Phrasing things the way a
  person actually would (not as robotic `go north` primitives) is the point —
  it shows the natural-language interpretation holding up.

This is **unavoidably stochastic**: the interpreter is an LLM, so a phrasing
occasionally lands on the wrong action. That's expected and fine — react and
rephrase, exactly as a player would. Do not try to make it deterministic.

## How the harness reads you

The harness runs a **parse-only sense-act loop**: it maps ONE natural-language
request per turn into one or more engine actions, shows the engine's authored
text, and stops when the request is done or blocked. Play to that grain:

- **Speak in intents, and chain the obvious.** "Force the window open and climb
  inside", "grab the brass lantern and the sword", "pry open the trap door and
  climb down", "open the trophy case and put the painting inside" all work — the
  parser carries out the implied prerequisite steps.
- **It won't pathfind or solve puzzles for you.** One turn is one *local* intent.
  It won't cross the map from a vague "go find the dam" or figure out a puzzle
  from "win the game". Name a direction or an adjacent place ("head north into
  the troll room", "go back south to the cellar"), and drive puzzles yourself
  one intent at a time.
- **Directions are flexible.** Cardines, diagonals, and synonyms all resolve
  (`northeast`≡`ne`, `up`, `in`, "climb up the chimney to the kitchen").
- **Engine-authoritative text.** For these Infocom conversions the engine writes
  all prose; you are only choosing what to *do*, never narrating.

## Playing well (natural, with mistakes)

- Open like a player: read the leaflet, poke at things, try the obvious wrong
  move (the boarded front door) before finding the way around back. A few
  dead-ends make the transcript real and exercise the refusal paths.
- Explore a little off the critical path, then get on with it.
- **Recover agentically.** Read each response. If a command was blocked or did
  something other than you meant, that's information — rephrase more explicitly
  and continue (e.g. "look in the sack" did nothing useful → "open the brown
  sack", then "take the lunch"). Never bang on the identical failing phrasing.
- Watch for **end states**: death (the grue in the dark, an open flame in the
  gas room, going over the falls) and victory end the game — the harness prints
  a banner and refuses further commands until `/reset`.

## Driving the game

**Reproducible transcript (preferred for a deliverable).** Author the session as
a natural-language command file (one intent per line; `#` lines are comments/
section headers) and run the generator:

```bash
python scripts/make_transcript.py games/zork1 \
    -c .agents/skills/play-grue/zork1-first-treasure.txt \
    -o transcript.md
```

It drives the real parse-only harness and writes `> command` followed by the
game's output for each turn — no debug, no invented prose. See
`zork1-first-treasure.txt` for a worked example and
`zork1-sample-transcript.md` for its output.

**Interactive / genuinely reactive play.** Run the game and issue commands
turn by turn, reading each result before deciding the next:

```bash
gnusto games/zork1            # natural-language play; add --debug to see actions
```

Because each `gnusto` process starts fresh, use **`/save <slot>` and `/load
<slot>`** to checkpoint before risky steps and to resume long sessions across
runs (verified to round-trip). `/look`, `/state`, and `/saves` help you orient.

## Walkthrough content

`zork1-walkthrough.md` is a natural-language, spoiler-level guide to Zork I —
region by region, the critical path plus the notable treasures and puzzles,
phrased as intents you can issue more or less verbatim (and vary). Use it as the
spine; improvise the exploration and mistakes around it.

## Adapting to another game

The mechanics above are game-agnostic. For a new Grue game, skim its rooms/
objects (or `frotz map <game>`) for the shape of the world, then write the
walkthrough the same way: natural intents, one local goal per turn, puzzles
driven step by step. Keep the engine-authoritative, no-narration stance.
