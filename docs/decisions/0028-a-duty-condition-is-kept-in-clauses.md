# 0028 — A duty's condition is kept in clauses on its one atom

**Status:** Decided, 2026-10-24 (the owner, on #109)
**Context documents:** `due2-workflows.md` §3.1, §3.5, §4, §5.1–§5.3, §6.4, §8 L9 · `due2-architecture.md` §4 · `decisions/0003`, `0016` · `docs/briefings/due2-review-2026-10-24.md` R01 · issue #109

## Question

W1 stage 2 puts each constraint in disjunctive normal form (DNF) and makes each disjunct an atom (`due2-architecture.md` §4 item 3). For a root rule this is right, because root atoms are alternatives: any one of them may match the request. For a duty it is wrong. W1 makes every atom of a nested duty a child of its parent, and every child is owed (`due2-workflows.md` §4, *Position decides conjunction*). A duty conditioned on `or(a, b)` therefore became two duties, and both were owed. A root obligation split the same way became two obligations. The `constraint` relation was "conjunctive per atom", so the corpus had no way to state one duty with alternative conditions.

The spec already assumed otherwise in two places. `due2-workflows.md` §5.2 rejects only a disjunction that mixes guards with witness conditions (`MixedDutyConstraint`), so a disjunction of guards alone, or of witness conditions alone, is admitted. L9 says that duty guards are not rewritten. The external review found the gap (R01), with this example. A permission's compensation duty has the witness condition `amount eq 5 or amount eq 10`, and one witness has amount 5. Read as authored, the duty is fulfilled and the verdict is `Permit`, which the review's interpreter returned. Split into two duties, the amount-10 duty is outstanding and the verdict is `Pending`.

## Decision

1. **A duty stays one atom.** W1 does not split a duty atom on its constraint. Its identity, its `duty` tuple, and its instance are those of the authored duty after stage 1's expansion.
2. **A duty atom's constraints are grouped into clauses.** `constraint` gains the field `clause: Count`. It is present on every constraint of an `Oblige` atom and absent on a `Permit` or `Forbid` atom, whose disjuncts W1 still makes separate atoms. A duty's constraint is a conjunction of pure guard parts and pure witness parts, since `MixedDutyConstraint` rejects any disjunction or negation that mixes the two (`due2-workflows.md` §5.2). W1 therefore puts the guards' conjunction and the witness conditions' conjunction in DNF separately, and each disjunct becomes one clause. A clause holds constraints of one kind only, and its number is unique within the atom.
3. **A kind's value is the Kleene disjunction of its clauses' conjunctions.** A duty is owed, or its guards hold for `in_force`, when some guard clause holds: `T` if some clause is `T`, `F` if every clause is `F`, `U` otherwise. A duty with no guard clause has no guards, and is owed whenever its parent applies, as before. A witness satisfies the witness conditions when it satisfies some witness clause, by the same rule, and a duty with no witness clause is satisfied by any witness. The `fulfilled` finding is still the Kleene disjunction of that value over all witnesses (`due2-workflows.md` §5.3).
4. **The basis and `unknown_part` read clauses as they read root atoms.** For `T`, the basis records every part of each clause that holds. For `F`, it records the failing parts of every clause. For `U`, it records the `U` parts of each clause that is not `F`. `unknown_part` names a `U` part when some root atom or duty clause that reads it is `T` or `U`, so a leaf is named under the same rule whether its tree sits on a root rule or on a duty (`decisions/0016`).

## Why this holds

- **Completion is unchanged.** The variables of `due2-workflows.md` §6.4 are literals, not clauses. A guard clause, like a root atom, is a conjunction of parts that are identical or complementary to authored ones, so the completion key is unaffected. A completion re-derives each clause by Kleene conjunction and each kind by Kleene disjunction. The monotonicity proof of `due2-workflows.md` §6.4 reads the `owed` and `fulfilled` findings, never their parts: making `owed` more true can only add an outstanding duty or a violated-precondition removal (`decisions/0003` #4), and making `fulfilled` more true can only remove one. Both hold however a finding is computed from its parts.
- **L9 is unchanged.** DNF is a strong Kleene equivalence, and the clauses of one kind are disjoined back into one finding. So a duty's finding is `U` exactly when its authored tree is, which is the condition L9 already relies on for root atoms. L9's sentence that duty guards "are not rewritten" now says that they are rewritten within the duty's own atom.
- **Instances are unchanged.** One authored duty, with one binding, still gives one `binding_key`, one instance, and one `fulfilled` finding.

## Rejected

- **Copy the parent per disjunct.** Each permission would get one atom per disjunct of each of its duties' conditions, so a permission with *c* disjunctive duties would need a product of atoms. `decisions/0003` rejected the same blowup for hoisted guards. A root obligation has no parent to copy.
- **Reject a disjunctive duty condition.** This is sound, but it rejects natural policies, such as "consent is owed when the purpose is marketing or the audience is public" and "pay at least 5, or pay with a voucher". It would also contradict `due2-workflows.md` §5.2, which admits a disjunction that does not mix guards with witness conditions.
- **Keep the duty's constraint as a tree** in a new relation. This is exact, but it adds a recursive relation that W2 would walk, where clauses give the same meaning in a flat form, of the kind the corpus already uses for root atoms.

## Consequences

- `due2-workflows.md` v0.36 states the field, the clause rule, and the basis in §3.1, §3.5, §3.6, §4, §5.1–§5.3, §6.4, and L9. `due2-architecture.md` v0.11 §4 item 3 says that W1 splits only root atoms. The port schema is regenerated, and `check_invariants` in `tools/harness/vectors.py` checks that `clause` is present exactly on the constraints of `Oblige` atoms.
- clingo-i reads the authored tree (`spikes/clingo-i/lp/constraint.lp`), so it already gave these verdicts and needs no change.
- `due2-duty-disjunction` pins the reading: a duty whose guards and witness conditions are both disjunctions over different operands, with five scenarios. Under the old lowering, scenario 1 would be `Pending` and scenario 2 `Indeterminate`, where both are `Permit`.

## Revisit when

- A policy needs a duty whose condition is a disjunction that mixes a guard with a witness condition. That is a `MixedDutyConstraint` rejection today, and this record does not change it.

## Amendment (2026-10-26, the clause moves to `duty_constraint`)

A named constraint can be attached to several atoms, so its attachment is no longer a field of `constraint` (`decisions/0036`). The clause number of item 2 is a field of `duty_constraint (atom_id, clause: Count, constraint_id, scope: Enum)`, the relation that attaches a constraint to an `Oblige` atom, and a `Permit` or `Forbid` atom's constraints are attached by `atom_constraint`, which has no clause (`due2-workflows.md` §3.1). The meaning of a clause is unchanged, and `check_invariants` checks that each relation names an atom of its effect.
