# 0025 — A set-valued operand takes only the set operators

**Status:** Decided, 2026-10-23 (the owner, on #102)
**Context documents:** `due2-profiles.md` §3, §4 · `due2-workflows.md` §6.4 · `due2-diagnostics.md` · `decisions/0005`, `0023` · issue #102

## Question

An operand binding may declare `due2:cardinality due2:set` (`due2-profiles.md` §3), and then a read of several values gives the set. `eq`, `neq`, the four order operators, `isAnyOf`, and `isNoneOf` take one left value (§4). The spec gave these operators no reading on a set-valued operand, and no rejection either. Only `isA` on a set-valued operand was rejected.

The answer matters to the completion key (`due2-workflows.md` §6.4). The key pairs `eq` with `neq`, and `isAnyOf` with `isNoneOf`, as complements. Under an existential reading of both sides ("some value equals", "some value differs"), both can be `T` on one set. Pairing them would then give a wrong definite verdict, as the concept-scheme gap did (`decisions/0023`).

## Decision

1. **An operator of one left value over a set-valued operand is rejected at normalisation**, with `OperatorTypeMismatch`, as `isA` already was. The operators are `eq`, `neq`, `lt`, `lteq`, `gt`, `gteq`, `isAnyOf`, and `isNoneOf`.
2. **A set-valued operand takes the set operators:** `isAllOf`, `isPartOf`, and `hasPart` (`decisions/0005`). "The set contains `v`" is `hasPart v`. "It contains all of these" is `isAllOf`. "It contains any of these" is an `odrl:or` of `hasPart`s.

ODRL already reads the operators this way. The Vocabulary defines `eq` as "a given value equals the right operand" (`profiles/vendor/w3c/ODRL22.ttl`): one value. Set-valued left operands are due2's own extension, and the operators ODRL provides for sets are the ones in item 2 above.

## Rejected

- **An existential reading, with the complement as its negation.** `eq v` would hold when some value is `v`, and `neq v` when none is. The pairing stays sound. But `neq v` would no longer mean "some value differs", which is what an author may expect. A policy accepted under that reading could not later be given another one.
- **`U` at evaluation whenever a read gives more than one value.** This accepts a constraint that can never be decided on the operand it names. The cost is an `Indeterminate` every time, and the author is never told why.

## Consequences

- `due2-profiles.md` v0.16 §4 states the rule. `due2-diagnostics.md` v0.9 extends `OperatorTypeMismatch`.
- clingo-i used to decline the shape. Now it rejects it.
- No corpus case changes. The two cases with a set-valued operand use `isAllOf` (`rl2-multi-certification`) and `isPartOf` (`oval-list-right-operand`).
- The Alloy model of claim K left set-valued operands out. With this record, no complement pair can have a set-valued operand (`formal/alloy/k_completion_key.als`).

## Revisit when

- A real policy needs a condition on a set that the set operators cannot express. Admitting a reading then would change no policy that is accepted today.
