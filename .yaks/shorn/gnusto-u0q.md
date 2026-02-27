---
id: gnusto-u0q
title: Global pseudo-objects have invented :examine messages instead of default fallback
type: bug
priority: 2
created: '2026-01-15T15:46:07.921783-05:00'
updated: '2026-02-08T19:07:11.025528Z'
labels:
- LH
---

## Problem
Global pseudo-objects like @dirt, @air, @noise return custom :examine messages in Grue that don't exist in the original ZIL game.

**Grue behavior:**
```
grue> (do @dirt :examine)
[OK: message=Just ordinary dirt and debris.]
```

**dfrotz behavior:**
```
>examine dirt
You see nothing special about the dirt.
```

## Root Cause
During ZIL→Grue conversion, we invented :examine handlers for objects that have NO ACTION handler in ZIL. Objects without handlers should fall through to a default response.

**ZIL pattern:**
- Objects WITH action handler (GROUND-F, SNOW-F, WALL-F): have explicit EXAMINE → custom response
- Objects WITHOUT action handler (DIRT, AIR, NOISE, CORRIDOR): no EXAMINE → default "nothing special"

## Affected Objects (likely incomplete)
- @dirt - invented message, should be default
- @air - invented message, should be default
- @noise - invented message, should be default
- @corridor - has :through/:walk-to but NOT :examine, should be default for examine

## Solution Options
1. Remove invented :examine handlers; implement runtime default for unhandled verbs
2. Replace invented messages with standard default message
3. Add explicit :default behaviors that return (default) for standard fallback
