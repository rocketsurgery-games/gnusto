---
id: gnusto-mx5
title: Handle article hints (AN, THE) as :article property
type: task
priority: 2
created: '2026-01-17T23:59:21.301833-05:00'
updated: '2026-02-08T19:07:11.010591Z'
---

Convert article-related flags to a single :article property.

Before: `:flags (AN)` or `:flags (THE)`
After: `:properties (:article :an)` or `:properties (:article :the)`

Default article is :a. Value :none for no article.

Update parser/printing code that uses these flags.
