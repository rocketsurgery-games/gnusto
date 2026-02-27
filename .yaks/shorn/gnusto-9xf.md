---
id: gnusto-9xf
title: Make The Lurking Horror fully playable
type: task
priority: 2
created: '2026-01-17T14:05:40.989125-05:00'
updated: '2026-02-08T19:07:11.019424Z'
---

Close the gap between the walkthrough test (which uses workarounds) and a fully playable game. The walkthrough-full test in walkthrough.test.grue uses (move!), (set!), etc. in ~15 places where game mechanics aren't working. This epic tracks fixing those gaps.

Categories:
1. Navigation gaps - missing room connections
2. Unimplemented puzzles - forklift, rats, waxer cord, ritual
3. Event/action bugs - professor death, plug action, etc.
4. Item acquisition - axe, boots, note, hand
