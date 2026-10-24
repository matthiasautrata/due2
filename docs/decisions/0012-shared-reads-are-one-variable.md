# 0012 — The same read is one completion variable; different reads stay independent

**Status:** Decided, 2026-10-17; narrowed by `decisions/0016` (#1 and #2 hold only for unresolved values, so #1 no longer applies to request fields) and by `decisions/0023` (#1 and #2 apply only when the concept reading is also the same)
**Context documents:** `due2-workflows.md` §5.2, §6.4, §9 (open decision 6) · `decisions/0011` #2 · issues #56, #59

## Question

§6.4 makes each `U` part its own completion variable, except that constraint parts with the same key share one. Relation and party parts were not in that exception. When the request leaves out a field, such as the target, two atoms that read it were completed independently. Should they share a variable (#56)?

An example, with `odrl:conflict odrl:invalid`, a permission and a prohibition that both `use` `ex:a`, and a request with no target:

| Reading | Completions | Verdict |
|---|---|---|
| per part | (T,T) void · (T,F) Permit · (F,T) Deny · (F,F) NotApplicable | `Indeterminate`, Deny..Permit |
| shared | T void · F NotApplicable | `NotApplicable` |

The mixed completions say "the target is `ex:a`" for one rule and "it is not" for the other, about one request. No request produces them.

## Decision

1. **The same expression is one variable.** Two parts that test the same request field against the same value with the same relation are one completion variable: the target, or one function's party (`odrl:assignee` and `odrl:assigner` are different fields). This is #56's alternative 2. It is the constraint key's equal-operator case, applied to relation and party parts, and it is what `decisions/0011` #2 assumed ("two atoms may share one, such as one absent party").
2. **A complement is the same expression negated.** Constraint parts with complementary operators stay one variable with opposite polarities (§6.4, since v0.6). The pairing is read from the fixed operator table, with the same operand and right operand: no arithmetic. Relation and party parts have no negated form, so only #1 applies to them.
3. **Anything else stays independent.** Different expressions over one field, such as target `ex:a` and target `ex:b`, or `x eq 0` and `x lteq 2`, are separate variables. Whether one implies or excludes the other is not worked out: that would be symbolic or algebraic resolution, and it is out of scope. #56's alternative 3, mutual exclusion over the values of a single-valued field, is one case of it, and goes to workflows §9 open decision 6 (domain-aware completion), not rejected.

## Why it is sound

Parts that are the same expression always have the same truth value, so sharing drops only completions that cannot occur. It cannot turn a real disagreement into a definite verdict. Leaving different expressions independent keeps completions that may not occur. Those only add disagreement, so the cost is an `Indeterminate`, or a `verdict_range` wider than domain reasoning would give, never a wrong definite verdict. With `perm`, a permission on `x lteq 2` and a prohibition on `x eq 0`, and no `x`, the completions give `Deny`..`Permit`. Algebra would exclude the `Deny`, since `x eq 0` implies `x lteq 2`, and give `NotApplicable`..`Permit`.

## Rejected

- **Per part** (#56's alternative 1). It is sound, but it reports `Indeterminate` where every possible request gives one verdict, and its `verdict_range` and pivotal `unknown` atoms (`decisions/0011`) describe completions that cannot occur. In `perm`'s version of the example above, it reports `Deny`, which no request gives.

## Consequences

- workflows §6.4 states #1 (v0.20) and #3 (v0.21).
- Corpus case `due2-shared-reads` pins the choice. Under the per-part reading, its scenarios without a target and without an assignee would be `Indeterminate`.
- clingo-i keys literals this way (`spikes/clingo-i/lp/completion.lp`), and its brute-force differential shares the key with it. So the differential cannot check the choice; the corpus case does.
- `tools/check_completion.py` needs no change. Its variables are abstract and already shared across atoms. It checks §6.4's computation over variables, not the key that maps parts to them.

## Process note

The v0.20 edit to §6.4 (#59, 5f3e22d) put #1 into [D] text before this record existed. The owner adopted it afterwards, with #3 as the stated limit. This record is the settlement #56 asked for.

## Revisit when

- `odrl:partOf` or another hierarchy relation lands for targets, so that several target reads can hold at once.
- A real policy needs domain-aware completion (§9 open decision 6).
