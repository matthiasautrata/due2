# Decision records

A decision record settles one question that the specification depends on. It states the question, the decision, why it was made, the alternatives rejected, and what would reopen it. Each record is dated and is not rewritten afterwards. A later record that reverses or narrows a decision says so, and the earlier record's **Status** line names the later one. A clarification within the scope of a decision is appended to its record as a dated amendment or note. The specification sections a record changes cite it by number, as `decisions/0003`.

Throughout the repository, `decisions/0002` #5 means item 5 of that record's decision, and a bare "#5" means GitHub issue 5. A record's "the owner" is the project's maintainer, who takes the decisions an implementation cannot settle by itself.

**Standing.** *In force*: the decision holds as recorded. *Amended*: it holds, with the amendments, addenda, and notes appended to its record. *Narrowed* or *superseded in part*: the later record named in the row holds where the two overlap.

| # | Decision | Date | Standing |
|---|---|---|---|
| [0001](0001-rl2-as-donor.md) | due2 stays ODRL-native; RL2 is a donor; DPROD Contracts is a profile | 2026-10-09 | In force |
| [0002](0002-w1-implementation-and-verification.md) | W1 stays Python; verification enters as a Dafny oracle; Clingo is out of the evaluator pipeline | 2026-10-10 | Amended. Superseded in part: by 0003, which withdraws hoisting; by 0009, which makes the L9 oracle a clingo program (item 7); by 0021, which withdraws Dafny (items 2–4). 0006 exercises item 5's carve-out for a clingo backend. |
| [0003](0003-duty-guards-stay-on-the-duty.md) | Duty guards stay on the duty; conditional-duty hoisting is withdrawn | 2026-10-11 | In force |
| [0004](0004-frontier-complete-by-bounded-enumeration.md) | `frontier_complete` is computed by bounded enumeration | 2026-10-11 | Amended: 0026 changes the listed frontier it compares with |
| [0005](0005-set-based-operators-read-after-salas-pareti.md) | Set-based operators with lists are read after Salas–Pareti, with a warning | 2026-10-11 | Amended: an addendum on `isAllOf` |
| [0006](0006-w2w3-backend-bakeoff.md) | W2 and W3 are built as a bakeoff: Python, Elixir, Clingo, under one conformance suite | 2026-10-16 | In force |
| [0007](0007-collections-are-jcs-json.md) | Collections are JCS JSON arrays, identified by SHA-256 | 2026-10-16 | In force |
| [0008](0008-ledger-one-case-per-request.md) | The ledger: one case per request, an append-only sequence of events | 2026-10-16 | In force |
| [0009](0009-the-semantics-live-in-clingo.md) | The semantics live in a clingo program: the L9 oracle and the generator | 2026-10-16 | Amended |
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
| [0020](0020-vocabulary-defined-by-odrl-a-profile-or-the-policy.md) | A vocabulary term is defined by ODRL, a declared profile, or the policy itself | 2026-10-18 | In force |
| [0021](0021-formalisation-follows-cedar.md) | Formalisation follows Cedar: an executable model, proofs, and differential testing | 2026-10-19 | Amended: a note corrects the #25 example |
| [0022](0022-repeated-logical-constraint-member.md) | A repeated member of a logical constraint is malformed | 2026-10-22 | In force |
| [0023](0023-completion-key-includes-concept-reading.md) | The completion key includes the concept reading | 2026-10-23 | In force |
| [0024](0024-datetime-with-timezone-date-without.md) | A `dateTime` has a timezone; a `date` has none | 2026-10-23 | In force |
| [0025](0025-set-valued-operand-takes-set-operators.md) | A set-valued operand takes only the set operators | 2026-10-23 | In force |
| [0026](0026-listed-frontier-routes-that-suffice.md) | The listed frontier is the routes that suffice | 2026-10-24 | In force |
