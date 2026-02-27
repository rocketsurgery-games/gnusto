---
id: gnusto-7l2.30
title: Use match for multi-condition dispatch in pc.grue
type: task
priority: 2
created: '2026-01-14T14:12:03.300218-05:00'
updated: '2026-02-08T19:07:11.026862Z'
labels:
- lh
---

pc.grue :examine (lines 22-44) has a long cond chain checking for screen objects:

```scheme
:examine (fn ()
  (cond
    ((not (has-flag ?self POWER))
      (success :context ((power off)) ...))
    ((in? @odd-paper ?self)
      (success :context ((power on) (screen-contents @odd-paper)) ...))
    ((in? @menu-box ?self)
      (success :context ((power on) (screen-contents @menu-box)) ...))
    ((in? @more-box ?self)
      (success :context ((power on) (screen-contents @more-box)) ...))
    ((in? @yak-window ?self)
      (success :context ((power on) (screen-contents @yak-window)) ...))
    (true
      (success :context ((power on)) ...))))
```

Could use a helper to find first screen object:
```scheme
(def screen-objects '(@odd-paper @menu-box @more-box @yak-window))

(defn current-screen-content ()
  (first (filter (fn (?o) (in? ?o @pc)) screen-objects)))
```

Then simplify the cond. Similar patterns in :read behavior.
