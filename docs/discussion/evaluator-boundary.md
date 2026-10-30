# The evaluator boundary: minted ids, one wire form, JSON-LD

**Status:** Proposed, 2026-10-30, for review. Not a decision record yet: on acceptance it becomes decision record 0053, and the edits below land in one increment.
**Source of truth touched:** `due2-workflows.md` §2, §3.5, §3.6, §7.1, §8 · `due2-platform.md` §1.2, §1.3, §2.1, §2.6, §2.10 · `schema/README.md` · `ways-of-working.md` §2.4 · `decisions/0007`, `0038`, `0041` · issues #172, #163, #166, #37, #170.

---

## 0. What this settles

One question, asked at one boundary, answered so the other boundaries inherit the answer: what is an id, what is a document, and what crosses between two due2 components.

1. Every id is either authored or minted. **No id is derived from content.**
2. A document that a store or ledger refers to carries its own id, as `@id`. A computed output carries none.
3. JSON-LD is the only wire form between published components. The relation-keyed JSON object survives as the internal form: a store's storage, a vector's authoring form, the generator's source. It never reaches a client.
4. JCS keeps one job — canonical serialisation, so two documents are equal iff their bytes are. SHA-256 keeps none. A digest, if a deployment wants one, is an integrity facility at an adapter (an ETag), never an identifier.

---

## 1. The question was raised: why may the evaluator not mint ids for its returns?

Because the trace is the object the audit rests on, and minting breaks five things at once:

1. **L1 becomes unsatisfiable.** L1 is *same evaluation, same trace bytes* (`due2-workflows.md` §8). A minted `@id` on the returned trace makes two runs over identical inputs differ in content, not serialisation. Rescuing the law by "equal up to renaming" needs a comparer that knows which fields may differ, which is exactly the byte contract `decisions/0038` deleted.
2. **Replay stops being equality.** `due2-platform.md` §2.6 compares the new trace with the recorded one. W2 and W3 mint nothing today, so the trace is a pure function and the comparison is total and trivial. Under minting it becomes a normalisation, and the one thing a second implementation cannot reproduce (`ways-of-working.md` §10.2, commitment 2).
3. **Purity is the audit guarantee.** `due2-platform.md` §1.1: `decide` is pure and "everything impure happens around it". *Given these inputs, this trace* is what lets a reader recompute the record (`due2-workflows.md` §7, L10). Minting is randomness, an effect, inside the component the record rests on.
4. **Retries stop being recognisable.** `due2-platform.md` §1.2 assumes a caller that times out may retry. A minted trace id makes every retry a new object, so nothing downstream can dedupe two answers to one question.
5. **Minting belongs to the writer.** The store mints versions, the ledger mints case ids and sequence numbers, the orchestrator mints idempotency keys. The evaluator computes a value; it creates nothing that needs a name.

**The counterargument, and its answer.** A direct caller of a published evaluator port may want an id for the trace it received. That is not an exception to the rule — it is the rule applied: whoever stores mints, and a caller that stores is a writer. So `plan` and `decide` return documents without `@id`, and the ledger, on `record_evaluation`, names the trace by its own id and records it **as returned**. Recording it as returned is what keeps L1's byte comparison exact and needs no elision before comparing.

---

## 2. The decision

1. **Authored identity is kept.** A named node keeps its IRI; an authored `odrl:uid` is the node's id, as today (`odrl-compound-to-atomic-normalization.md` §5.1).
2. **Every id that no author chose is minted** — a `urn:uuid:` IRI with a random version 4 UUID (RFC 9562), minted once, when its thing is created (`decisions/0038` item 2). This extends without change to anonymous nodes, expanded atoms, derived constraints, bound duty atoms, and **every n-ary node the wire form needs** (§4 below).
3. **A collection's id is minted by the component that stores it** and carried as `@id` in the document. `decisions/0007`'s "identified by SHA-256" is amended: canonical bytes remain the equality relation, the digest is no longer the identifier.
4. **Ids are never port arguments.** A document carries its own id, so `decide` has no `corpus_id` parameter, and `due2-platform.md` §1.3's "the evaluator never takes the id from the caller" is replaced by "the evaluator reads the id the document carries". The trust check it defended is dropped: between due2's own components it guarded against a bug, and the mutation it feared is visible in the trace's `evaluation` tuple.
5. **A computed output carries no id.** `Reads` and `Trace` are returned without `@id`; a component that stores one mints it (§1). No derived id exists anywhere, so no test has to reproduce one.
6. **The trace's `evaluation` tuple names its three inputs by `@id`**, not by digest. The evaluation's own id is gone: the ledger's record (case, sequence) names it.
7. **JSON-LD is the only wire form**, between every pair of published components. A collection document as `schema/` defines it is not a wire format; it is the internal form (§4 below).
8. **`Digest` leaves the value types.** A digest may appear at an adapter as an integrity facility and nowhere in a port document.

