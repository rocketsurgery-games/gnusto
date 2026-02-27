---
id: gnusto-b11z
title: Fix render tests for RenderResult.prompt_parts change
type: bug
priority: 3
created: '2026-02-08T17:17:14.694012-05:00'
updated: '2026-02-13T15:57:05.830232-05:00'
---

The RenderResult class was updated to use `prompt_parts` instead of `prompt`, but the tests still reference `.prompt`:

Failing tests:
- tests/grue/test_render.py::TestRenderSpecEvaluation::test_simple_prompt
- tests/grue/test_scene_renderer.py::TestRenderSpecIntegration::test_object_with_render_spec

Error:
```
AttributeError: 'RenderResult' object has no attribute 'prompt'
```

Fix: Update tests to use `prompt_parts` or add a `prompt` property that joins the parts.
