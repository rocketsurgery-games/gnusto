---
id: gnusto-hmp
title: Implement :on-enter room hook
type: task
priority: 1
created: '2026-01-12T12:02:22.588603-05:00'
updated: '2026-02-08T19:07:10.972898Z'
---

Add support for :on-enter hooks on rooms, triggered when the player enters a room.

## Use Case
- Terminal room needs to detect entry from @platform-room (nightmare wake-up)
- Queue hacker-helps event and display wake-up message

## Design
Room behaviors can include:
```
:on-enter (fn (?from-room)
  (cond
    ((= ?from-room @platform-room)
      (success
        :effects ((queue! hacker-helps))
        :message "awakened by the thump of your head"))))
```

## Implementation
- Add :on-enter to room behavior parsing
- Call :on-enter hook in runtime after successful movement
- Pass previous room as parameter
