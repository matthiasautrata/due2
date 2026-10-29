# Decision records

A decision record settles one question that the specification depends on. It states the question, the decision, why it was made, the alternatives rejected, and what would reopen it. Each record is dated and is not rewritten afterwards. A later record that reverses or narrows a decision says so, and the earlier record's **Status** line names the later one. A clarification within the scope of a decision is appended to its record as a dated amendment or note. The specification sections a record changes cite it by number, as `decisions/0003`.

Throughout the repository, `decisions/0002` #5 means item 5 of that record's decision, and a bare "#5" means GitHub issue 5. A record's "the owner" is the project's maintainer, who takes the decisions an implementation cannot settle by itself.

**Standing.** *In force*: the decision holds as recorded. *Amended*: it holds, with the amendments, addenda, and notes appended to its record. *Narrowed* or *superseded in part*: the later record named in the row holds where the two overlap.

| # | Decision | Date | Standing |
|---|---|---|---|
| [0001](0001-rl2-as-donor.md) | due2 stays ODRL-native; RL2 is a donor; DPROD Contracts is a profile | 2026-10-09 | In force |
| [0002](0002-w1-implementation-and-verification.md) | W1 stays Python; verification enters as a Dafny oracle; Clingo is out of the evaluator pipeline | 2026-10-10 | Amended. Superseded in part: by 0003, which withdraws hoisting; by 0009, which makes the L9 oracle a clingo program (item 7); by 0021, which withdraws Dafny (items 2–4); by 0027, which narrows item 1 to W1, closes item 5's carve-out for a clingo backend, and no longer sets Kotlin aside for W2 and W3 (item 8). |
| [0003](0003-duty-guards-stay-on-the-duty.md) | Duty guards stay on the duty; conditional-duty hoisting is withdrawn | 2026-10-11 | In force, with a note: 0028 makes a duty's DNF disjuncts clauses, not atoms |
| [0004](0004-frontier-complete-by-bounded-enumeration.md) | `frontier_complete` is computed by bounded enumeration | 2026-10-11 | Amended: 0026 changes the listed frontier it compares with; the bound was config, and is a constant again (`decisions/0045`) |
| [0005](0005-set-based-operators-read-after-salas-pareti.md) | Set-based operators with lists are read after Salas–Pareti, with a warning | 2026-10-11 | Amended: an addendum on `isAllOf` |
| [0006](0006-w2w3-backend-bakeoff.md) | W2 and W3 are built as a bakeoff: Python, Elixir, Clingo, under one conformance suite | 2026-10-16 | Superseded by 0027, except for the relation-level vectors (item 3) and the gate (item 4), whose oracle 0027's amendment of 2026-10-25 changes |
| [0007](0007-collections-are-jcs-json.md) | Collections are JCS JSON arrays, identified by SHA-256 | 2026-10-16 | Amended: a collection is a JSON object keyed by relation name; W1 writes no N-Quads (`decisions/0037`) |
| [0008](0008-ledger-one-case-per-request.md) | The ledger: one case per request, an append-only sequence of events | 2026-10-16 | In force, with notes: a case fixes its corpus, so a case is per request and corpus (`decisions/0038`); it fixes its config and pins too (`decisions/0042`), and holds no config (`decisions/0045`) |
| [0009](0009-the-semantics-live-in-clingo.md) | The semantics live in a clingo program: the L9 oracle and the generator | 2026-10-16 | Amended. Role (d), the bakeoff entrant, lapses with 0027. |
| [0010](0010-the-trace-is-the-explanation.md) | The trace is the explanation | 2026-10-16 | In force |
| [0011](0011-indeterminate-explained-by-pivotal-literals.md) | An `Indeterminate` verdict is explained by its pivotal literals and its range | 2026-10-17 | In force |
| [0012](0012-shared-reads-are-one-variable.md) | The same read is one completion variable; different reads stay independent | 2026-10-17 | Narrowed by 0016: items 1 and 2 hold only for unresolved values. Narrowed by 0023: they apply only when the concept reading is also the same. |
| [0013](0013-repeated-right-operand-values.md) | Repeated right-operand values are the same set as a list | 2026-10-17 | Amended: the empty list is rejected |
| [0014](0014-operand-type-belongs-to-its-declaring-layer.md) | An operand's type belongs to the layer that declares it | 2026-10-17 | In force |
| [0015](0015-concept-schemes-on-operands.md) | An operand may compare concepts under a SKOS hierarchy | 2026-10-17 | In force |
| [0016](0016-only-unresolved-values-are-completed.md) | Only an unresolved value is completed, and every `U` part is reported | 2026-10-17 | Amended: `unknown_part` excludes `F` findings |
| [0017](0017-empty-logical-constraint-is-malformed.md) | A logical constraint over the empty list is malformed | 2026-10-17 | In force |
| [0018](0018-each-member-bears-a-collection-duty.md) | Each member bears a duty whose bearer is a party collection | 2026-10-18 | In force |
| [0019](0019-pending-basis-under-unknowns.md) | A `Pending` basis under unknowns is checked only for its kinds | 2026-10-18 | Amended: 0026 answers its question on the listed frontier |
| [0020](0020-vocabulary-defined-by-odrl-a-profile-or-the-policy.md) | A vocabulary term is defined by ODRL, a declared profile, or the policy itself | 2026-10-18 | Amended: item 5 is reversed by 0033 |
| [0021](0021-formalisation-follows-cedar.md) | Formalisation follows Cedar: an executable model, proofs, and differential testing | 2026-10-19 | Amended: the search over clingo-i covers M and W; a note corrects the #25 example; the prover spike is parked, and 0027 answers item 7 |
| [0022](0022-repeated-logical-constraint-member.md) | A repeated member of a logical constraint is malformed | 2026-10-22 | In force |
| [0023](0023-completion-key-includes-concept-reading.md) | The completion key includes the concept reading | 2026-10-23 | In force |
| [0024](0024-datetime-with-timezone-date-without.md) | A `dateTime` has a timezone; a `date` has none | 2026-10-23 | In force |
| [0025](0025-set-valued-operand-takes-set-operators.md) | A set-valued operand takes only the set operators | 2026-10-23 | In force |
| [0026](0026-listed-frontier-routes-that-suffice.md) | The listed frontier is the routes that suffice | 2026-10-24 | In force |
| [0027](0027-the-corpus-is-the-boundary.md) | W1 stays Python; the corpus is the boundary; the bakeoff ends; the W2/W3 language is open | 2026-10-24 | In force, except item 1, which is open (#104). Amended: clingo-i's relation-level face (#41) replaces the brute-force W3 (#38) as the gate's oracle |
| [0028](0028-a-duty-condition-is-kept-in-clauses.md) | A duty's condition is kept in clauses on its one atom | 2026-10-24 | Amended: 0036 moves the clause number to `duty_constraint` |
| [0029](0029-a-void-policy-keeps-its-obligations.md) | A void policy keeps its root obligations | 2026-10-24 | In force, with a note: a violated obligation never denies (`decisions/0045`) |
| [0030](0030-a-re-evaluation-moves-the-request-time.md) | A re-evaluation asks at its own time | 2026-10-24 | In force |
| [0031](0031-a-permit-is-the-answer-of-the-terms.md) | A verdict is the answer of the terms supplied | 2026-10-24 | In force |
| [0032](0032-an-instance-records-whether-its-deadline-passed.md) | An instance records whether its deadline passed; a grant instance is keyed on its binding | 2026-10-24 | Amended: an instance is its duty atom, with the request's performer, reference, and occurrence added; a note: ids are minted, and an instance is keyed by its atom and occurrence (`decisions/0038`) |
| [0033](0033-a-replaced-policy-and-an-unrecognised-profile-are-rejected.md) | A replaced policy and an unrecognised profile are rejected | 2026-10-24 | In force |
| [0034](0034-the-odrl-layer-checks-the-action-hierarchy.md) | The ODRL layer checks the action hierarchy, and `odrl:hasPolicy` is rejected | 2026-10-24 | Amended: a refined action is its `rdf:value`, whatever its node kind; `odrl:assignerOf` and `odrl:assigneeOf` are rejected as `odrl:hasPolicy` is |
| [0035](0035-a-witness-read-is-keyed-by-its-witness.md) | A part read against a witness is keyed by its witness | 2026-10-25 | In force |
| [0036](0036-an-id-never-includes-its-policy.md) | An id never includes its policy, and an atom roots each policy that states it | 2026-10-26 | Amended: agreement between corpora is a precondition, checked at publish; a note: a `root` tuple names an authored policy, since no Atomic Policy node exists (`decisions/0037`); a note: ids computed from content are minted, and publishing renames them (`decisions/0038`). Superseded in part by 0050: every atom has entries, a root obligation is in force per entry (item 4), and the union keeps each policy's `closure` apart (item 5) |
| [0037](0037-w1-emits-no-rdf.md) | W1 emits no RDF: stage 1's atomised form is internal | 2026-10-26 | In force, with a note: `source_digest` is dropped (`decisions/0038`) |
| [0038](0038-ids-are-minted-and-a-case-fixes-its-corpus.md) | Ids are minted once, and a case fixes its corpus | 2026-10-26 | In force, with notes: a case fixes its config and pins too (`decisions/0042`); there is no config (`decisions/0045`); an instance and an activation are keyed by entry (`decisions/0050`) |
| [0039](0039-the-lineage-is-a-collection-of-its-own.md) | The lineage is a collection with relations of its own | 2026-10-26 | In force |
| [0040](0040-facts-are-kept-per-source.md) | Facts are kept per source, and W2 combines them | 2026-10-26 | In force, with notes: the connector registry admits sources (`decisions/0045`); a changed value arrives by an explicit call (`decisions/0046`) |
| [0041](0041-the-evaluator-returns-the-whole-trace.md) | The evaluator returns the whole trace | 2026-10-26 | In force |
| [0042](0042-a-case-fixes-its-config-and-pins.md) | A case fixes its request, corpus, config, and pins | 2026-10-26 | In force, with a note: there is no config (`decisions/0045`) |
| [0043](0043-world-edges-are-case-events.md) | World hierarchy edges are events on the case | 2026-10-26 | In force, with notes: the entities of an answer (`decisions/0047`); an answer's source and status (`decisions/0048`) |
| [0044](0044-the-source-version-is-on-the-event.md) | The source version is recorded on the event | 2026-10-26 | In force |
| [0045](0045-no-config.md) | An evaluation has no config | 2026-10-26 | In force |
| [0046](0046-platform-calls-are-explicit.md) | Publication is its own workflow, and a case changes only by explicit calls | 2026-10-26 | In force |
| [0047](0047-bindings-in-the-corpus-and-reads.md) | The corpus carries operand bindings, and `Reads` is four relations | 2026-10-26 | In force, with notes: `Reads` gains two relations (`decisions/0048`); one hierarchy per policy (`decisions/0050`) |
| [0048](0048-world-answers-have-a-source-and-a-status.md) | A world-edge answer has a source and a status, evidence edges are planned, and a plan over the read limit is refused | 2026-10-26 | In force, with a note: item 2 reads the corpus `closure` of the entry's policy only (`decisions/0050`) |
| [0049](0049-a-unit-belongs-to-the-binding.md) | A unit belongs to the operand's binding, and a unit no binding declares makes the comparison unknown | 2026-10-26 | In force |
| [0050](0050-a-policy-is-its-own-data-space.md) | A policy is its own data space: its findings read only its own corpus, its profiles, and the world | 2026-10-28 | In force |
| [0051](0051-a-parameter-and-its-values.md) | A request or evidence parameter and its values are two relations | 2026-10-29 | In force |
| [0052](0052-an-elimination-holds-in-every-completion.md) | An elimination is listed only when it holds in every completion | 2026-10-29 | In force |
