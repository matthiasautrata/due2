# 0016 — Only an unresolved value is completed, and every `U` part is reported

**Status:** Decided, 2026-10-17
**Context documents:** `due2-workflows.md` §3.5, §3.7, §5.4, §6.4, §8 (L4, L9) · `due2-profiles.md` §3 · `decisions/0011`, `decisions/0012` · issues #61, #71

## Question

`due2-workflows.md` §6.4 completes every `U` part to `T` or `F`, and pairs a constraint with its complement (`eq`/`neq`, `lt`/`gteq`, `lteq`/`gt`, `isAnyOf`/`isNoneOf`) as one variable with opposite polarities. That pairing assumes that the operand has a value and that the value can be compared, so that exactly one of the pair holds. Does that hold for every cause of a `U`? And how does a reply say that a definite verdict was reached with something missing (#71)?

An example: two permissions, `r1: x lt 5` and `r2: x gteq 5`, read one request parameter `x`. clingo-i at `47929af`:

| `x` in the request | status (`due2-profiles.md` §3) | verdict | `verdict_basis` |
|---|---|---|---|
| `3` | `resolved` | `Permit` | `r1` |
| absent | `missing` | `Permit`, `exact` | `[]` |
| `"abc"` | `resolved`, does not fit `lt` | `Permit`, `exact` | `[]` |
| `ex:v` | `resolved`, does not fit `lt` | `Permit`, `exact` | `[]` |

Two prohibitions give `Deny` in the same way. In the last three rows nothing in the reply says that `x` was missing or wrong. And for `"abc"`, which is neither `< 5` nor `≥ 5`, no permission applies under a two-valued reading, yet the verdict is a definite `Permit`.

## Decision

1. **Only an unresolved value is completed.** A `U` part is a completion variable (`due2-workflows.md` §6.4) only when its value exists but is not known: a state property whose status is `unresolved`, or that has no fact. Such a value exists and fits, so a complement pair has exactly one true member, and the pairing of `decisions/0012` and `due2-workflows.md` §6.4 v0.6 holds for it unchanged.
2. **Every other `U` part is opaque.** A part is **opaque** when its `U` comes from a value that is `missing`, `invalid`, or in `conflict`, or that is `resolved` but does not fit its operator (a *misfit*, `due2-workflows.md` §5.4 step 3). An absent request field (the target, or one function's party) is `missing`. An opaque part shares a variable with no other part, its complement included, so it is a completion variable of its own. Inside an authored constraint tree it stays `U` under Kleene logic, and a completion completes the finding it leaves `U`. Why this is the same thing on both sides of L9 is shown below.
3. **Every `U` part is reported.** A new W2 relation, `unknown_part (atom_id, predicate, kind, ref | input, status)`, names every `U` part of every finding W2 produces, whether or not it determined the finding or the verdict. `input` is what the part reads: the target, a party function, or an operand's property. `status` is one of `missing`, `invalid`, `conflict`, `unresolved`, and `misfit`. W3 reads it to tell completed parts from opaque ones. `due2-workflows.md` §3.7 adds it to the explanation, so a reader can see, beside any verdict, everything that was missing. A renderer may show less. It cannot show what the trace never recorded.
4. **The basis is cautious** (#71, alternative A). `verdict_basis` names the atoms that carry the verdict in every completion. A definite verdict that holds by cases has no such atom, and its basis is empty, while `unknown_part` names what was missing. A `U` atom that carries the verdict in every completion is named.

The owner's reasons, 2026-10-17: "I prefer more explainable U than unexplainable decisions. If people want the policy to decide they might as well supply the data." And: "report every U. Downstream, an app/GUI can decide how verbose it wants to be and leave details out. It can't make them up if they were never reported back."

## Why it is sound, and why L9 still holds

**Soundness.** An opaque part completed as its own variable admits every combination its findings could take, so it only adds completions. Added completions can only add disagreement, so the cost is an `Indeterminate`, never a wrong definite verdict (the argument of `decisions/0012`, § Why it is sound). The example's last three rows become `Indeterminate`, `NotApplicable`..`Permit`.

**L9.** `I` evaluates the authored tree. W1 rewrites it to DNF atoms, conjunctions of parts. The two must give the same verdicts.

1. W1's rewrites are De Morgan, double negation, distributivity, and the complement operators. Each is an equivalence of strong Kleene logic. So with every opaque leaf at `U` and every completed leaf at `T` or `F`, the tree and the disjunction of its atoms have the same value.
2. On the `I` side, a tree that is `U` in a completion is completed as one variable. On the pipeline side, each atom's opaque parts are variables of their own, so each atom that is `U` takes `T` or `F` freely. The disjunction of the atoms is then `U`-free and takes both values, as `I`'s one variable does.
3. The atoms of one rule share its policy, its duties, and its conflict strategy, so W3 sees only whether one of them applies. Both sides offer W3 the same choices in each completion, so they give the same verdicts.

An example: `x eq 5 or not (x eq 5)` with `x` absent. `I` gets `U or U = U` and completes it, giving `T` or `F`. W1's atoms `x eq 5` and `x neq 5` are two opaque variables, and their disjunction also gives `T` or `F`. The verdict is `Indeterminate` on both sides. Under the old pairing it was `Permit` on both sides.

**L4 is restated.** L4 says that resolving an unknown never changes a definite verdict. A completed variable stands for an unresolved value that exists and fits, so the law holds when that value arrives and fits. It does not hold when the value arrives as a misfit, or the source answers that there is none. Then a part that was completed becomes opaque, and a definite verdict can become `Indeterminate`. Information that turns out to be bad can remove a decision, but it never reverses one: `Permit` never becomes `Deny`. L4 is restated to say this.

## Rejected

- **Keep the pairing for every `U`** (alternative a in the discussion). It reads "unknown" as "some valid value we do not know". That is true for `unresolved` and false for `missing` and for a misfit. The example's `"abc"` row is the counterexample: the verdict is a `Permit`, but no permission's condition is met. `due2-profiles.md` §3 promised that a misfit "costs a late `U`, never a wrong verdict", and the pairing broke that promise.
- **Keep `decisions/0012`'s sharing for opaque parts that are the same expression.** Two rules on target `ex:a` with no target in the request would still give `NotApplicable` under `invalid` (case `due2-shared-reads`). That verdict is decided by cases over a value that does not exist, the decision without data this record removes. The scenarios become `Indeterminate`, and `unknown_part` says that the target is missing.
- **Complete `conflict` as one of its values.** A cardinality-one property with two values is broken data, not an unknown value. The fix is to resolve the conflict.
- **Only report the parts that determined the verdict.** `basis` and the pivotal `unknown` atoms already do that. The owner asked for every `U`, so that a reader learns what was missing even when it did not matter.
- **A `verdict.complete` flag.** It would be derived from `unknown_part`, which is empty exactly when the flag would be true, and `due2-workflows.md` §3.5 does not store a value twice.

## Consequences

- `due2-workflows.md` v0.25:
  - §3.5 adds `unknown_part`, and §3.7 adds it to the explanation;
  - §5.4 records each `U` part's status;
  - §6 gives W3 the relation;
  - §6.4 restricts completion to unresolved values, defines opaque parts, and settles `verdict_basis` (#71);
  - L4 and L9 are restated as above.
- `due2-profiles.md` v0.10 §3 says which statuses are completed. `conformance/README.md` drops the invariant that a `Deny` names a prohibition or a violated obligation.
- `decisions/0012` #1 and #2 now hold only for unresolved values. For request fields, which are never `unresolved`, #1 no longer applies at all.
- **The implementation increment** follows this record:
  - clingo-i keeps opaque leaves at `U` in each world and completes the atom they leave `U`;
  - its reply, the case format (`expected.unknown_parts`), and `tools/check_corpus.py` carry the new relation;
  - its brute-force oracle completes opaque leaves independently;
  - `due2-shared-reads`'s scenarios "no target" and "no assignee" become `Indeterminate`.

  With every literal unpaired, which is a superset of this change, 4 of the corpus's 252 runnable scenarios change at `47929af`. Those two are the only ones this record changes.
- `tools/check_completion.py` needs no change. Its variables are abstract, and an opaque part is one more variable of its own.
- #61 (remedies) gets its first user question: for a request, which missing inputs would decide it. `unknown_part` is its raw material.

## Revisit when

- A profile declares an operand total, so that `missing` contradicts the profile instead of meaning "no value". Then the value exists, and pairing could hold for it.
- A real policy needs a decision while its data is missing, and supplying the data is not possible.
