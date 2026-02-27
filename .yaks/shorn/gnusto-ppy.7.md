---
id: gnusto-ppy.7
title: Design turn-based event handler system
type: task
priority: 3
created: '2026-01-11T10:17:19.900027-05:00'
updated: '2026-02-08T19:07:11.07662Z'
depends_on:
- gnusto-ppy.5
---

Design and implement turn-by-turn event handlers for GRUE.

## Background
ZIL uses interrupt routines (I-*) that run each turn when queued. These handle:
- Multi-stage cutscenes (I-HACKER-HELPS: 4-stage sequence)
- Progressive effects (I-COMPULSION: escalating horror, then teleport)
- Resource depletion (I-LANTERN: countdown with warning messages)

## Analysis from Lurking Horror

### I-HACKER-HELPS Pattern
```
Turn 1: Hacker walks over, takes chair, examines terminal
Turn 2: Hacker types furiously, windows pop up
Turn 3: Hacker explains problem, mentions Alchemy/Lovecraft clue
Turn 4: Hacker returns to his seat, event dequeues
```
Each stage: state changes + narrative context for LLM

### I-COMPULSION Pattern
```
Turns 1-N: Print increasingly disturbing paper descriptions
Turn N+1: Player faints, teleported to YUGGOTH, inventory stolen
```
Countdown with major state change at end

### I-LANTERN Pattern (Zork)
```
At turn 200: "Your lamp is getting dim"
At turn 220: "Your lamp is quite dim"
At turn 240: Lamp goes out (clear ONBIT)
```
Table-driven warnings + final state change

## Design Questions

### 1. Representation
Options:
a) Staged event definitions:
```scheme
(event HACKER-HELPS
  :stage 1 :effects (...) :context (...)
  :stage 2 :effects (...) :context (...)
  :final :effects (...) :then (dequeue! HACKER-HELPS))
```

b) Single handler with stage property:
```scheme
(event HACKER-HELPS
  :each-turn (cond
    ((= (prop QUEUE hacker-helps-stage) 1) ...)
    ((= (prop QUEUE hacker-helps-stage) 2) ...)
    ...))
```

c) Behavior on special EVENTS object

### 2. Turn Processing
- When does the runtime process events? Start of turn? End?
- How do event effects interact with action effects?
- Can events be interrupted mid-sequence?

### 3. Narrative Integration
- Events print text in ZIL - in GRUE, LLM generates narrative
- Need rich context for LLM to know what happened
- Stage-specific context hints

### 4. Countdown Tables
- I-LANTERN uses table of (turns, message) pairs
- Could model as property list on event
- Or as stages with turn-count triggers

## Dependencies
- Requires basic queue flags (frotzlm-ppy.5) first
- May need runtime turn-processing hooks

## Priority
P3 - Not needed for basic terminal-room conversion, but required for full game.
