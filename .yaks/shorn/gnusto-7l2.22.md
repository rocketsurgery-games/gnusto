---
id: gnusto-7l2.22
title: PC login flow missing - verb-level state machine not converted
type: bug
priority: 1
created: '2026-01-13T19:28:24.17891-05:00'
updated: '2026-02-08T19:07:10.969264Z'
labels:
- lh
---

## Problem

The PC login flow is missing from our conversion. After turning on the PC, the menu box appears immediately, but the original game requires:

1. `type 872325412` (login ID) → responds "PASSWORD PLEASE:"
2. `type uhlersoth` (password) → shows menu box with "Edit Classics Paper"

Alternative shortcuts: `xyzzy`/`plugh` also work as login/password.

## Root Cause

This mechanic is implemented as a **verb-level state machine**, not as object behaviors:

1. **Global state variables**: `USERNAME?` and `LOGGED-IN?` track login progress
2. **V-TYPE verb**: Intercepts typing and redirects to `V-LOGIN` or `V-PASSWORD` based on state
3. **V-LOGIN**: Sets `USERNAME?` when valid login entered
4. **V-PASSWORD**: Sets `LOGGED-IN?` and moves `MENU-BOX` to `PC` when valid password entered
5. **CANT-USE-COMPUTER?**: Checks PC is accessible and powered on

The original ZIL code is in:
- `games/lurkinghorror/source/pc.zil` lines 291-347 (V-LOGIN, V-PASSWORD routines)
- `games/lurkinghorror/source/parser.zil` lines 437-463 (LOGIN-ID, PASSWORD-STRING constants)

The reference conversion captured this in `converted/reference/routines.grue` but it was never implemented because our conversion focused on object behaviors, not verb-level mechanics.

## Additional Issues Found During Playtesting

### 1. Menu-box starting location
- **Original**: Menu-box starts in nil/limbo; only moves to PC after successful login
- **Ours**: Menu-box starts in @pc, visible immediately after power-on
- **Fix**: Change `@menu-box :location` from `@pc` to `nil`

### 2. PC examine output after login
- **Original**: "On the screen you see a mouse." (shows first item in PC container)
- **Ours**: Doesn't dynamically show screen contents in examine output
- **ZIL**: `(<FIRST? ,PC> <TELL " On the screen you see " A <FIRST? ,PC> ".">`

### 3. Screen element "take" messages
- **Original**: "You won't get a passing grade for that idea!" (for take menu-box)
- **Ours**: Likely gives generic "can't take" message
- **ZIL**: Custom TRYTAKEBIT handling in object behaviors

### 4. Login state reset
- **Original**: Turning off PC or unplugging it resets USERNAME? and LOGGED-IN? via INIT-PC routine
- **Ours**: No login state to reset, but when implemented need to wire up state clearing

## Lessons for Future Conversions

1. **Verbs can have state machines**: Some mechanics live in verb handlers (V-TYPE, V-LOGIN, V-PASSWORD), not object behaviors. These are easy to miss.

2. **Look for NEW-VERB redirects**: When a verb routine calls `<NEW-VERB ...>`, it's redirecting to another verb based on state. This pattern indicates a multi-step interaction flow.

3. **Check SYNTAX definitions**: The syntax file shows custom verbs like `LOGIN OBJECT` and `PASSWORD OBJECT` that hint at special mechanics.

4. **Global variables as state**: `USERNAME?` and `LOGGED-IN?` are global flags that persist across turns. Object properties are per-object; globals track cross-object state.

5. **Test against the original**: Running `dfrotz` on the compiled game reveals interaction flows that aren't obvious from reading ZIL source alone.

6. **Watch for INIT-* routines**: These often reset state when objects change state (power off, close, etc.).

## Fix Approach

Option A: Add `:login` and `:password` behaviors to PC object with globals tracking state
Option B: Implement as a barrier/interceptor on PC read/click behaviors
Option C: Create a "login-flow" event that tracks state

Recommend Option A as it maps most directly to the original ZIL structure.

Specific fixes needed:
1. Add `logged-in` and `username` globals to pc.grue
2. Move @menu-box starting location to nil
3. Add `:type` behavior that redirects to login/password flow based on state
4. Update `:turn-off` and `:unplug` to reset login state
5. Update `:examine` to show "On the screen you see..." for first item in PC
6. Add custom TRYTAKEBIT messages for screen elements
