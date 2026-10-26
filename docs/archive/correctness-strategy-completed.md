# Correctness strategy — completed sequence and resolved register rows

This file keeps what `docs/correctness/correctness-strategy.md` §8 and §9 carried until 2026-10-26, moved here verbatim: the whole sequence as it stood, steps taken included, and the statements of the register rows that were resolved. The current remaining steps and open rows are in that document, which holds where the two differ. Section and step numbers below are those of the document at the time.

## §8 Sequence, as it stood

1. The open items of §9. Row 11 is settled by the prover spike of step 6, which is parked.
2. The case-format extension for negative cases (`expected_rejection`, §4.2).
3. The status matrix and Kleene truth tables, as data (ASP facts, `decisions/0009`). They are spec as much as tests, and `I` uses them first.
4. Slow `I`, the clingo semantics program (issue #9, `decisions/0009`): the driver and its syntactic flatten, the one-value integrity constraint, then every runnable corpus scenario, triage per §6. Fast mode (`due2-workflows.md` §6.4's computation) follows, differentially against enumeration.
5. The input-space description, the bounded-exhaustive enumerator, and the generators (§1.1, §5), with the coverage histogram, first over clingo-i (#42, #44).
6. The formal model (§4.8, `decisions/0021`): an Alloy model per claim and, for M and W, the bounded-exhaustive search over clingo-i, then the prover spike on M, parked (`decisions/0021`, the amendment of 2026-10-24).
7. The W2/W3 evaluator (`decisions/0027`; its language is #104): relation-level vectors (#36, #37), clingo-i's relation-level face (#41), then the evaluator as a spike under the shared suite, gated by `decisions/0006` #4 and as in §4.4 and §4.5 as far as the vectors reach.
8. W1 stage 1 with the Python `Den` oracle. The formal model's `Den` (issue #8) waits for the prover spike.
9. W1 stage 2, gated by L9 against `I`.
10. The W2/W3 evaluator on the full corpus through W1, completing the §4.4 and §4.5 gates.
11. The ledger (data model in §4.7), gated by the stateful machine.

## §9 Resolved rows, as stated

Rows 1–10 are resolved, each where its section states it:

- **1.** Strategy before code is a standing rule (§1; `CLAUDE.md`).
- **2.** Oracles implement definitions; `I` is the clingo program, slow mode first, then fast mode, the two differentially tested (§3, `decisions/0009`).
- **3.** `I` and W1 share only the Turtle reading, and the driver is tested on its own (§4.1, `decisions/0009`).
- **4.** Negative cases are `expected_rejection` with codes from the diagnostic registry (§4.2, `due2-diagnostics.md`).
- **5.** `check_completion.py` covers `violations = deny` and `frontier_complete`, and leaves multi-policy conflict under `invalid` and nested constraints to the differential against slow `I` (§4.5).
- **6.** The generator coverage histogram is a failing check (§5).
- **7.** The disagreement protocol is §6.
- **8.** The critical features are atomization, evaluation, and case history, tested bounded-exhaustively, by generation, and differentially (§1.1).
- **9.** The ledger data model is `due2-workflows.md` §7.1 (§4.7, `decisions/0008`).
- **10.** The enumeration bounds are measured per input space and tier, not guessed (§1.1). clingo-i's bounds, for evaluation, and their timings are in `spikes/clingo-i/TESTS.md` (#42); W1's and the case history's follow the same rule.
