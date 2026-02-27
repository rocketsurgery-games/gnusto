---
id: gnusto-ntr.4
title: Add test-group form for shared setup
type: task
priority: 2
created: '2026-01-13T13:13:48.940117-05:00'
updated: '2026-02-08T19:07:11.03362Z'
labels:
- lang
---

Add test-group to the test DSL for grouping tests with shared setup.

Pattern:
```scheme
(test-group "microwave timer"
  :setup ((move! @player @kitchen))

  (test "set to 2 minutes"
    :action (do @microwave :set-timer 120)
    :expect ((global? microwave-timer 120)))

  (test "set to 30 seconds"
    :action (do @microwave :set-timer 30)
    :expect ((global? microwave-timer 30))))
```

Benefits:
- Reduces boilerplate (no repeated setup per test)
- Groups related tests logically
- Could support nesting for hierarchical setup
