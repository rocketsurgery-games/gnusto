---
id: gnusto-aab0
title: 'Event queue contract: countdown one-shot vs. fire-until-dequeued'
type: task
priority: 2
created: '2026-07-11T14:36:57Z'
updated: '2026-07-11T14:58:58Z'
labels:
- lang
- runtime
---

Root/design yak for the open question about the event-queue countdown semantics in runtime.process_events. Today, when a queued event reaches its firing turn it fires but is NOT removed from the queue, so (queue X 1) means 'fire every turn from now on' unless the body explicitly (dequeue X). This surprised the elevator code (which assumed one-shot) and caused a soft-lock. Decide the intended contract: should a positive countdown auto-dequeue on fire (true one-shot), leaving countdown=None as the only 'indefinite' mode? Weigh against existing self-dequeuing events (compulsion, hacker-helps, food-hint) and state-space analysis (frotz domains collapse countdowns). Capture decision + migration plan here.

---
▸ 2026-07-11T14:48:01Z
DECISION (ZIL-faithful): adopt the interrupt contract from The Lurking Horror's own CLOCKER/QUEUE/DEQUEUE (games/lurkinghorror/source/misc.zil L773-878).

ZIL ground truth (CLOCKER L843-875):
- TICK > 0 (positive): decrement each turn; when it reaches 0, CLEAR C-RTN (dequeue) THEN fire the routine -> a ONE-SHOT that auto-removes.
- TICK = -1 (negative): never decremented, fires every turn, never dequeued -> INDEFINITE until explicit DEQUEUE. (e.g. <QUEUE I-MICROWAVE -1>.)

Grue contract we adopt:
- (queue X)  / countdown None  -> INDEFINITE (fires every turn; body must (dequeue X)). Maps to ZIL -1.
- (queue X N), N >= 1           -> ONE-SHOT: fires after N turns (countdown=1 fires this turn, keeping existing timing), then AUTO-DEQUEUES. To repeat, the body re-queues itself (the established chain idiom: freezing 4, waxer-moves 5, item-cooling 2, food-hint 2, elevator-moves 1).
- (queue X 0)                   -> ONE-SHOT immediate (fire this turn, then dequeue).
- negative countdown            -> INDEFINITE (preserve; game already uses -1 for panel-noises, slime-attack, rats-event, line-in-water, hand-dives, hacker-returns, frob-appears).

Runtime today (src/grue/runtime.py process_events L579-592) NEVER dequeues a fired event, so BOTH None/-1 AND positive-N end up 'fire forever'. -1/None happen to be correct (indefinite); positive-N is the bug (elevator soft-lock). Fix: on fire, if countdown is a finite non-negative int (0 or 1 at fire time), del it from state.queues BEFORE calling _evaluate_event (queue/dequeue effects mutate state.queues synchronously during body eval, so dequeue-before-fire preserves a body's self-re-queue -- exactly ZIL's PUT C-RTN 0 before APPLY).

BEHAVIORAL DELTA: only finite-countdown events that neither re-queue nor self-dequeue change (fire-forever -> fire-once = the intended one-shot). Chain events (re-queue with finite N) are identical under both. None/-1 indefinite events unchanged. Audited all ~30 LH events + builtins: chains re-queue, one-shots either self-dequeue (redundant after fix, harmless) or were latently buggy (now fixed).

FOLLOW-UP NOTE: frotz/domains.py abstracts queue as None/missing=NOT_PENDING, 0=FIRING, >0=PENDING -- inconsistent with runtime's None=indefinite. Out of scope here; flag for a frotz-alignment yak.

---
▸ 2026-07-11T14:58:54Z
DONE. Implemented ZIL-faithful contract in runtime.process_events (src/grue/runtime.py): on fire, if countdown is a finite non-negative int, del it from state.queues BEFORE _evaluate_event (so a body's self-re-queue survives; mirrors ZIL PUT C-RTN 0 before APPLY). None/negative = indefinite (unchanged). Collateral migration: compulsion (terminal-room.grue) had DROPPED its ZIL self-re-queue (I-COMPULSION does <QUEUE I-COMPULSION 1> each page) and relied on the old fire-forever bug; added (queue compulsion 1) to the 3 non-terminal page branches. Audited all ~30 LH events: only compulsion actually relied on the bug; delayed one-shots self-dequeue, chains re-queue (freezing 4, waxer-moves 5, item-cooling 2, food-hint 2, elevator-moves 1), yuggoth-advance is re-queued externally by bowl-room :on-enter, indefinite events use None/-1. Docs updated (docs/grue.md queue-contract table + lifecycle). Tests: 770 pytest + 478 grue all green. FOLLOW-UP (not filed): frotz/domains.py queue abstraction (None=NOT_PENDING) is inconsistent with runtime None=indefinite; worth a frotz-alignment yak if state-space analysis is revisited.