### The invariant the record states, because three laws depend on it

**The evaluator mints no id.** Every id in a trace is one of two things: an input's `@id`, or a value the spec fixes (`alt_id` is a position, `decisions/0038` item 6). This single sentence is what makes L1 byte comparison exact, what makes replay equality total, and what keeps the evaluator pure. It is stated as law text, not as a comment.

### Laws

- **L1** keeps its text and gains one clause: "The evaluator mints no id, so a trace is a function of its inputs' bytes alone."
- **L11** says tuples are "the same" in `{P,Q}` as in `{P}`. With minting that holds only up to the renaming of ids the store performed at publish, so it gains "on one stored corpus". Its generator already runs over a single corpus, so this states what the test does.
- **New L12 — W1 determinism up to renaming.** Two runs of W1 over one policy document and one normaliser version give corpora and lineages that one bijection between minted ids makes equal, and `lineage.minted` names each side's domain of it (`decisions/0038` item 9, promoted from a record note to a law with a property-test target). §8 is the table that states properties an implementation must satisfy, and W1 has no entry in it today.

---

## 3. Rejected

- **Keep collection digests as ids** (`decisions/0007` item 8). The digest's four jobs all die under minting: the memo's trust check is dropped by item 4; a cache cannot be stale for an immutable, versioned collection; replay and L1 need equality of bytes, which JCS gives; and cross-store identity was never available anyway, because W1 mints.
- **Mint in the evaluator** (§1 above).
- **Content-address the corpus and dedupe downstream.** Two documents for one authored source is what explicability forbids (`decisions/0036`).
- **Keep a digest *and* a minted id on every collection.** Two names for one thing, with no reader for the second. The one place a content witness is useful is a deployment's ETag, and that belongs to its adapter.
- **Publish the relation-keyed JSON as the wire form, with JSON-LD as an optional view** (`due2-platform.md` §1.2 today). Rejected by the owner: every published component speaks JSON-LD, so a client never sees relation JSON, and an optional view is a second contract nobody tests.
- **Make RDF the internal form too.** Each store, the vectors, and the harness would then carry an RDF parser, and the corpus's key semantics would have to be re-expressed as graph constraints for no reader's benefit.

---

## 4. The wire: published versus internal, one generator

