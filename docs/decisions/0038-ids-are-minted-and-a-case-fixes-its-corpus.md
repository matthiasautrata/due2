# 0038 — Ids are minted once, and a case fixes its corpus

**Status:** Decided, 2026-10-26 (the owner, on #107)
**Context documents:** `due2-workflows.md` §2, §3.1, §3.3, §3.5, §4, §5.2, §5.3, §6.3, §7.1 · `odrl-compound-to-atomic-normalization.md` §3, §5, §6, §7, §8, §10 · `due2-platform.md` §2.2, §2.3, §2.6, §2.11, §3.3 · `due2-profiles.md` §7 · `decisions/0007` · `decisions/0008` · `decisions/0032` · `decisions/0036` · `decisions/0037` · issues #107, #121, #133

## Question

In `due2-workflows.md` v0.47, every id that no author chose was computed from content, so that a separate run could compute it again:

- stage 1 hashed an anonymous node from its parent, the predicate that reaches it, and its content (`anon_node_uid`), and an expanded rule from its source rule and selection (`atomic_rule_uid`), in `odrl-compound-to-atomic-normalization.md` §5.2;
- stage 2 hashed a bound duty atom from its rule and its binding (the `duty-atom` domain);
- W2 hashed a duty instance from its atom, the performer, the reference, and the occurrence (the `duty-instance` domain);
- `alt_id`, `discharges`, the disjunct atoms of a constraint, and the negations that `xone` elimination adds were digests whose bytes were open (#107);
- `policy.version` was the digest of the policy's canonical N-Quads (`source_digest`).

Each construction is a byte-level contract that every implementation must reproduce exactly, and each has caused a fault downstream: `binding_key` left out the action (#121, `decisions/0032`), and #107 stayed open because every new derived id needed bytes of its own. The owner asked why id generation has to be repeatable at all.

It had to be repeatable for three readers:

1. **A case re-evaluated against an amended corpus.** Its activations and evidence name instances and duties. They still had to name the same things after the policy was normalised again, so an id had to survive an edit to an unrelated part (invariant 10, *Locality*).
2. **Two policies that state one named node.** Each policy is normalised on its own (`decisions/0036`), and the union of the corpora had to give the node's parts one id.
3. **A value computed outside the evaluator.** A submitter had to compute `discharges`, and a vector had to state `alt_id`.

Which of these needs an id computed from content?

## Decision

1. **A case fixes its corpus.** `case (case_id | request, corpus: Digest)`: the corpus is chosen when the case is opened, and every evaluation of the case names it. An amended policy or a new normaliser version changes no case. To apply the new version to an earlier request, as for a revocation, the orchestrator opens a new case for the request over the new corpus. Its activations start afresh, so a relative deadline runs from the activation the new case records, or from its `effective_at` without one, and evidence of the earlier case counts only if it is recorded again. A what-if run (`due2-platform.md` §2.11) stays hypothetical and records nothing.
2. **An id that no author chose is minted.** It is a UUID IRI, `urn:uuid:` followed by a random version 4 UUID (RFC 9562), minted once, when its thing is created. What it came from is held in link fields: `atom.source_rule`, `duty.source_duty`, and the lineage (`due2-workflows.md` §3.6). An authored identity is kept. An atom that is the only one made from its rule (an anonymous rule's id is itself minted), and to which stage 2 binds nothing, keeps the rule's id. Every other atom gets a minted id: the atoms of an expanded rule, the disjunct atoms of a constraint, and a duty atom that stage 2 binds roles or parameter values into. So do anonymous nodes and the negation constraints that `xone` elimination adds. `duty_constraint.clause` is any numbering W1 chooses. All of `odrl-compound-to-atomic-normalization.md` §5.2 is dropped: `frame`, `H`, the namespace, `term`, `local_digest`, `anon_node_uid`, `atomic_rule_uid`, the `duty-atom` and `duty-instance` domains, and `source_digest`.
3. **A named node is one individual, created once and found again.** A named node keeps its name everywhere. The parts minted for it, such as its anonymous constraints or its expanded atoms, are minted when it is first published. When a later policy states it again, `put_corpus` renames the ids the new corpus minted for that node and its parts, in the corpus and in its lineage, to the published ones. A bound duty atom is found again by its duty and its binding. `put_corpus` renames before it computes the collection ids of the corpus and its lineage. The renaming exists exactly when the two corpora agree up to renaming, which is the agreement check of #133. Where it is not unique, the parts it could swap have equal content, and either choice gives one corpus. Otherwise the policy is refused with `IdentityConflict`, as before (`decisions/0036`). The union of corpora stays a plain set union, and W1 stays pure over one policy. A named duty bound differently in two places, such as with the inherited assignees Alice and Bob, is two duty atoms, as before.
4. **`policy.version` is minted by the store.** `put_policy` already returns `policy_id, version`. The version is an `Id`, passed to W1 with the document and copied into `policy.version`. No workflow reads it.
5. **A duty instance is keyed by its atom and occurrence.** `instance (atom_id, occurrence?: Instant | status: Enum, passed: Flag)` and `activation (atom_id | at: Instant)`. A case has one request, so the performer and the reference are fixed within it (`decisions/0030`), and an instance key need not hold them. The member and grant scopes differ only in the witness test (`due2-workflows.md` §5.3). An occurrence instance's activation is its occurrence `t`, derived, so `activation` records only an atom's first-owed instant. A key field may now be optional, and an absent optional field sorts before any value (`due2-workflows.md` §2).
6. **`alt_id` is the alternative's position.** It is a `Count`, from 0, in the order in which alternatives are listed: by outstanding-set size, then by the list of the set's duty ids, sorted and compared by code point (`due2-workflows.md` §6.3).
7. **`discharges` is two plain fields.** `evidence` carries `discharges_duty?` and `discharges_reference?: String`, both or neither: the authored duty and the request's `reference` that the evidence was submitted against. The grant test reads `e.discharges_duty = d.source_duty` and `e.discharges_reference = request.reference`.
8. **Collection ids stay digests** (`decisions/0007`). Each is computed from bytes that both sides already hold, so its construction is fixed by RFC 8785 and SHA-256, with nothing left to choose.
9. **W1 is deterministic up to renaming of minted ids.** Two runs over one input give corpora and lineages that one bijection between minted ids makes equal. Invariant 10, *Locality*, is dropped.

## Why this holds

- **Each reader of item 1 to 3 in the question no longer needs a computed id.**
  - A fixed corpus removes reader 1: no case outlives its corpus, so no id has to survive a re-normalisation. In the owner's words: "If policies change - make a new request. Don't re-evaluate against a moving target."
  - The store holds every published corpus, so reader 2 is served by finding a node again rather than computing its id twice. That makes a named node one individual, as RDF intends: a duty that two policies state is instantiated once, carried once in a frontier, and discharged once (ODRL IM §2.6.5).
  - Reader 3 reads values that already exist. `discharges` names an authored duty and an authored reference, and `alt_id` is a position in an order that `due2-workflows.md` §6.3 fixes.
- **The instance key loses its hash for the same reason.** The performer and reference were in it to tell apart instances of different requests. A case has one request, and activations are recorded per case (`decisions/0008`), so those values never vary where the key is used.
- **One rule replaces every construction the question lists.** Minting needs no canonical term form, no framing, and no byte order. Each test of "same id" becomes a test of "same link". In the owner's words, minting is "simpler and more regular".
- **Agreement already had to compare content.** `decisions/0036` refuses a policy that says something different of a published node. Comparing up to renaming is the same check, and it yields the renaming as its witness.

## Rejected

- **Fix the bytes of every derived id (#107's plan).** Each new derived id would need a construction, a test that two implementations agree, and a review of what enters it. F02 (#121) showed how an ingredient goes missing.
- **Re-evaluate a case against an amended corpus.** The case's activations and evidence would have to be re-keyed or recomputed, and its later verdicts would rest on terms its earlier ones did not. That is the moving target the owner ruled out.
- **Mint per run, and copy the unnamed parts of a shared named node.** A duty that two policies state would then be two duties, instantiated twice and discharged twice, which contradicts ODRL's reading of a named node.
- **Name-based UUIDs (version 5) from the authored id and a path.** That is a derived id again, with a path syntax that every implementation must reproduce.

## Consequences

- `due2-workflows.md` v0.48:
  - §2: the sort rule for an absent optional key field; the `Id` and `Digest` rows.
  - §3.1: `policy.version`, `atom.atom_id`, `constraint`, and `duty.atom_id`.
  - §3.3: `evidence.discharges_duty` and `discharges_reference`; `activation` keyed by `atom_id`.
  - §3.5: `instance`, `alternative`, `alt_duty`, and `dominated`.
  - §4: the stage 1 row, *Several policies are one corpus*, and determinism up to renaming.
  - §5.2, §5.3: the instance and the grant test.
  - §6.3: *Sorting*.
  - §7.1: `case.corpus`, and amendments open new cases.
- `odrl-compound-to-atomic-normalization.md` 0.25: §5.2 is replaced by minting, and §3, §5.1, §6.1, §6.3, §7, §8, and §10 follow.
- `due2-platform.md`: `create_case` takes the corpus; `put_corpus` renames; re-evaluation on an amendment opens new cases; `policy.version` is minted.
- `due2-profiles.md` §7 and `due2-architecture.md` follow, and so do `ways-of-working.md`, `conformance/README.md`, and `schema/README.md`.
- `tools/gen_schema.py` accepts an optional key field, and the regenerated schema has the new relations. The harness drops its rule that turned a placeholder name in a `Digest` field into a digest.
- A corpus's ids depend on the store it is published into, not on its document alone: two stores, or one store fed in another order, give corpora equal up to renaming. `put_corpus` is a check and a rename, not a plain insert, and the union of published corpora stays a plain set union.
- `decisions/0008`, `0032`, `0036`, and `0037` get notes.
- #107 is closed as superseded, and so is what remained of #121.

## Revisit when

- A case has to outlive a policy amendment, for example because a long-running obligation must be carried into the amended terms. That needs a migration of the case's activations and evidence, which is a design of its own.
- #119 gives a recurring duty's occurrence a form other than an `Instant`.

**Note (2026-10-26, `decisions/0042`, #139):** a case fixes its config and pins too, by the argument of item 2 here: within a case, only the world changes. *A case fixes its corpus* in `due2-workflows.md` §7.1 becomes *A case fixes its terms*.
