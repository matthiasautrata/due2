# 0004 — `frontier_complete` is computed by bounded enumeration

**Status:** Decided, 2026-10-11
**Context documents:** `due2-workflows.md` §3.5, §6.1–§6.4 · `correctness-strategy.md` §4.5 · `tools/check_completion.py` (fifth phase) · issue #29

## Finding

Workflows §6.4 defined `frontier_complete` by quantifying over completions: it is false when some uncertain candidate could, in some completion, add or change a frontier alternative without changing the verdict. It gave no computation. §6.4's two-extremes shortcut does not carry over. That shortcut works because the verdict is monotone into a chain, but a frontier is a set of alternatives, and sets have no extremes to complete towards.

The fifth phase of `check_completion.py` (seed 20261015) compared the listed frontier with every completion's frontier. It ran 50,000 partial-knowledge instances, 942 of them a definite `Pending`:
- By the definition, `frontier_complete` is false in 199 of the 942. In 191 of those the listed frontier is empty.
- In 4, a listed alternative is not on some completion's frontier, because an uncertain candidate with a smaller outstanding set dominates it.
- The cheap rule "complete iff no candidate is uncertain" was never wrong, but it says false in 133 instances where the definition says true.

## Options

| | A — the cheap rule | **B — bounded enumeration (chosen)** | C — any sound approximation |
|---|---|---|---|
| What the spec defines | weakened to "false when some candidate is uncertain" | unchanged | unchanged |
| Cost | none | `2^r` frontier computations for `r` relevant unknowns, at most `2^max_frontier_vars` | implementation's choice |
| Exact | no (133 of 942 false negatives above) | yes below the bound; beyond it, false and `exact = false` | no guarantee |
| Deterministic across implementations | yes | yes | no: two correct engines may disagree, so replay and the corpus cannot pin the field |

## Decision

1. **The definition stays.** For a definite `Pending`, `frontier_complete` is true iff every completion yields the listed frontier (workflows §6.4).
2. **Relevant unknowns.** These are the variables of the `U` parts of uncertain candidates (permission, `owed`, `fulfilled`) and of prohibitions whose finding is `U`. Ready and pending candidates have no `U` parts. Under a definite `Pending`, no other unknown can change the frontier: a `U` obligation that could deny would already have made the verdict non-definite.
3. **The computation.** If there are `r ≤ max_frontier_vars` relevant unknowns (a W3 limit; default 8), W3 enumerates all `2^r` assignments and compares each frontier with the listed one. There is no shortcut through extremes.
4. **Beyond the bound.** `frontier_complete = false` and `verdict.exact = false`. False is the safe direction: it only says that the listed alternatives may not be all of them. A single `exact` flag covers every approximation W3 makes.
5. **Checked.** In the fifth phase of `check_completion.py`, the bounded enumeration equals the definition (brute force over every unknown) in all 942 instances. With the bound forced to 1, the fallback runs in 148 instances and is never unsound. Both are gates.

## Scope

The model in `check_completion.py` covers one policy. Under conflict `invalid` with several policies, a `U` prohibition can void another policy's ready candidate while `Pending` stands. Item 2 includes `U` prohibitions for this reason, but the multi-policy case is only checked once the brute-force W3 differential exists (`correctness-strategy.md` §4.5).

## Impact

- The `frontier_complete` paragraph of workflows §6.4 now states the computation, and §3.5's meaning of `exact` now covers this fallback too. The workflows draft goes to v0.9.
- No corpus case asserts `frontier_complete`. This is a coverage gap, tracked as issue #30.