**Published (new):** a JSON-LD context and vocabulary under a pinned IRI, plus one node shape per document a port takes or returns. **Internal (today's `schema/`):** the relation-keyed collection schema, relabelled as not-a-port, still generated from `due2-workflows.md` §3 and still what vectors, stores, and tests use.

One generator, two writers, so the artifacts cannot drift: `tools/gen_schema.py` already parses the §3 relation blocks; the context and vocabulary are a second writer over the same parse.

**Versioning.** The wire contract is new, so it gets its own version and `$id` space (`https://w3id.org/due2/wire/1/`), versioned `1.0` on first publication. The internal schema stays at `3.x`, and its only change here is `Digest` → `Id`, a widening, so `3.1`. Pretending a compatibility relation between a form that never shipped and one that did would be a fiction.

**The four mapping shapes.** This is the whole of the structure problem:

| Relation shape | JSON-LD form |
|---|---|
| Single-`Id` key (`atom`, `constraint`, `policy`, `evidence`, `request_param`, `case`) | one node; the key field is the `@id` |
| Composite key (`fact`, `closure`, `closure_answer`, `atom_party`, `atom_constraint`, `duty_constraint`, `constraint_value`, `*_param_value`, `root`, `policy_profile`) | one node with a minted `@id`; key fields as properties |
| Empty key (`request`, `sotw`, `verdict`, `lineage`, `evaluation`) | properties of the enclosing document node |
| Field values | `Enum`, `Flag`, `Count`, `String` → typed literals; `Id` → `@id`; literal → `@value` + `@type`/`@language`; `Truth` → `due2:T`, `due2:F`, `due2:U`, never a string that reads as a boolean |

**Vocabulary naming.** One property per (relation, field), `due2:`-namespaced, generated from §3. A relation name is a class. An `Enum` value becomes a `due2:` IRI, except where the value is already an external IRI in the tuple — actions, operands, operators, functions, and the `odrl:` conflict values keep their own names.

**What this deletes rather than adds:** the `Digest` value type; the `x-key` annotation, because two tuples with one key are now literally one `@id` and uniqueness is expressed instead of validated; the `{"v","t","l"}` literal at the boundary; `schema/README.md`'s admitted wart that `Id` accepts a prefixed name because "the schema cannot tell one from an IRI", since a pinned context resolves compact IRIs; and the normal-path/fast-path pair, because a node is either inlined or referenced by `@id` (`due2-platform.md` §1.3).

### The recipe every later port follows

So the other seven ports need no new decision:

1. Publish the subset of the vocabulary the port's documents use, in one context file.
2. One call per step of a use case, carrying one graph; ids are `@id`s in it, never arguments.
3. Return the document the caller stores, or references to documents it already holds.
4. Express a failure as a `due2:Error` node with a `due2:code` — a client branches on the code, never on the text (`due2-platform.md` §1.2 today is text-only).
5. The component that stores mints; the component that computes does not.

---

## 5. Document adjustments, file by file

| File | Edit |
|---|---|
| `due2-workflows.md` §2 | Delete the `Digest` row. Extend the `Id` row with the minting rule and "no id is derived". *Collections*: "identified by the digest of its canonical form" → "identified by a minted id, carried as `@id`". *Canonical form*: keep encoding and order; replace the **Digest** bullet with **Equality**: two collections are equal iff their canonical bytes are, and the bytes identify nothing. |
| `due2-workflows.md` §3.1 | The `diagnostic` row's reason ("so that the corpus digest, and with it the evaluation id, records the reading") → restate against the trace: the diagnostic is in the corpus so a verdict that rests on a contested reading says so. |
| `due2-workflows.md` §3.5 | `evaluation (\| corpus_id: Id, request_id: Id, sotw_id: Id)`; the row's text: the three inputs' `@id`s, read from the documents; delete "the evaluation id is the digest of this tuple". State the minting rule in §2 only, not twice. |
| `due2-workflows.md` §3.6 | `lineage.minted` gains its second reason: it names the domain of the renaming a store performs (L12, §2 above). |
| `due2-workflows.md` §7.1 | `case (case_id \| request, corpus: Id, pins)`; `evaluation (case_id, seq \| sotw: Id, …)`; "the digest is the evaluation's `sotw` id" → the `@id`. Add: the ledger records a trace as returned, without `@id`. |
| `due2-workflows.md` §7 | Replay compares canonical bytes of the stored and the re-run trace, which minting makes exact. |
| `due2-workflows.md` §8 | L1's added clause; L11's "on one stored corpus"; new L12. |
| `due2-platform.md` §1.2 | "One schema, several adapters" → published versus internal, JSON-LD as the only wire form, the four-move recipe, `Error` carrying a code, and the present-tense claim about generated OpenAPI and MCP marked as a target with its issue. |
| `due2-platform.md` §1.3 | Rewrite: ids are minted and carried as `@id`; the memo is keyed by the id the document carries; the normal/fast path pair is replaced by inlining versus reference; delete the trust-check paragraph and the "JSON-LD as a view" sentence. |
| `due2-platform.md` §2.1 | `plan(input)` and `decide(input)`, one graph per call: a `due2:Corpus`, `due2:Request`, and `due2:Sotw` node, each with `@id`. The output is a `due2:Trace` node with no `@id`. |
| `due2-platform.md` §2.3 | "A collection is named by its digest" → by a minted id; `put_corpus` renames minted ids and computes no id. |
| `due2-platform.md` §2.6 | Replay: byte comparison of the recorded trace as returned. |
| `due2-platform.md` §2.10 | The wire contract's version is what a mixed-version fleet disagrees about, so "the reader upgrades before its writer" is a deployment order, not a convention. |
| `schema/README.md` | Split into *published* (context, vocabulary, node shapes) and *internal* (the relation schema, not a port). Remove the `Digest` row; replace the `x-key` paragraph with the `@id`-identity note; state that the wire schema is generated by the second writer and starts at `1.0`. |
| `ways-of-working.md` §2.4 | "RDF at the boundary" → RDF at *every published boundary*, read and written; the acceptance test becomes "no RDF import outside an adapter module", and each published component has one. The digest paragraph becomes the canonical-bytes paragraph. |
| `due2-overview.md` | "named by its digest" → minted id; the table row "Replay, caching, and audit need no further machinery" keeps its claim, cited to L1 and minting rather than to `decisions/0007`. |
| `due2-architecture.md` | The one sentence naming the corpus as "digest (`decisions/0007`)". |
| `correctness-strategy.md` | "…digests (`due2-workflows.md` §7)" → canonical bytes. Add L12 to the property-test targets. |
| `conformance/README.md` | Relation-level vectors: each collection states its `@id` — the file writes it, since a minted id is an ordinary IRI — so the *Ids the vector file does not state* section loses its `evaluation` bullet (the harness no longer computes anything) and keeps the minted-ids and operand-bindings bullets. Add: the harness renders the file to JSON-LD before sending. |
| `spikes/README.md` | The `decide` example's `sha256:…` ids become `urn:uuid:…`. |
| `decisions/0007` | Third amendment: ids are minted; the canonical form is an equality relation. The title stays, and the amendment says so. |
| `decisions/0038` | Item 8 amended to point here; items 2 and 3 unchanged. |
| `decisions/README.md` | The row for the record this document becomes. |
| Each document's Status line, Changes line, and `docs/archive/changes.md` | Version bump and one `Changes in` sentence, per `ways-of-working.md` §15.2. |

---

## 6. Schema and code

Small, because almost everything is generated:

| Where | Change |
|---|---|
| `tools/gen_schema.py` | Delete the `Digest` type; `Id` gains the minting note. A second writer emits the context and vocabulary from the same parse. Two output roots, two versions. |
| `schema/*.schema.json` | Regenerated: internal at `3.1`, published at `1.0`. |
| `tests/test_schema.py` | The `DIGEST` fixture goes. New: every relation in §3 has a vocabulary term; every `Enum` value has one; render then parse round-trips every fixture and every corpus collection; the two writers' outputs match the generator. |
| `tools/harness/vectors.py` | `check_collection` drops the digest check; `NOT_PREFIXES` loses `sha256`; `x-key` checking stays for internal files. Adds a render step. |
| `tools/harness/run.py` | `--wire=jsonld` mode: the harness sends the graph a published port would receive and compares the returned graph. |
| `tests/fixtures/vectors/due2-one-permission.json` | States its collections' `@id`s. |
| New: `conformance/vectors/due2-shared-anonymous.json` | One corpus, two policies, one **anonymous** node shared between them (§7 below). |

---

## 7. Tests this increment adds

1. **Round-trip.** For every collection in the corpus and every fixture: `parse(render(c)) = c` on the internal form, and the wire form is the same graph. This is the property that keeps one mapping honest, and it is the only test the wire has until the evaluator exists.
2. **No derived id.** A checker over `conformance/vectors/` and the fixtures: every `Id` field in a collection is either an authored IRI or a `urn:uuid:`, and no field of a port document is a `sha256:` value. This makes item 1 of the decision machine-checked rather than prose.
3. **The shared anonymous node.** A vector file where two policies state one unnamed rule under named parents, so W3 sees one atom with two entries and one minted id. The corpus cannot express this today: every case must name its rules, and `expected` can only name authored IRIs, so the anonymous half of `decisions/0036` has no case, no vector and no generator. This is the identity evidence that does not need W1, because a vector writes its corpus, ids included.

---

## 8. Issue adjustments

| Issue | Adjustment |
|---|---|
| **#172** | Rewrite from an option list to this document: the rule is decided, minted everywhere and nothing derived; the first increment is the evaluator boundary; the gate is the record this document becomes, plus the published context, the round-trip test, and the no-derived-id checker. Remove its option 1–3 framing and its "private digest" parenthetical, which cannot hold because the trace's `evaluation` tuple is output. |
| **#163** | Remove its dependency on #172, recorded in a comment: the flat corpus's RDF form is a *due2* vocabulary, not ODRL, so RDF at the boundary no longer forces the normal form. #163 is decided on its own merits, as #170 orders it. |
| **#166** | Narrows: the wire form is JSON-LD either way, so the question is which subset of the trace a port publishes. Note that under this decision an Answer is a *view* of the trace, which makes the fork smaller, not larger. |
| **#37** | Add: each collection states its `@id`; the harness renders to JSON-LD; one vector file shares an anonymous node (§7 above). #37 becomes the vehicle for the identity work, so it moves ahead of #167 in the order. |
| **#170** | Move #172 from group 3 to group 1 (decide first), because it now gates #167's step 3 and the whole schema. Reason stated: the id rule is a prerequisite, not an outcome, of the slice. |
| **#174** (`open-decision`, filed) | W1's determinism as §8 law L12, with the property test that checks it. |
| **#175** (`corpus`, filed) | The case format's per-entry observables — `by_policy` in `expected.eliminated` (`decisions/0050` #10) and an activation per entry (`decisions/0050` #4). Today `sotw.activation` is one instant per duty IRI "for every entry", so 0050's semantics can change without a case moving. |
| **#176** (`work-item`, filed) | Re-record `spikes/clingo-i/scorecard.json` on a clean tree. Its `revision` is `9d0e9d0+dirty`, three commits behind, and `117dfaf` changed `lp/explain.lp` after it, so README's 461/502 is pinned to a tree no commit reproduces. |
| **#133, #165** | Commented, not edited: `lineage.minted` is the record the renaming reads and the domain of L12's bijection, and an explicit `renamed (from, to)` relation would be decided here, because `put_corpus` is where the renaming is applied. |

---

## 9. Steps, in order (`ways-of-working.md` §14)

1. **Design.** Decision record 0053 from this document, Status Decided; the #172, #163, #166, #37 and #170 edits; the three new issues created before the commit.
2. **Docs.** §5's table, end to end; each document's Status and Changes lines.
3. **Test.** §7's three tests, written against the not-yet-regenerated schema so they fail.
4. **Code.** The second writer in `gen_schema.py` and the `Digest` deletion; the harness render step and `--wire=jsonld`; the fixture's ids.
5. **Verify.** README § Verify, plus `uv run --group docs mkdocs build --strict` and `test_doc_counts.py`. Commit citing #172; close nothing else.

Nothing here needs an evaluator, W1, or a running clingo. It is spec, generator, and tests, which is why it is a safe first increment.

---

## 10. Not in scope

- The other seven published ports. They follow §4's recipe when each is built; publishing their schemas now would be the speculative work the owner ruled out.
- OpenAPI and MCP artifacts. The vocabulary is their prerequisite, not the reverse.
- #163's normal form, #166's published subset, #164's exactness, #165's cross-policy fork.
- Recurrence, monitoring, and the case format's per-entry gaps (the new issue).
- Any change to W2/W3's semantics. This increment changes no verdict and no trace tuple; the corpus is unchanged.

---

## 11. Open items needing the owner

1. **The wire version's number.** `1.0` in a fresh `w3id.org/due2/wire/1/` space (recommended: no false compatibility), or `3.0` beside the internal schema (one number to track, one fiction to explain).
2. **`due2:` versus `odrl:` for the reused terms.** Recommended: keep an external IRI wherever the tuple already holds one, and mint `due2:` only for the abstracted `Enum` values, so the vocabulary does not restate ODRL.
3. **`lineage.minted` as the renaming domain.** It names which ids a run minted, but not which *kind* of thing each is. The store's renaming needs the pairs, which `anonymous`, `atom_rule`, `negation`, and `selected` supply per kind. Recommended: state that the renaming is per kind through those relations, and add no field. If you would rather have one explicit relation (`renamed (from, to)`), it belongs in this record, because `put_corpus` is where it is applied.
