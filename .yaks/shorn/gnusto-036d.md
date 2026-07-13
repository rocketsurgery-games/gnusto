---
id: gnusto-036d
title: 'No default eat/drink behavior: agent silently substitutes ''take'' for ''eat''/''drink'''
type: task
priority: 2
created: '2026-07-13T03:36:12Z'
updated: '2026-07-13T03:38:54Z'
labels:
- bug
---

---
▸ 2026-07-13T03:36:23Z
Found during Zork playthrough. 'eat the lunch' -> (do @lunch :take); 'drink the water' -> (do @water :take). The lunch/garlic declare :food and water declares :drinkable, but builtins.grue has defaults for take/drop/open/close/put/throw/examine and NO eat/drink, and the objects define none. With no eat/drink verb exposed, the agent falls back to 'take' -- another silent wrong-action. Original Zork supports both (V-EAT/V-DRINK).

eat/drink are fundamental IF verbs and belong as engine defaults (mirroring the existing take/drop pattern, keyed on the :food/:drinkable flags already declared). Implementing generic defaults that consume the item (move ?self nil) with the canonical Zork messages ('Thank you very much. It really hit the spot.' / '...I was rather thirsty.'); non-food/non-drinkable -> 'I don't think that the X would agree with you.'

DESIGN NOTES for user: (a) generic engine message vs per-game override -- games can still define :eat/:drink to override; (b) consume-on-eat is standard IF and matches ZIL, but note the Zork lunch also feeds the cyclops and the garlic wards the bat, so eating them is a legitimate (analyzable) player choice, not something to block; (c) used :food (not :edible) since that's the flag already in the conversion.

---
▸ 2026-07-13T03:38:54Z
FIXED. Added default eat/drink behaviors to builtins.grue (mirroring take/drop), keyed on :food / :drinkable (defaulted lookups), consuming the item (move ?self nil) with canonical Zork messages; non-food/non-drinkable -> 'I don't think that the X would agree with you.'. Games can still override with their own :eat/:drink. Grue tests in games/zork1/house-interior.test.grue (eat lunch, drink water, eat non-food blocked). Verified via harness: 'eat the lunch'/'drink the water' now dispatch :eat/:drink. 691 grue-test + 813 pytest green.
