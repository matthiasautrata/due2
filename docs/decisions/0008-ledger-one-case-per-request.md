# 0008 — The ledger: one case per request, an append-only sequence of events

**Status:** Decided, 2026-10-16
**Context documents:** `due2-workflows.md` §3.3, §7, §7.1 · `due2-architecture.md` §7 · `correctness-strategy.md` §4.7, §9 #9 · issue #28

## Question

The case-history properties (replay, pinning suffices, append-only, two clocks) are stated over a ledger model that did not exist (`correctness-strategy.md` §4.7). What does the ledger hold?

## Decision

Workflows §7.1:

1. **Each request opens exactly one case.** Facts, evidence, activations, and evaluations are events on it, in the order recorded.
2. **The SOTW is the case's evolving truth.** An evaluation reads, for each fact, the value with the latest `valid_at` no later than its `effective_at`. A fact learned late is an event with an earlier `valid_at`. `sotw` has no revision field.
3. **Past decisions are read, not recomputed.** The recorded evaluation pins its inputs and replays.
4. **Append-only; the shell serialises writes per case.**

This reverses §3.3's rule that a later SOTW revision may not change a terminal resolution. A fact that changes in the world is a new event. `conflict` stays for sources that disagree about one fact at one time.

## Rejected

A draft of the same day added a log-position fold, an as-of query over record time, and optimistic-concurrency appends. due2 serves a governance workload with few concurrent writers per case. None of those problems occurs at that scale.

## Revisit when

- Writes to one case contend in practice.
- An audit question needs what was known by a past moment, rather than what was decided then.
