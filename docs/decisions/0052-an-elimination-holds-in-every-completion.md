# 0052 — An elimination is listed only when it holds in every completion

**Status:** Decided, 2026-10-29 (#160)
**Context documents:** `due2-workflows.md` §3.5, §6.2, §6.4 · `decisions/0011` · `decisions/0045` · `spikes/clingo-i/lp/explain.lp` · issue #160

## Question

`due2-workflows.md` §3.5 lists, for each removed entry, each remover and the rule: under `prohibit` and `prohibit-overrides` each `T` `Forbid` that eliminates the candidate, under `perm` each `T` candidate that eliminates the `Forbid`. With no unknowns there is one completion, and the row says what happened in it. Under unknowns, `decisions/0011` #4 lets a `U` entry be removed, while only a `T` entry removes. Within a policy, a `T` remover takes part in every completion, so its rows hold in each. Across policies, a `T` `Forbid` removes only if it survives its own policy's fold, and that can depend on an unknown.

An example (#160): policy p1, under `perm`, has a permission `ex:r` on `ex:x eq 5`, with `ex:x` unresolved, and a prohibition `ex:forbid` whose finding is `T`. Policy p2 has a permission `ex:rq` whose finding is `T`. Where `ex:x` is 5, `ex:r` removes `ex:forbid` within p1, and `ex:rq` permits; elsewhere `ex:forbid` denies and removes `ex:rq`. The verdict is `Indeterminate`, `Deny` to `Permit`. clingo-i listed `ex:rq` removed by `ex:forbid` under `prohibit-overrides`, a removal that one completion does not make.

What does `eliminated` list when a removal holds in some completions only?

## Decision

1. **A tuple is listed only when it holds in every completion** in which its entry reaches the step that removes it: under `violated_precondition`, where the entry applies; under a conflict rule, where it is a candidate or, for a `Forbid`, applies (`due2-workflows.md` §3.5).
2. **Within a policy, nothing changes.** Each remover of `due2-workflows.md` §3.5 that takes part in every completion, a `T` `Forbid` or a `T` candidate that no completion closes, removes the entry wherever the entry takes part.
3. **Across policies, the `Forbid` must survive.** The `T` `Forbid` entry `(Y, Q)` is listed as removing the candidate entry `(X, P)` only if `Q`'s fold keeps `(Y, Q)` in every completion in which `(X, P)` is a candidate.
4. **A removed entry may still be `U`** (`decisions/0011` #4). What may not be uncertain is the removal itself.

## Why this holds

- **A row is a reason that holds whatever the unknowns are.** Under a definite verdict, the reply's other relations hold in every completion: the cautious basis (`due2-workflows.md` §6.4) and the routes that suffice (`due2-workflows.md` §6.3). A reader checks an `eliminated` row against the policies alone. A row that one completion contradicts cannot be checked that way, and it reads as a fact about the request that is not one.
- **The verdict says what is uncertain.** In the example the verdict is `Indeterminate`, its range is `Deny` to `Permit`, and `unknown_part` names `ex:x`. That is what a caller needs to resolve the `U`. A row conditioned on `ex:x` would repeat it, in a second form that a reader must also check.
- **"Not surely removed" is not "survives".** The weaker test is world `k`'s: no `T` candidate of `Q` removes `(Y, Q)`, so `Q` does not surely remove it. It is wrong both ways. In the example it lists a removal under an `Indeterminate`. With `ex:r` on `ex:x eq 5 or ex:x neq 5`, `ex:r`'s finding is `U` but it applies in every completion, so `ex:forbid` never survives, the verdict is `Permit`, and the weaker test still lists `ex:rq` as removed. With a duty on each permission the verdict is `Pending`, and the same row takes `ex:rq`'s route out of the listed frontier.

## Rejected

- **Each removal with the condition under which it holds.** It says more, but the condition is a formula over the unknowns, and its form would need a specification of its own. `unknown_part` and the range already name what the verdict waits on.
- **List nothing under `Indeterminate`.** It is simple, but it drops rows that hold in every completion, such as a `U` candidate removed within its policy by a `T` `Forbid`, which `decisions/0011` #4 lists.

## Consequences

- `due2-workflows.md` v0.62 §3.5 states the rule, and §6.2 #2 points to it.
- clingo-i's `explain.lp` keeps world `k`'s cross-policy row as a candidate (`may_override/4`) and drops it in a model whose completion world breaks it (`override_broken/4`). The cautious solve 2 then keeps only the rows that hold in every completion. The listed frontier reads the same rows. `test_cross_policy_rows_hold_in_every_completion` pins the `Indeterminate` and the `Permit` by cases, and `test_route_listed_beside_a_forbid_removed_by_cases` the `Pending`.
- The brute-force oracle of `tests/test_brute_force.py` has one policy, so it never reaches the cross-policy rule; within one policy its rows already hold in every completion.
