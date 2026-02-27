---
id: gnusto-gv2.21
title: Include barrier preconditions in tracked refs
type: task
priority: 2
created: '2026-01-24T16:30:52.824141-05:00'
updated: '2026-02-08T19:07:10.996554Z'
---

When computing state refs for exploration, we currently track refs that behaviors MODIFY but not refs that behaviors READ as preconditions. This causes exploration to fail when navigation barriers check conditions we're not tracking.

Example: @tentacle-climb checks (not (:wearable @gloves)) but we don't track @gloves:wearable, so the 'open' action on it gets pruned and we can't pass through.

Solution: Extend backward constraint propagation to:
1. Analyze barrier :through behaviors on navigation paths
2. Extract the conditions they check (static analysis of behavior body)
3. Add those conditions as refs to track
4. Find behaviors that can establish those conditions

This is the same pattern as build_victory_constraints but applied recursively to navigation barriers.
