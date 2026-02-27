---
id: gnusto-lp1.4
title: Test in-context generation with reference images
type: task
priority: 1
created: '2026-01-07T19:17:10.566967-05:00'
updated: '2026-02-08T19:07:10.985071Z'
depends_on:
- gnusto-lp1.7
---

Use OmniGen2's native multi-image input to test: (1) style transfer from a reference, (2) object consistency using reference images, (3) combining multiple references (style + object). Measure how faithfully the reference is reproduced.

## Progress (2026-01-07)
- ✅ Single reference test completed: brass lantern in cave scene (test_lantern_scene.png)
- 🔄 Multi-reference test started but interrupted (CPU too slow ~1min/step)
- Reference images created: brass_lantern.png, elvish_sword.png, jade_figurine.png

## Next Steps
1. Run multi-reference test on GPU (lantern + sword in dungeon scene)
2. Test jade figurine visibility in complex scene
3. Evaluate reference adherence quality across all tests
