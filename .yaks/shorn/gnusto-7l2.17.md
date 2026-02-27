---
id: gnusto-7l2.17
title: Kitchen & Microwave (food puzzle)
type: task
priority: 2
created: '2026-01-13T10:17:58.697273-05:00'
updated: '2026-02-08T19:07:11.034304Z'
labels:
- lh
---

Convert the kitchen room and microwave from hacker.zil. This completes the food puzzle needed to trade with the hacker for the master key.

## Objects
- Kitchen room
- Microwave (container, open/close, timer event)
- Controls (number buttons, WM/LO/MED/HI, START/STOP/CLEAR)
- LED readout/display
- Refrigerator (contains chinese food carton)
- Kitchen counter (surface)

## Mechanics
- Microwave timer counts down each turn when running
- Temperature settings affect heating rate
- Items heat up while in running microwave
- Items cool down over time when not being heated
- Chinese food needs heat >= 12 but < 20 (overcooked)
- Opening door stops microwave (safety interlock)

## Dependencies
- hacker.grue already has trade logic expecting @chinese-food heat property
