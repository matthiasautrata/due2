# 0049 — A unit belongs to the operand's binding, and a unit no binding declares makes the comparison unknown

**Status:** Decided, 2026-10-26 (the owner, in the triage of open issues on that date)
**Context documents:** `due2-profiles.md` §2, §3, §4 · `due2-workflows.md` §3.1, §3.5, §5.4, §6.4 · `due2-diagnostics.md` · `decisions/0014` · `decisions/0016` · `decisions/0047` · issue #67

## Question

`odrl:unit` names the unit of a constraint's right operand (ODRL IM 2.2, the Constraint class). A value due2 reads for the left operand has no unit: request parameters, SOTW facts, and witness parameters are bare literals (`due2-workflows.md` §3.2, §3.3, §5.3). No section said what a unit does to a comparison. clingo-i treated it as a label and compared the values alone, so a right operand `5` with unit `ex:EUR` equalled a read `5` that was meant in USD. That is a definite verdict on data that does not support one, where due2's rule is that unknown is never false (`ways-of-working.md` §5.1).

Issue #67 listed three alternatives: the binding fixes the unit, values carry units, or the unit is a label only. `decisions/0014` #1 had already said that "a unit, when one is defined, is a type attribute too", so it is owned by the lowest layer that declares the operand. The question left open was how a constraint's unit is compared with values that carry none.

## Decision

1. **A binding may declare its operand's unit** (#67, alternative 1). `due2:unit` on a left operand names, by IRI, the unit of every value read for it. It is a type attribute (`decisions/0014` #1): stating it declares the operand, the lowest declaring layer owns it, and a higher layer that states a different unit is rejected with `RetypedOperand`. An owner that states no unit declares an operand without one, and that is as fixed as a stated unit. The producer of the value converts to the declared unit before evaluation, as it computes every other value (`due2-profiles.md` §3, *One hop*). Units are compared as IRIs, by identity. due2 converts nothing and loads no unit ontology.
2. **A constraint's unit must be its binding's.** A constraint that states `odrl:unit` with a different IRI from its binding's `due2:unit` is rejected at normalisation with `OperatorTypeMismatch`, like a right operand of the wrong kind. A constraint that states no unit is read in its binding's unit, if any.
3. **A unit that no binding declares makes the comparison `U`.** A constraint that states `odrl:unit` on an operand whose binding declares no unit is admitted, with the warning `UncheckedUnit`. Nothing says what unit the read value is in, so whatever value is read, the comparison is `U`. The part is opaque (`due2-workflows.md` §6.4, `decisions/0016`), and in `unknown_part` and `witness_part` its status is `misfit`, whatever the status of the value it reads.
4. **The corpus carries the binding's unit.** `constraint` gains `operand_unit?`, beside `range` (`decisions/0047`): the binding's `due2:unit`, absent when the binding declares none. W2 reads it to apply item 3. `constraint.unit` stays the constraint's own `odrl:unit`, and is still part of the completion key.

## Why this holds

- **Unknown is never false.** A value with no stated unit compared against `5 EUR` could be in euros or in anything else. A `T` or `F` from that comparison is a guess. `U` is what the data supports.
- **The binding is where a value's type is fixed.** `decisions/0014` made the range, cardinality, and allowed operators belong to the layer that declares the operand, because they describe the values its source produces. A unit describes those values in the same way. Putting the unit on the binding keeps every value a bare literal and needs no change to the request, the SOTW, or evidence.
- **Rejecting a unit the binding does not declare would refuse ordinary ODRL.** The baseline binds `odrl:payAmount` with no unit, because the currencies a deployment pays in vary. A rejection would make every policy that writes the CG idiom, `odrl:payAmount 5.00` with unit euro, unpublishable, and because the baseline owns `odrl:payAmount`'s type, no policy could add the unit. Admitting the policy with a warning keeps it publishable, and the `U` keeps it honest.
- **Opaque is sound.** No value fits, so a completion that paired the part with its complement would claim a verdict that no arriving value can produce. An opaque part is never paired, which can widen the verdict to `Indeterminate` and never makes it wrong (`decisions/0016`, § Why it is sound).
- **Units compared as IRIs are coarse in a safe direction.** Two IRIs for one unit, such as two vocabularies' euro, differ, so a policy that writes the other one is rejected at publish. That is an authoring error found early, not a wrong verdict.

## Rejected

- **Values carry units** (#67, alternative 2). The request, the SOTW, and evidence would each give a unit with every value, and every producer would have to state one. The binding already describes the values a source produces, so the unit belongs there.
- **The unit is a label only** (#67, alternative 3, clingo-i's earlier reading). It gives a definite verdict on mixed units.
- **Reject a unit that no binding declares.** As above, it makes the CG payment idiom unpublishable on the baseline's `odrl:payAmount`.
- **Let a higher layer add a unit the owner omits.** It would make the unit the one type attribute a higher layer may state, which breaks the rule of `decisions/0014` #2 that only the owner types an operand. A policy that needs a currency binds an operand of its own.
- **Conversion between units.** It is computation, which belongs to the producer (`due2-profiles.md` §3, *One hop*).

## Consequences

- `due2-profiles.md` v0.27: §2 lists `due2:unit` among the binding attributes and the attributes that declare an operand; §3 defines it, its default, the check against a constraint's unit, and the unchecked case, and says that the baseline's `odrl:payAmount` declares no unit; §4 says how a unit affects a comparison.
- `due2-workflows.md` v0.57: §3.1 adds `constraint.operand_unit`; §3.5, §5.4, and §6.4 make a constraint with an unchecked unit a misfit, opaque.
- `due2-diagnostics.md` v0.20: `UncheckedUnit` is a new warning of stage 2; `OperatorTypeMismatch` and `RetypedOperand` cover units.
- `schema/` gains `operand_unit` on the corpus `constraint`.
- clingo-i reads `due2:unit` as a type attribute, rejects a differing unit, and makes a leaf with an unchecked unit `u` with status `misfit`. `tools/check_corpus.py` checks units the same way and emits the warning.
- Corpus: `w3c-fs-b1`'s translation, which already binds `odrl:resolution`, declares its unit and keeps its verdicts. `w3c-fs-c1`, `w3c-fs-c2`, and `oval-duty-payment` write `odrl:payAmount` with unit euro on the baseline binding, so a payment's witness condition is `U`, and a scenario whose duty a payment fulfilled becomes `Indeterminate` between `Permit` and `Pending`. `due2-conditional-duties` drops its unit, which the case is not about. A new case covers a binding with a unit, a constraint without one on that binding, and an unchecked unit. A negative case covers a differing unit.
- #67 closes with this record.

## Revisit when

- A deployment needs two units for one operand, such as amounts in several currencies with the currency carried beside each value.
- A unit ontology, such as QUDT, is needed to tell two IRIs for one unit apart from two units.
