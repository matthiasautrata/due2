# 0024 — A `dateTime` has a timezone; a `date` has none

**Status:** Decided, 2026-10-23 (the owner, on #101)
**Context documents:** `due2-profiles.md` §4 · `due2-workflows.md` §5.4, §6.4 · `due2-diagnostics.md` · `decisions/0016`, `0023` · issue #101

## Question

`due2-profiles.md` §4 orders `dateTime` and `date` values "within the kind". XSD orders them only partially (XSD 1.1 Part 2 §3.3.7, §3.3.9). A value with a timezone and one without are incomparable when they lie within 14 hours of each other, and whether they are equal is undetermined as well. What does an operator give on such a pair?

The answer matters to the completion key (`due2-workflows.md` §6.4). The key pairs `eq` with `neq`, `lt` with `gteq`, and `lteq` with `gt` as complements. If both members of a pair could be `F` on one value, pairing them would give a wrong definite verdict, as the concept-scheme gap did (`decisions/0023`).

## Decision

1. **Each kind has one shape.** A `dateTime` carries a timezone, and a `date` carries none. Within that shape XSD's order is total, so every complement pair has opposite truth values. `xsd:dateTimeStamp`, which requires a timezone, is the natural range for an operand of this kind.
2. **A policy literal of the other shape is rejected at normalisation.** A right operand is rejected with `OperatorTypeMismatch`, and a `dprod:deadline` with `InvalidTiming`.
3. **A read value of the other shape does not fit the operator.** The part is `U`, with status `misfit` (`due2-workflows.md` §5.4). A misfit part is opaque, so the key never pairs it (`decisions/0016`). This holds for every operator, not only the order operators.
4. **The input instants have a timezone too.** These are `request.at`, `sotw.effective_at`, activations, and evidence times (`due2-workflows.md` §3). A deadline is compared with them.

## Rejected

- **`F` for every operator on an incomparable pair.** This is what an XSD order test returns. But it makes `lt` and `gteq` both `F` on one value, which breaks the pairing. It also treats an unknown order as a false condition.
- **An implicit timezone**, fixed by a profile or by the evaluation, as XSD allows. The order would be total, but the result would depend on an input the policy does not show. That input needs a place to be declared, and replay must record it. No corpus case or known source needs it.
- **`U` for an incomparable pair, and no shape rule.** This is sound, but a policy literal without a timezone would be admitted and could then never be compared reliably. Rejecting it tells the author at once.

## Consequences

- `due2-profiles.md` v0.16 §4 states the shape. `due2-workflows.md` v0.33 §5.4 lists the misfit, and says that the input instants have a timezone. `due2-diagnostics.md` v0.9 extends `OperatorTypeMismatch` and `InvalidTiming`.
- clingo-i used to decline both shapes. Now it rejects a right operand or deadline with the wrong shape, and gives `u` for a read value with the wrong shape. An input instant with the wrong shape still declines.
- `tools/check_corpus.py` requires a timezone on the instants of a scenario. Every corpus instant already had one.
- `oval-untyped-datetime` keeps its rejection. Typing its literal would no longer be enough, because the literal has no timezone.
- The Alloy model of claim K assumed each ordered kind is totally ordered. That assumption now follows from this record (`formal/alloy/k_completion_key.als`).

## Revisit when

- A real source supplies only timestamps without a timezone. An implicit timezone could then be declared on the operand's binding (`due2-profiles.md` §3), where the policy shows it and replay records it.
