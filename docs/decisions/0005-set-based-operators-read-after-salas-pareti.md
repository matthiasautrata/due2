# 0005 — Set-based operators with lists are read after Salas–Pareti, with a warning

**Status:** Decided, 2026-10-11
**Context documents:** `due2-profiles.md` §4 · `odrl22-conformance.md` §2 (erratum) · `conformance/odrl22-shape.ttl` · `oval-list-right-operand` · issue #31

## Finding

The ODRL Vocabulary calls six operators set-based (§3.16.7–3.16.12: `isA`, `hasPart`, `isPartOf`, `isAllOf`, `isAnyOf`, `isNoneOf`) and allows a list right operand for exactly those (§3.14.7; IM §2.5.1). due2's shape and `due2-profiles.md` §4 admitted lists only for `isAnyOf`, `isNoneOf`, and `isAllOf`. That was a defect, now fixed.

Validity is settled, but meaning is not. Each operator's definition is one sentence written for a single right operand ("a given value is contained by the right operand"). The published formal semantics disagree:

| Source | `isPartOf` | `hasPart` | `isA` | Logic |
|---|---|---|---|---|
| Bonatti, Fornara, Harth 2025 (OPAL@ESWC, CEUR 3977), Table 1 | ∈ | ∋ | ∈ | two-valued |
| Salas, Pareti et al. 2025 (arXiv 2509.05139), §3 | ⊂ | ⊃ | classes(i) ⊇ {v} | two-valued; null is false |
| Mustafa et al. 2026 (arXiv 2602.19883) | downward closure, one value | upward closure, one value | downward closure, one value | Kleene |

Salas–Pareti depart from the earlier reading deliberately (§5: "differentiating between isA, isPartOf and isAnyOf"). The W3C ODRL workshop's open-issues paper lists the question (Rodríguez-Doncel 2026, R-V2: "Improve definitions to avoid ambiguity with set-membership operators").

## Options

- **A — reject a list on the three contested operators** until the WG resolves R-V2. This follows architecture §1 most literally, but it refuses valid ODRL that has a well-defined published reading.
- **B — adopt the most reasonable published reading, and warn (chosen).**
- **C — membership (Bonatti).** This collapses `isPartOf` into `isAnyOf` and leaves `hasPart` with a list degenerate (the left contains the list itself).

## Decision

1. **Adopt Salas–Pareti**, which is also what OVAL implements, with three adjustments:
   - inclusion is non-strict (⊆, ⊇);
   - set inclusion generalises to the declared `partOf` closure:
     - `isPartOf` holds when every left value is part of some right value;
     - `hasPart` holds when every right value is part of some left value;
     - `isA` holds when the left value is an instance of every listed class;
   - logic stays Kleene: a missing or `invalid` value gives `U` (ways-of-working §5.1).

   Under an identity closure these readings are exactly Salas–Pareti's.
2. **Warn, do not reject.** A list right operand, or a set-valued left operand, on `isPartOf`, `hasPart`, or `isA` is accepted with the warning `ContestedOperatorReading`. A warning is a diagnostic that does not reject, and the trace carries it. This qualifies architecture §1 ("never accepted and approximated") without breaking it: the reading is a stated choice with a published source, not an approximation, and the warning makes the choice visible wherever it applies.
3. **Revisit** if the ODRL WG or CG resolves R-V2 differently. The warning marks every affected policy.

## Addendum: `isAllOf` (issue #33, decided 2026-10-11)

due2 has left ⊇ right; Bonatti has =, Salas–Pareti have ≡, and Mustafa has "below every right value". **due2 keeps ⊇: the left covers the listed values and may hold more.** This departs from the Salas–Pareti reading adopted above, deliberately: the Vocabulary's wording requires every listed value, not the absence of others, and equality would make an extra purpose or certification defeat a constraint that only asks for the listed ones. No warning is raised (`due2-profiles.md` §4).

Corpus cases for `hasPart` and `isA` with a list: #32.
