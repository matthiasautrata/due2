# 0011 — An Indeterminate verdict is explained by its pivotal literals and its range

**Status:** Decided, 2026-10-17
**Context documents:** `due2-workflows.md` §3.5, §3.7, §6.2, §6.4 · `decisions/0010` · `references.md` §2–§3 · issues #58, #59, #60, #61

## Question

Workflows §6.4 says `verdict_basis` names, for `Indeterminate`, "the `U` atoms whose completion changes the outcome". Issue #59's first draft read this as the `U` atoms whose value differs between two completions with different verdicts. Under that reading, every `U` atom that is not constant over the completions qualifies, including atoms that cannot affect the verdict. What does the sentence mean, and what else does an `Indeterminate` need to say?

## Decision

1. **Pivotal literals.** A completion variable (a literal, §6.4) is **pivotal** when some completion's verdict changes if that variable alone is flipped. For an `Indeterminate` verdict, `verdict_basis` with role `unknown` names each atom whose finding is `U` and one of whose `U` parts is a pivotal variable. The atom's `basis` names the part. This is the established notion, reached independently four ways (`references.md` §2):
   - the relevant (essential) variables of the verdict function over the completions, those with non-zero influence or Banzhaf power;
   - Halpern–Pearl actual causes under some contingency, equivalently a Chockler–Halpern responsibility above zero;
   - the literals that occur in some abductive explanation (a prime implicant) of some verdict;
   - XACML's missing attributes that a PDP may name for an `Indeterminate`.
2. **Flip literals, not atoms.** Completions range over literals (§6.4 **[D]**), and two atoms may share one, such as one absent party or a complementary constraint pair. Flipping a whole atom would complete correlated parts independently, which §6.4 forbids.
3. **`verdict_range`.** An `Indeterminate` verdict also records the least and the greatest completion verdict in the chain `Deny < NotApplicable < Pending < Permit` (§6.4), as `verdict_range (| low, high)`. By monotonicity, the two extremes give them, and the mixed enumeration gives them when there are mixed variables. When `verdict.exact` is false, the range is sound, and may be wider. This is what XACML's `Indeterminate{P}`, `{D}` and `{DP}` record. It tells the reader how much is at stake: `Deny`..`Permit`, or only `NotApplicable`..`Permit`. A definite verdict records no range.
4. **Elimination is over findings.** This restates §3.5 and §6.2, which already say it. A remover is a `T` atom, and an atom removed is a `T` or `U` one: "`U` atoms eliminate nothing" (§6.2), and a candidate is a root `Permit` with finding `T` or `U` (§6.1). So `eliminated` records a `U` candidate that a `T` prohibition removes under `prohibit`. A `U` prohibition beside a `T` candidate removes nothing, and leaves the verdict uncertain (XACML reasons the same way).
5. **Computing it.** clingo-i computes the pivotal literals and the range by enumeration, inside its variable cap (#59). W3's computation, and its fallback past a bound, are set with W3 (#38). A sound fallback reports every `U` atom with role `unknown` and records `verdict.exact = false`.

## Context

The determining sets for `Permit` and `Deny` match Cedar's *determining policies*: the satisfied permits, the satisfied forbids, and an empty set for a default answer. That is due2's empty basis for a `NotApplicable` (`references.md` §3). A finding's `basis` is why-provenance (Buneman, Khanna, and Tan). `eliminated` answers a why-not question (Chapman and Jagadish). A definite verdict is a certain answer over the completions (Imieliński and Lipski; Libkin). due2's three-valued explanation therefore reuses established notions throughout. Its one addition is that unknowns are kept apart from false. FORCE, OVAL and the W3C CG reports all close an unknown to false (`conformance/external/README.md`, § Traces compared).

## Rejected

- **The draft reading** (an atom that differs between two disagreeing completions). It reports nearly every `U` atom, so it explains nothing.
- **Degrees of responsibility, Banzhaf or Shapley scores.** They are numbers, exponential to compute exactly, and the corpus asserts membership. Membership is responsibility above zero, so a score can be added later without changing the set.
- **Provenance polynomials, and xclingo or causal justifications as the trace.** The trace records the determining parts, not every derivation, and is already the derivation (`decisions/0010`). xclingo is a candidate for rendering clingo-i's derivations later.
- **Recording every reachable verdict instead of the range.** Intermediate verdicts between the extremes need extra enumeration. The range costs nothing beyond what §6.4 already computes.

## Open

- A witness pair for `Indeterminate` (#58). A pivotal literal gives a pair of completions that differ in that literal alone, the smallest pair possible, which answers the cost objection to #58's third alternative. Choosing one pair canonically for L1 is still open.
- Remedies: what would change the verdict, as abductive and contrastive explanations (#61).

## Revisit when

- A renderer or user question needs the values that resolve an `Indeterminate`, not only which unknowns matter (#61).
- W3's bound on the pivot computation is set (#38, #42).
