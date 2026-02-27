---
id: gnusto-6iq
title: LOOK shows vehicle instead of room when player is inside
type: bug
priority: 1
created: '2026-01-15T22:36:20.448574-05:00'
updated: '2026-02-08T19:07:10.964233Z'
---

When the player is inside a vehicle (e.g., sitting in a chair), (look) shows the vehicle as the location instead of the containing room. Three methods use get_player_location() instead of get_player_room(): repl.py:_make_location_result(), runtime.py:get_room_description(), runtime.py:get_exits(). See ZIL desc.zil:13-24 for reference implementation.
