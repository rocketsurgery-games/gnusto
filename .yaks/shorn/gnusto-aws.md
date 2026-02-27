---
id: gnusto-aws
title: Make blocked/success/default into forms
type: task
priority: 1
created: '2026-01-11T01:37:05.550375-05:00'
updated: '2026-02-08T19:07:10.974559Z'
---

Change outcome specification from keyword values to actual forms.

Before:
```lisp
(case true
  :outcome success
  :effects ((move! self ?actor))
  :context ((message "Taken.")))
```

After:
```lisp
(true
  (success :effects ((move! self ?actor)) :message "Taken."))
```

Benefits:
- Cleaner syntax
- outcome type is now the form head, not a keyword value
- Easier to validate at parse time
