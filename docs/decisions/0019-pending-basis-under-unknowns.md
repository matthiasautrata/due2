# 0019 — A `Pending` basis under unknowns is checked only for its kinds

**Status:** Decided, 2026-10-18 (the owner chose alternative A of #75)
**Context documents:** `due2-workflows.md` §6.3, §6.4 · `decisions/0016` #4 · `conformance/README.md` (`expected.verdict_basis`) · `tools/check_corpus.py` · issue #75

## Question

Under unknowns, `verdict_basis` names the atoms that play a role in every completion (`due2-workflows.md` §6.4 **[D]**, `decisions/0016` #4), and the reply's `frontier` is read from the candidates that are ready or pending whatever the unknowns are, so an uncertain candidate enters only through the verdict (`due2-workflows.md` §6.3). `tools/check_corpus.py` asked more of a `Pending` scenario: role `duty` exactly the frontier's duties, and role `permission` present unless the scenario lists an `unresolved` unknown part. Two clingo-i runs give a definite `Pending` whose reply breaks those checks.

1. **A dominating uncertain route** (`test_pending_basis_under_an_uncertain_route` in `spikes/clingo-i/tests/test_duty.py`). `ex:perm` has finding `T` and needs `ex:d` and `ex:d2`. `ex:perm2` needs `ex:d`, and its finding is `U` on a missing request parameter. Where `ex:perm2` applies, its `{ex:d}` dominates; where it does not, `ex:perm` is the frontier. Both completions are `Pending`, no permission is in both frontiers, and the basis is `ex:d` alone. The frontier is `[[ex:d, ex:d2]]`. The only unknown part is `missing`, so the waiver did not apply: one variable suffices, because dominance, not a shared variable, makes the role vary.
2. **A route every completion offers** (`test_pending_basis_beyond_the_listed_frontier`). `ex:perm` has finding `T` and needs `ex:d`. `ex:permA` on `ex:x eq 5` and `ex:permB` on `ex:x neq 5` both need `ex:d3`, with `ex:x` unresolved, so exactly one of them applies in each completion. Each completion's frontier is `{ex:d}` and `{ex:d3}`, so the basis names `ex:perm`, `ex:d`, and `ex:d3`. Neither `ex:permA` nor `ex:permB` is listed, so the frontier is `[[ex:d]]`, and the basis's duties are not even a subset of the frontier's.

## Decision

The spec stands. When a `Pending` scenario lists an unknown part of any status, the checker asks of its basis only what it asks of every basis: each `permission` entry is a permission of `policy.ttl` and each `duty` entry a precondition. Neither role must be present, and the duties need not match the frontier's. Without an unknown part every completion is the same, so the checks stay as they were: `permission` and `duty` present, and the duties exactly the frontier's.

## Alternatives

- **A cautious frontier.** List the alternatives that are in the frontier in every completion. It changes `due2-workflows.md` §6.3, and in the first run it lists nothing under a definite `Pending`.
- **A listed basis for `Pending`.** Take roles `permission` and `duty` from the listed frontier, not from every completion. It reverses `decisions/0016` #4 for one verdict.
- **Relax to a subset.** The duties a subset of the frontier's, as #75 first proposed. The second run refutes it.

## Consequences

`tools/check_corpus.py` and `conformance/README.md` (`expected.verdict_basis`) state the relaxed check. No corpus case reaches either shape. The second run also shows that the listed frontier can omit a route that every completion offers, `{ex:d3}`, because no single permission gives it. Whether `due2-workflows.md` §6.3 should list such a route is a question for the formalisation review (#70), with both shapes among its counterexamples.

## Amendment (2026-10-24, the listed frontier)

§ Consequences left open whether `due2-workflows.md` §6.3 should list a route that every completion offers when no single permission gives it. `decisions/0026` answers it: under unknowns, the listed frontier is the non-dominated routes that suffice, those within which every completion has an open route. In the second run, the listed frontier becomes `[[ex:d], [ex:d3]]`, so the basis's duties are now the frontier's. In the first run it stays `[[ex:d, ex:d2]]`, and the basis is still `ex:d` alone. The relaxed check therefore stands. clingo-i and `test_pending_basis_beyond_the_listed_frontier` follow `decisions/0026` with #103.
