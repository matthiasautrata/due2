# 0042 — A case fixes its request, corpus, config, and pins

**Status:** Decided, 2026-10-26 (the owner, on #139)
**Context documents:** `due2-workflows.md` §3.2, §3.4, §3.5, §7.1 · `due2-platform.md` §2.2, §2.6, §2.10 · `decisions/0008` · `decisions/0030` · `decisions/0038` · issue #139

## Question

`decisions/0038` made a case fix its request and corpus: `case (case_id | request, corpus)`. Each evaluation of the case still named its own config and pins: `evaluation (case_id, seq | request, corpus, sotw, config, pins, trace?, verdict?, error?)`. So one case could be evaluated under one `combination`, `admit_source`, or `signer` record on Monday and another on Friday.

Config changes the trace (`due2-workflows.md` §3.4), so a case's later verdicts could rest on terms its earlier ones did not. That is the moving target `decisions/0038` ruled out for the corpus. Should a case fix its config and pins too?

## Decision

1. **A case fixes its request, corpus, config, and pins.** `case (case_id | request, corpus: Digest, config: Digest, pins)`. The orchestrator records all four when it opens the case for a request, and every evaluation of the case reads them from the case.
2. **An evaluation records only what varies.** `evaluation (case_id, seq | sotw: Digest, trace?, verdict?, error?)`. Its corpus, config, and pins are the case's. Its request is the case's request with an earlier `at` moved to `effective_at` (`decisions/0030`), so it is derived from the case and the SOTW and is not stored either.
3. **A config change opens a new case,** as an amended policy or a new normaliser version does (`decisions/0038`). The new case's activations start afresh, and evidence of the earlier case counts only if it is recorded again.

## Why this holds

- **The owner's earlier project worked this way** (#139). There, the request wrote the case into the ledger, and evaluation read the case.
- **Config is part of the terms.** `combination` picks the conflict strategy, `admit_source` says whose facts count (`decisions/0040`), and `signer` says whose evidence counts. L1 (`due2-workflows.md` §8) requires the same trace from the same inputs, and the config is one of them (`due2-workflows.md` §3.5). The argument of `decisions/0038` therefore applies to the config as it does to the corpus: within a case, only the world changes.
- **Pins follow the corpus.** The pins are the normaliser versions in force, and the corpus is what those versions built. A case that fixes its corpus fixes its pins with it.
- **The ledger holds each fixed value once.** The evaluation tuple no longer repeats what the case holds, so nothing has to check that the two agree.

## Rejected

- **Each evaluation names its own config (v0.49).** A case's verdicts could then differ because the config changed while the world did not, and the ledger would have to show which config each verdict ran under.

## Consequences

- `due2-workflows.md` v0.50 §7.1: `case` and `evaluation` as in items 1 and 2, and *A case fixes its terms* replaces *A case fixes its corpus*.
- `due2-platform.md`: `create_case` takes the request, corpus, config, and pins (§2.2), and §2.6 and §2.10 follow.
- `decisions/0008` and `decisions/0038` get notes.

## Revisit when

- A config field turns out to be operational rather than part of the terms, such as a bound that only limits cost. `max_mixed` and `max_frontier_vars` change the trace (`due2-workflows.md` §3.4), so they are terms today.
