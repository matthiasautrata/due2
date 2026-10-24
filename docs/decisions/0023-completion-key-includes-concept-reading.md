# 0023 — The completion key includes the concept reading

**Status:** Decided, 2026-10-23 (the owner, after the Alloy model of claim K found a counterexample, #84)
**Context documents:** `due2-workflows.md` §6.4 · `due2-profiles.md` §3, §4 · `decisions/0012`, `0015` · `correctness-strategy.md` §4.8 · `formal/alloy/k_completion_key.als` · issue #84

## Question

Two completed parts share one completion variable when they have the same key: scope, operand binding, unit, and right operands (`due2-workflows.md` §6.4). Parts with equal operators share it with the same polarity, and parts with complementary operators, such as `eq` and `neq`, with opposite polarities (`decisions/0012`). The pairing is sound only if two parts with one key make the same comparison, so that complements always have opposite truth values.

The key compares the binding, not the operand IRI, so two operands bound to one property are paired. But an operand's concept schemes belong to the operand (`decisions/0015` #2), and they change what `eq` means: with a scheme, `eq c` holds for every value ⊑ `c` under `skos:broader`; without one, only for `c` itself. Should two operands on one property, one with a scheme and one without, share a variable?

An example. `ex:x` has no scheme, and `ex:y` is bound to the same state property with scheme `ex:s`, in which `ex:low` is below `ex:top`. Permission `ex:r1` has `ex:x eq ex:top`, and permission `ex:r2` has `ex:y neq ex:top`. The key as `due2-workflows.md` v0.31 states it makes them complements over one variable, so in every completion exactly one of the two permissions applies.

| Value of the property | `ex:x eq ex:top` | `ex:y neq ex:top` | Verdict |
|---|---|---|---|
| `ex:top` | `T` | `F` | `Permit` |
| `ex:low` | `F`: not identical | `F`: `ex:low` ⊑ `ex:top` | `NotApplicable` |
| unresolved, one shared variable: both completions | `T` or `F` | the opposite | `Permit` |

With the property unresolved, the shared variable gives `Permit`, which `ex:low` refutes: a wrong definite verdict.

The Alloy model's `run SchemeGap` found the instance, and clingo-i reproduced it. clingo-i's brute-force differential shares the key with clingo-i, so it could not see the gap (`decisions/0012`, Consequences), and no corpus case puts two operands with different schemes on one property.

## Decision

1. **The key includes the concept reading:** whether the left operand has a concept scheme. Two parts share a variable only when both operands have one or neither has.
2. **The reading is whether there is a scheme, not which schemes.** ⊑ is one predicate over every `skos:broader` edge, not scoped to a scheme (`decisions/0015` #5). A scheme decides only that `eq` is ⊑, and whether a value is valid. A value outside an operand's schemes is `invalid` (`decisions/0015` #4), which makes the part opaque, never a definite value that contradicts the pairing.

The Alloy model checks the key with this change sound at scope 6 (`check KeySound`, `formal/alloy/README.md`).

## Rejected

- **Compare the schemes themselves.** Two operands would share a variable only with the same set of schemes. This is sound too, and stays sound if ⊑ were ever scoped to a scheme. But it gives up sharing between operands whose layers add different schemes (`decisions/0015` #6), which compare the same way, and the cost is an `Indeterminate` where the policy decides.
- **Reject the shape at normalisation.** Two operands on one property, one with a scheme and one without, are a legitimate shape. A baseline operand may compare strings by code point while a policy's operand compares concepts (`decisions/0015` #7). Rejecting them would refuse policies that have one meaning.

## Consequences

- `due2-workflows.md` v0.32 §6.4 adds the concept reading to the key.
- clingo-i adds `leaf_attr(C, concept)` to the key (`spikes/clingo-i/lp/completion.lp`). `test_concept_scheme_in_key` pins the example: `Indeterminate` while the property is unresolved, and `NotApplicable` at `ex:low`.
- `decisions/0012`'s Status line names this record: its #1 (same polarity) and #2 (opposite polarity) apply only when the concept reading is also the same.

## Revisit when

- ⊑ is scoped to a scheme, or cross-scheme mappings are read (`decisions/0015` #5). The key would then need the schemes themselves.
