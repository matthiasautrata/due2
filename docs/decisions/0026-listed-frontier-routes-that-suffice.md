# 0026 — The listed frontier is the routes that suffice

**Status:** Decided, 2026-10-24 (the owner, on #84)
**Context documents:** `due2-workflows.md` §6.3, §6.4 · `decisions/0004`, `0019` · `correctness-strategy.md` §4.8 (claim P) · `formal/alloy/p_listed_frontier.als` · `tools/check_completion.py` · issues #84, #70

## Question

A route is an outstanding set: the duties a requester must still fulfil through one candidate (`due2-workflows.md` §6.1). Under unknowns, `due2-workflows.md` v0.33 §6.3 formed the reply's frontier only from the candidates that are ready or pending whatever the unknowns are. `decisions/0019` found a definite `Pending` whose listed frontier omits a route that every completion offers, because no single permission gives it in every completion. It left open whether §6.3 should list such a route (question P, `correctness-strategy.md` §4.8).

An Alloy model of v0.33 (commit `ca4a783`) characterised that omission at every completion of three unknowns. Every omission left `frontier_complete` false, so the reply was flagged incomplete, never wrong. Every omission needed two permissions that read one variable in opposite directions, in their own findings or in their preconditions' `owed`, or a finding that reads a variable both ways. Four shapes reach it, one run each in that commit (`Shape0019`, `ClosingPrecondition`, `ComplementaryPreconditions`, `SelfContradiction`):

- complementary permissions, the shape of `decisions/0019`;
- a lapsed precondition owed on `x` that closes one route, where a permission on `x` opens the same route;
- two permissions whose preconditions are owed on `x` and on `¬x`;
- a finding that reads a variable both ways, such as `x eq 5` and `x neq 5` in one `and`.

In instances of the second and third, the listed frontier is empty: the reply is `Pending` with nothing to do, though every completion agrees on what to do.

A commoner shape is not an omission of that kind. One permission needs `d` and `d2`, and `d2`'s `fulfilled` finding is `U`. Its route is `{d, d2}` in some completions and `{d}` in the others, so the candidate is uncertain, and v0.33 lists nothing. `tools/check_completion.py` finds an empty listed frontier in 191 of 942 random definite `Pending` verdicts.

## Decision

1. **A route is open in a completion** when some candidate that survives `due2-workflows.md` §6.2 there has it as its outstanding set, whether or not a smaller route dominates it there.
2. **A route suffices** when it is open in some completion, and every completion has an open route within it: the same set or a subset.
3. **For a definite `Pending` or `Permit`, the listed frontier is the non-dominated routes that suffice.** Each is an alternative whose grounds are the permissions that give it in some completion. For a definite `Permit`, every completion has the empty route open, so the listed frontier is the empty route.
4. **Within `max_frontier_vars`, W3 computes it exactly** by enumerating the relevant unknowns (`decisions/0004`): two `Pending` completions that agree on them have the same open routes. Beyond the bound, W3 lists the routes of the candidates that are ready or pending whatever the unknowns are, and that no completion removes in `due2-workflows.md` §6.2. Under `invalid`, a `U` prohibition in a candidate's policy voids the policy in some completion, so such a candidate is left out; under `prohibit`, a definite `Pending` has no such prohibition. `frontier_complete` and `verdict.exact` are then false.
5. **`frontier_complete` keeps its definition:** it is true iff every completion's frontier is the listed frontier.

A listed route is one the requester can act on. Take a completion. Some candidate there has an outstanding set within the route, and fulfilling the route's duties empties that set. A fulfilled duty is not violated, so `due2-workflows.md` §6.1 closes no candidate on its account, and §6.2 never reads duties, so the candidate still survives, and it is ready. By monotonicity under the default combination (`due2-workflows.md` §6.4), making `fulfilled` findings true cannot lower that completion's verdict, which was not `Deny`, so the verdict is `Permit`. That holds in every completion.

The listed frontier is empty only when what to do depends on an unknown: each route suffices for some completions and not for others. The reply's `unknown_part` rows name the unknowns, and `frontier_complete` is false. `tools/check_completion.py` finds one such verdict in 942: a precondition `d0` owed when `x1` is false, and `d1` owed when it is true.

In `decisions/0019`'s first run, `ex:perm`'s route `{ex:d, ex:d2}` is open in both completions, and `ex:perm2`'s `{ex:d}` only in one. Only `{ex:d, ex:d2}` suffices, so the listed frontier stays `[[ex:d, ex:d2]]`, and `frontier_complete` stays false. In its second run, `{ex:d}` and `{ex:d3}` are open in both completions. The listed frontier becomes `[[ex:d], [ex:d3]]`, and `frontier_complete` becomes true. In the commoner shape, `{d, d2}` suffices and is listed.

## Alternatives

- **Keep v0.33.** The omission is flagged by `frontier_complete`. Rejected: a definite `Pending` can list nothing to do, although every completion agrees on a route.
- **The routes open in every completion.** Rejected: the commoner shape lists nothing, since `{d, d2}` is not open where `d2` is fulfilled. `tools/check_completion.py` finds an empty listed frontier in 181 of 942 verdicts this way.
- **The routes in every completion's frontier** (`decisions/0019`'s cautious frontier). Rejected: a route that a smaller route dominates in some completion is dropped. In `decisions/0019`'s first run it lists nothing.
- **The routes in some completion's frontier.** Rejected: fulfilling such a route's duties may permit only in some completions.
- **Unions of routes across completions.** In the empty case above, `{d0, d1}` permits in every completion. Rejected: it is no candidate's outstanding set, so it has no permission for its grounds, and the reply would ask for duties that some completions do not owe.

## Consequences

- `due2-workflows.md` v0.34 states the decision in §6.3, and in §6.4 how it is computed. Its §3.5 `alternative` relation lists every permission that gives a route in some completion.
- No single permission need give a listed route in every completion. Which one gives it depends on the unknowns, which the reply's `unknown_part` rows name. `verdict_basis` already names only the atoms that play their role in every completion (`decisions/0016` #4).
- `tools/check_completion.py`'s fifth phase checks the bounded computation against brute force over every completion, and checks that every route the fallback lists suffices.
- `formal/alloy/p_listed_frontier.als` checks this record, and P becomes a claim. `formal/alloy/f_frontier_relevance.als` checks that the relevant unknowns fix the open routes.
- clingo-i lists v0.33's frontier until #103. No corpus case reaches the shapes (`decisions/0019`), so the corpus is unchanged.
- `decisions/0019`'s relaxed basis check stands: in its first run, the basis duties are still not the listed frontier's.

## Revisit when

- An explanation must name, for each listed route, one permission that gives it in every completion.
- A requester needs a plan across the unknowns, such as `{d0, d1}` above.
