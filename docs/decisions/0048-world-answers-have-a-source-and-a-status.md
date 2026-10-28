# 0048 — A world-edge answer has a source and a status, evidence edges are planned, and a plan over the read limit is refused

**Status:** Decided, 2026-10-26 (the owner, in the triage of open issues on that date); notes 2026-10-27 (#150), 2026-10-28 (`decisions/0050`)
**Context documents:** `due2-workflows.md` §3.3, §3.5, §6.4, §7.1, §9 · `due2-platform.md` §2.4, §2.5, §2.6, §3.1 · `due2-profiles.md` §4, §6 · `decisions/0016` · `decisions/0040` · `decisions/0043` · `decisions/0047` · issues #34, #95, #142, #143

## Question

`decisions/0043` made each world-edge answer an event on the case: the edges on the paths up from one entity in one module. `decisions/0047` named the modules and listed the entities whose edges `plan` names. Four questions were left:

- **A lookup that fails** (#95). Hierarchy is closed-world: an edge that is not recorded does not hold, so a part that needs it is `F`. A catalog that does not answer therefore makes a prohibition on a classification certainly not apply, where it should be unknown (`ways-of-working.md` §5.1). An answer had no status in which to record the failure.
- **Several sources for one module** (#143). An answer named its module and entity but not its source, so two sources registered for one module overwrote each other, while facts are kept per source (`decisions/0040`).
- **Edges that evidence comparisons read** (#142). A duty compares an evidence issuer with its attester and an actor with its bearer, and a witness-source operand may compare a witness's values under a hierarchy. Those values are known only once evidence is submitted, so no plan listed their edges, and the comparisons read only the edges the case held.
- **The read limit** (#34). A plan larger than the shell's `max_reads` either refuses the request before a case is created, or creates the case and evaluates with the excess `unresolved`.

## Decision

1. **A world-edge answer is one source's answer, with a status.** The SOTW holds `closure_answer (module, entity, source | status: Enum)`, with `status ∈ {resolved, unresolved}`, beside `closure`. `resolved` means the source answered, with the edges it holds above the entity, possibly none. `unresolved` means the source could not be asked or did not answer, and its answer holds no edges. A `closure` event records one source's answer: its module, entity, source, status, and edges. The SOTW of an evaluation takes, for each module, entity, and source, the latest answer, and its `closure` is the union of their edges.
2. **A failed answer makes a hierarchy comparison `U`, never `F`.** For `a ≠ b`, `a ⊑ b` is `T` when a chain of edges in the union of the SOTW's `closure` and the corpus's `closure` leads from `a` to `b`; otherwise `U` when some answer is `unresolved` for `a` or for an entity that a chain of edges reaches from `a`; otherwise `F`. An answer counts in any module. A module with no registered source has no answers, and the corpus's edges are then all there is: registering no source for a module is the deployment's statement that the policies hold that hierarchy.
3. **A hierarchy part that is `U` for this reason is opaque.** It is not completed (`due2-workflows.md` §6.4). In `unknown_part` and `witness_part` its `status` is `unresolved`, and its `input` is what the part reads, as for every other part: `odrl:target`, a party function, or an operand's property. For a party comparison of the witness test, the part is the record's `evidence` part, and its `input` is the duty's party function that the comparison reads (`due2-workflows.md` §5.3).
4. **Evidence edges are planned.** `Reads` gains two relations. `read_evidence_edges (module, field: Enum)`, with `field ∈ {issuer, actor}`, names an evidence field whose value a duty compares under the party closure: `issuer` when some duty atom has an attester, `actor` when some duty atom has a bearer. `read_witness_edges (module, property)` names a witness-source property whose values a hierarchy comparison reads, in the modules that `decisions/0047` assigns to the comparison. When evidence is submitted, the shell records it, fetches the edges these relations name above its values, and only then evaluates.
5. **A plan over the read limit is refused.** `max_reads` is a limit the deployment sets on the shell, like its retry limit (`due2-platform.md` §3.1, step 10), not a constant of the evaluation. It counts the tuples of the plan: one per relation tuple, so a `read_fact_edges`, `read_evidence_edges`, or `read_witness_edges` tuple counts once, however many values it later fans out to. When the plan of a complete request exceeds it, the orchestrator refuses the request with `Error` and creates no case.

## Why this holds

- **A failed lookup must not decide a verdict.** Before this record, a catalog that timed out gave the same `closure` as a catalog that said the dataset has no classification, and the first is unknown while the second is false. `unresolved` keeps the two apart, as `fact` already does for state properties (`due2-workflows.md` §3.3).
- **Two statuses suffice.** A module that does not hold the entity answers `resolved` with no edges, which `decisions/0047` already relies on when it lists one value in two modules. Nothing about an edge set is `missing`, `invalid`, or in `conflict`: edges from several sources are combined by union, because an edge that one source knows is not contradicted by another source that does not know it.
- **Only answers at or above the narrower side matter.** `a ⊑ b` follows edges up from `a`, through any entity `c` that the recorded edges reach. A missing edge that would extend such a chain starts at `a` or at such a `c`, so only their answers can hide it. An unresolved answer for `b`, or for an entity not above `a`, hides only edges that no chain from `a` to `b` uses.
- **Any module counts.** W2 reads one hierarchy, the union of every module's edges (`decisions/0047`), so an edge that a failed source would have held could extend a chain whatever its module. Counting a module that holds no edges of the comparison's kind is sound, and costs at most an `Indeterminate`.
- **Opaque is sound and costs at most an `Indeterminate`.** An opaque part is never paired with another, so completion over it admits every combination, and the verdict can only be wider than with a completion variable (`decisions/0016`, § Why it is sound). A hierarchy relation is `T` or `F` in every world, so completing it would also be sound. It is left out because no corpus case needs it, and pairing hierarchy parts would need a key beside the constraint key of `due2-workflows.md` §6.4.
- **Planned evidence edges keep the rule that W2 reads only what was planned.** `decisions/0047` named the evidence comparisons as the one exception. The two relations name them the way `read_fact_edges` names fact values: by the field or property, with the values found when the data arrives.
- **Refusing is the simpler outcome.** It records nothing half-evaluated, and the plan of a complete request is known before the case is created (`due2-platform.md` §3.1, step 6). Evaluating with the excess `unresolved` would need a rule for which reads are the excess, and each choice of rule changes the verdict.

## Rejected

- **An unresolved hierarchy lookup is an `Error` for the case** (#95, alternative 2). One failed source would block every verdict of the case, including verdicts the failed edges cannot change.
- **Catalog completeness as an operational requirement only** (#95, alternative 3). A requirement nobody can check at evaluation would leave the wrong `Permit` in place whenever it is broken.
- **One source per world module** (#143). It would treat world edges differently from facts and forbid two catalogs.
- **Fetching evidence edges without planning them.** The shell would decide what to fetch from rules that no relation states, and W2's reads would no longer be within the plan.
- **Counting each value of a fact against `max_reads`.** The count would be known only after the case exists, so exceeding it could not refuse the request.

## Consequences

- `due2-workflows.md` v0.54: §3.3 adds `closure_answer`, the comparison rule, the two `Reads` relations, and the read limit as decided; §3.5 says which `U` parts are completed; §5.3 and §5.4 say how a hierarchy comparison made `U` by a failed answer is recorded, and §6.4 counts it as opaque; §7.1 records one source's answer per `closure` event; §9 #9 is resolved.
- `due2-platform.md` v0.16: `edges` returns one answer per source with its status (§2.4); a catalog that does not answer makes a classification part `U`, while one that answers and omits an edge still makes it `F` (§2.5); `submit_evidence` fetches the planned evidence edges (§2.6); step 6 refuses a plan over `max_reads` (§3.1); §5 #2 is resolved.
- `due2-profiles.md` v0.26: §4 and §6 state the exception to the closed-world reading.
- `due2-platform.md` §3.1, step 6, plans the complete request and checks `max_reads` before it creates the case.
- `schema/` gains `closure_answer` in the SOTW and the two relations in `Reads`.
- In a corpus case, `sotw.closure` lists edges from resolved answers. No case records an unresolved answer, which is a coverage gap (`conformance/README.md`), so clingo-i reads hierarchy as closed-world throughout (`spikes/clingo-i/DESIGN.md` § Negation as failure).
- `decisions/0043` and `decisions/0047` carry notes.
- The fan-out of a set-valued fact or of many pieces of evidence is not bounded by `max_reads`.
- An entity that a corpus edge reaches from a planned entity has no answer, so an `unresolved` answer cannot mark it and the world edges above it are not fetched. That is a gap in the plan, not in this record's rule (#144).

## Revisit when

- A policy needs a definite verdict that only a completion over a hierarchy part gives.
- A fact's values or a case's evidence fan out to more answers than a source can serve.

**Note (2026-10-27, #150):** item 3's two party functions can be `U` for one record: its `e.actor ⊑ bearer` and its `e.issuer ⊑ attester` comparisons each read an `unresolved` answer. That is two `unknown_part` rows for one atom, predicate, kind, and `ref`, which the key `(atom_id, predicate, kind, ref)` did not allow. `due2-workflows.md` v0.58 adds `input` to the key, so the part has one row per party function that makes it `U`. Every other part reads one input, so its rows are unchanged.

**Note (2026-10-28, `decisions/0050`):** in item 2, "the corpus's `closure`" is the `closure` of the policy whose entry makes the comparison. In *Any module counts*, "W2 reads one hierarchy" is one hierarchy per policy: the union of every world module's edges with that policy's own.
