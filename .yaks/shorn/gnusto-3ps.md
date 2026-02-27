---
id: gnusto-3ps
title: Require explicit player entity in (world) form
type: task
priority: 2
created: '2026-01-11T12:40:49.042141-05:00'
updated: '2026-02-08T19:07:11.053193Z'
depends_on:
- gnusto-b1f
---

Currently the runtime finds the player entity by looking for an object with the PERSON flag:

```python
def _find_player_name(self) -> str:
    for name, obj in self.state.objects.items():
        if "PERSON" in obj.flags and name not in self.state.rooms:
            return name
    return "PLAYER"  # Fallback
```

This is fragile - what if there are multiple PERSON objects (NPCs)?

Instead, require the world form to explicitly declare the player:

```lisp
(world
  :name "The Lurking Horror"
  :player @player)
```

Benefits:
- Explicit is better than implicit
- No ambiguity with NPCs that also have PERSON flag
- Clearer error messages if player not defined
- Parser can validate player entity exists

Implementation:
1. Add `:player` keyword to world form parsing in parser.py
2. Store `GrueWorld.player` attribute
3. Update runtime to use `self.world.player` instead of `_find_player_name()`
4. Update converter to emit `:player @player` in world form
5. Update existing .grue files
