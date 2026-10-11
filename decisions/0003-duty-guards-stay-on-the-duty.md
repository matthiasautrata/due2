# 0003 — Duty guards stay on the duty; conditional-duty hoisting is withdrawn

**Status:** Decided, 2026-10-11
**Supersedes:** architecture §4 item 5 (conditional-duty hoisting) and its register entry §11 #3; the hoisting parts of `decisions/0002` amendment 2.
**Context documents:** `due2-architecture.md` §4 · `due2-workflows.md` §5.1–§5.5, §6.1, §6.4, §8 · `tools/check_completion.py` · `conformance/cases/due2-conditional-duties`, `due2-max-mixed`, `due2-xone-unknown`, `w3c-fs-c2`

## Finding

Architecture §4 item 5 claimed that hoisting a duty's guards into its parent "costs one extra atom per conditional duty: additive, not multiplicative". The claim holds only when a permission has a single guarded duty, which is the only case its example shows. An atom carries a fixed set of duties, and atoms combine as alternatives. So a permission with *c* independently guarded duties needs one atom per combination of guard outcomes: 2^*c* atoms, and more when a guard is compound, since its negation expands under DNF. The blowup budget's additive term `+ |conditional duties|` was wrong for the same reason.

**Evidence.** The corpus has one permission with more than one guarded precondition, the synthetic nine-guard case (512 atoms under correct hoisting). The structural concern is the shape bank contracts invite: a base permission with independently priced optional modules, each a guarded duty. Twenty modules would be 2^20 atoms. No contract of that shape is in the corpus yet. `dprod-odcs-seller-contract`'s eight guarded duties are policy-level obligations, which hoisting never touched, so they are not evidence.

**Why hoisting existed.** The recorded rationale was to avoid a question: "A duty carrying its own guard forces the evaluator to answer 'what does an inactive duty mean' … Instead the case split is lifted into the parent's guard." The question has a plain answer, and DPROD (D-ACTIVATE) and the W3C CG examples (C21: the duty Inactive, the permission Active) already give it: **an inactive duty is not owed.**

## Options

| | A — keep hoisting, cost it honestly | **B — evaluate guards on the duty (chosen)** |
|---|---|---|
| Atoms per permission | ×2^*c* for *c* guarded preconditions; needs a W1 limit on *c* (#11) | Linear: one atom per duty, as authored |
| A duty is outstanding when | it sits in an applying atom and is unfulfilled | its guards hold (`owed`) and it is unfulfilled, in Kleene logic |
| Unknown guard | a mixed variable (its guard in one atom, the negation in another): enumerated, *k* = number of unknown guard literals | moves the verdict one way only (more owed, lower verdict): uniform, two extremes, *k* = 0 unless the same literal also appears in a rule's constraint |
| Expressiveness | a limit on *c* makes natural policies inexpressible | none lost |
| Dual-role duty (obligation and precondition) | special case: guards kept for the obligation, copied into each parent | one mechanism: both roles evaluate the same guards |
| Post-exercise-state guards (§11 #3) | open: cannot be hoisted, may need rejecting | nothing to hoist; the question dissolves |
| Cost | nothing new to specify | a fourth W2 predicate (`owed`); W3's outstanding and unknown sets read it |

**B wins** on every axis except familiarity. A's only advantage, "every duty is unconditional relative to its parent", is a convenience for W3, and it costs exponential atoms and a policy limit.

## Decision

1. **W1 no longer hoists.** A precondition duty's guards stay on the duty atom as its constraints. The guard/witness split stays derived from bindings (workflows §5.2). Stage 2 keeps DNF (including `xone`), parameter substitution, instantiation, and role inheritance.
2. **W2 evaluates a precondition's guards as `owed`** (workflows §5.1–§5.2): `T` when every guard holds, `F` when one fails, `U` otherwise; a duty with no guards is owed. A root obligation's `in_force` reads the same guards, together with the policy match, so a dual-role duty is one atom with one guard evaluation per role.
3. **W3 reads `owed`** (workflows §6.1): a precondition is *open* when `owed ∧ ¬fulfilled` in Kleene logic. The outstanding set holds the open duties that are `T`; the unknown set, those that are `U`. A violated precondition removes its candidate only when it is owed (`T`); when owed is `U`, the candidate is uncertain.
4. **Monotonicity** (workflows §6.4): making `owed` more true can only add an outstanding duty or a violated-precondition removal, so `owed` is completed like a prohibition. Checked by brute force: `tools/check_completion.py`, phase 3 — 50,000 instances, guards sharing variables with rule constraints in either polarity, 0 mismatches.

## Scope — what this does not change

Workflows v0.6's canonical literals stay load-bearing. `xone` elimination still creates complementary parts (each disjunct carries the others' negations). So do authored complements across rules ("home lending may read; everyone else must petition first", written as two permissions) and a guard literal that also appears in a rule's constraint. Only the hoisting motivation is withdrawn. `due2-xone-unknown` replaces `w3c-fs-c2` as the motivating case, and v0.6 is not reopened. L9 stays an equality whenever `verdict.exact` holds, with one rewrite fewer to preserve.

## Impact

- **Verdicts change in one scenario:** the nine-guard case's "all modules unknown, all fees paid" goes from `Indeterminate` (inexact, beyond `max_mixed`) to `Permit` (exact, *k* = 0). That case is renamed `due2-conditional-duties` and kept as the linearity and exactness regression, with a scenario added where nothing is paid (genuinely `Indeterminate`, still exact).
- **`w3c-fs-c2`:** verdicts unchanged; derivations rewritten (the guard is uniform, so two extremes suffice). It loses motivating-case status.
- **Other guarded-duty cases:** unaffected. Their guards belong to root obligations, which `in_force` already evaluated.
- **New cases:** `due2-max-mixed`, rebuilt to exercise the bound with nine facts each read in both polarities by authored permission pairs; and `due2-xone-unknown`, an `xone` whose unknown operand is decided only by sharing variables.
- **Registers:** architecture §11 #3 closes (issue #12). §11 #2 / issue #11 simplifies: only DNF is exponential, and its exact-count limit is decided.

## Revisit when

- A real policy needs a guard that reads post-exercise state. Under B that is a witness condition (`due2:witnessSource`, `due2:actionTime`), not a guard; if neither fits, it is a modelling question, not a hoisting one.
- The monitoring question (workflows §9 #4) is specified. It will read `owed` for obligations too; check that the predicate carries over unchanged.
