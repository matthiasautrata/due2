# 0035 — A part read against a witness is keyed by its witness

**Status:** Decided, 2026-10-25 (the owner, on #120)
**Context documents:** `due2-workflows.md` §3.5, §3.7, §5, §5.2, §5.3, §5.4, §6, §6.4, §8 (L2, L10) · `schema/` · `decisions/0010` · `decisions/0016` · `decisions/0028` · `docs/briefings/due2-review-2026-10-25.md` F01 · issue #120

## Question

W2 evaluates a duty's witness conditions once for each witness, the evidence records that pass the witness test (`due2-workflows.md` §5.3). One constraint can therefore be read several times in one finding, once per witness, with a different value and a different input status each time. The trace relations that record parts, as `due2-workflows.md` v0.42 declared them, have no field for the witness:

```text
basis          (atom_id, kind: Enum, ref | truth: Truth)
unknown_part   (atom_id, predicate: Enum, kind: Enum, ref | input, status: Enum)
```

The follow-up review (F01) gave an example. A duty requires a payment of 5. Evidence `e1` states no amount, so the amount is `missing`. Evidence `e2` states an IRI where a decimal is required, so the amount is `invalid`. Both make the constraint `c` `U`, and the duty's `fulfilled` finding is `U`. `due2-workflows.md` §5.4 step 3 requires both reads in `unknown_part`, each with the status of what it read, but both rows have the key `(d, fulfilled, constraint, c)`. The relation cannot hold them.

`basis` has the same gap, and a second one. It needs the witness for the same reason. It also has no predicate, although a duty has up to three findings (`owed`, `in_force`, `fulfilled`), each with a basis of its own. A duty that is both a precondition and a root obligation, whose guards hold, while no `Permit` or `Forbid` of its policy matches the request, has `owed` `T` with its guard parts as basis, and `in_force` `F` (`due2-workflows.md` §5.2). Without the predicate, the guard rows read as `in_force`'s basis too, and the conjunction of their truths gives `T`, against the finding.

The gap is in the explanation, not in W3. W3 completes a `U` `fulfilled` finding as one variable of its own (`due2-workflows.md` §6.4), so it reads no part beneath it.

## Decision

1. **Two relations hold the parts of a duty's witness conditions, per witness:**

   ```text
   witness_basis  (atom_id, witness, kind: Enum, ref | truth: Truth)
   witness_part   (atom_id, witness, kind: Enum, ref | input, status: Enum)
   ```

   `witness` is the witness's `evidence_id`. A row records one part of one witness clause (`due2-workflows.md` §5.2), evaluated against that witness, and `ref` is its constraint. Every part of a witness clause is a constraint that reads the witness: a constraint that reads anything else is a guard (`due2-workflows.md` §5.2), so the relations have no `kind` field. The predicate is always `fulfilled`, so they have no predicate field either.
2. **Both follow the rules of `basis` and `unknown_part`, per witness.** For each witness, `witness_basis` records every part of each clause the witness satisfies when the finding is `T`, the failing parts of every clause when it is `F`, and the `U` parts of each clause that is not `F` for the witness when it is `U` (`due2-workflows.md` §5.2). When the finding is `T` or `U`, `witness_part` names a `U` part under a witness exactly when a clause that reads it is `T` or `U` for that witness, with the status of what it read: the liveness rule `unknown_part` follows (`decisions/0016` and its amendment, `decisions/0028`).
3. **`basis` gains `predicate` in its key:** `basis (atom_id, predicate: Enum, kind: Enum, ref | truth: Truth)`. `basis` and `unknown_part` keep every part not recorded under item 1, including the `evidence` part that records whether a record is a witness.
4. **W2's signature lists what it writes:** `unknown_part`, which it omitted, and the two new relations. W3 reads neither new relation.

## Why this holds

- **A part is identified by where it was evaluated.** `due2-workflows.md` §5.3 evaluates the witness conditions once per witness, so a witness clause's part has one value per witness, and the witness belongs to its identity. With the witness in the key, every read has a row, and no row has to be chosen over another.
- **The explanation never re-runs W2.** `due2-workflows.md` §3.7 says the explanation is read from the trace, "never computed alongside it", and L10 asks that every finding follow from its basis. Without the witness, a reader learns that some witness's amount was missing but not which record to correct, and cannot check that `fulfilled` is the disjunction over witnesses of its clauses.
- **Each finding has its own basis.** L10 checks a finding against its basis by its predicate's connective, and the basis rule picks parts by the finding's value, so two findings of one atom pick different rows. The owed-but-not-in-force duty under *Question* shows the check failing without the predicate. `unknown_part` already keys by predicate for the same reason.
- **W3 is unchanged.** W3 completes a `U` `fulfilled` finding as one variable (`due2-workflows.md` §6.4) and reads its `instance` status (`due2-workflows.md` §5.3), so the parts beneath it never reach W3. The relations serve the explanation and L10 only, and W3's inputs, and law L2's list of them, stay as they were.
- **The keys stay required.** `tools/gen_schema.py` rejects an optional key field, because the canonical order sorts tuples by key, field by field (`due2-workflows.md` §2), and an absent field has no place in that order. Separate relations keep every key required without a placeholder witness.

## Rejected

- **Add the status to `unknown_part`'s key.** It is a one-field change, and clingo-i's `unknown_part(X, Input, S)` and the corpus's `unknown_parts` entries are already keyed by rule, input, and status. But the trace would not say which record to correct, and `basis` would still not show that `fulfilled` follows from its parts.
- **Keep the worst status.** Ranking `invalid` above `missing` is a rule no source gives, and it discards a read that `due2-workflows.md` §5.4 requires.
- **An optional `witness` field on `basis` and `unknown_part`.** An optional key field has no place in the canonical order, and a placeholder value for parts not read against a witness would be a sentinel every reader must know.

## Consequences

- `due2-workflows.md` v0.43 states the two relations in §3.5, their place in the explanation in §3.7, W2's signature in §5, the basis rule in §5.1–§5.3, the recording rule in §5.4, and law L10.
- `schema/collections.schema.json` is regenerated with the two relations and `basis.predicate`.
- The corpus's `expected.unknown_parts` is a projection of `unknown_part` and `witness_part` to `{ref, input, status}`, and `conformance/README.md` says so. Its format is unchanged: `e1`'s and `e2`'s reads are two entries.
- The relation-level vectors (#37) are to pin the two-witness pair, and clingo-i's relation-level face (#41) is to emit the new relations.

## Revisit when

- The trace gives a recurring duty's findings an occurrence. An occurrence has its own instance and evaluates its witnesses separately (`due2-workflows.md` §5.3, *Recurrence*), but `finding`, `basis`, and `unknown_part` have no occurrence field either, so the gap is not this record's: whatever key gives `finding` its occurrence gives these two relations theirs (#119, #80).
