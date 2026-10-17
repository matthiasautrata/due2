# 0010 — The trace is the explanation

**Status:** Decided, 2026-10-16
**Context documents:** `due2-workflows.md` §3.5–§3.7, §6.4, §7, §8 (L10) · `odrl-compound-to-atomic-normalization.md` §7 · `correctness-strategy.md` §4.1, §4.3, §4.6 · `decisions/0006` §5 · `decisions/0007` · issues #57, #58, #59

## Question

A verdict alone does not explain a decision. Every evaluation has to say why. That includes groups of atoms that belong together (one authored rule, a permission and its duties), policies that are evaluated together, and the evaluations of one case over time. What structure carries the explanation, and what must hold of it so that a readable form can be produced later?

## Decision

Workflows §3.7:

1. **The explanation is the trace.** Every evaluation that returns a verdict emits its trace (§7). The explanation is the part of the trace reachable from `verdict`, through references the relations already carry, together with the evaluation's inputs and the lineage. It is read, never computed alongside: reading it never re-runs W2 or W3 and never reads the world.
2. **Explicability is a law** (L10). Every reference resolves. A finding's truth is its predicate's connective over its `basis`. Every atom in `verdict_basis` or `eliminated` has its findings and an authored source. Being parseable means the derivation is typed relations under the canonical encoding (`decisions/0007`). Being explainable means L10 holds.
3. **Groups are keys, never inferred.**
   - Atoms of one rule share `source_rule` and the lineage's selection tuple.
   - A permission's duties are linked by `edge`, `alternative`, and `alt_duty`.
   - Policies evaluated together are told apart by `policy_id`, and by the conflict rule each elimination names.
   - The evaluations of a case are ordered by its `seq`. What changed between two of them is a per-relation set difference of their canonical traces.
4. **Rendering is later.** Prose, pages, and screens are a presentation step over the derivation. A renderer may select and order; it never adds a reason. A rendering that needs what the derivation lacks reveals a trace defect.
5. **The corpus asserts the explanation at the authored level.**
   - Atoms are named by their rule or duty IRI, as `frontier` and `obligations` already are (#57).
   - clingo-i returns the same projection (#59), so the explanation has an oracle as the verdict does.
   - Full traces, with atom ids, are pinned by L1 and replay.

## Rejected

- **English, or free-text reasons, in the trace.** They cannot be checked, compared across backends (`decisions/0006` §5), or diffed between evaluations.
- **A separate explanation log written beside the trace.** Two records of one decision can disagree. The trace is already the record that replay reproduces.
- **Extending L9 to the basis now.** The pipeline's `verdict_basis` and clingo-i's projection should agree, but nothing yet shows that DNF disjuncts project back to the authored rules without loss. The corpus checks the basis until a pipeline exists to compare.

## Open

- A witness for `Indeterminate`: the completions whose verdicts differ (#58).

## Revisit when

- A renderer, an audit question, or a cross-evaluation diff needs something the derivation does not hold. The fix is a trace relation, under L1 and L10.
