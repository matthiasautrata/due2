# Earlier changes

Each specification and design document opens with a **Changes** line for its latest version. The entries it replaced are kept here, newest first, verbatim as they stood. Section numbers in an entry refer to the document as it was then. Git has the full history: every commit names the sections it touched. The section before the last keeps the coverage-gap list's earlier re-derivations. The last section keeps README's Status paragraph as it stood before it was rewritten to describe only the present.

## `due2-workflows.md`

**Changes in v0.29** (2026-10-19, #81): §3.5 says which `U` leaves of a nested constraint `unknown_part` names: those that some `T` or `U` atom reads, which follows from atoms being the disjuncts of the constraint DNF; nothing else changes.

**Changes in v0.28** (2026-10-18, `decisions/0018`, #49): §5.3 says that each member bears a duty whose bearer is a party collection, so the witness's actor is the request subject when the subject is a member; §6's opening says that the one duty finding W3 reads before conflict is a violated precondition, which closes its route (§6.1).

**Changes in v0.27** (2026-10-17): §6.4 says that the completion key compares right operands as written terms, so the datatype is part of the key through them, and that two terms with one value are two variables.

**Changes in v0.26** (2026-10-17, `decisions/0016` amendment, #73): §3.5 restricts `unknown_part` to the findings that are not `F`, so that it does not depend on which certainly-`F` atoms an index skips (§5.5); §3.7 follows.

**Changes in v0.25** (2026-10-17, `decisions/0016`, #71): §6.4 completes only unresolved values, and every other `U` part is opaque, a variable of its own that is never paired; §3.5 adds `unknown_part`, every `U` part with what it reads and why, which §5.4 records, §6 gives W3, and §3.7 adds to the explanation; §6.4 says that `verdict_basis` names the atoms that carry a definite verdict in every completion, possibly none; L4 and L9 are restated. **v0.24** (2026-10-17, #68): §5.4 gives a `U` from a value basis kind `fact` only when a state property's status caused it, and kind `constraint` otherwise. **v0.23** (2026-10-17, `decisions/0015`, #52): §3.1 and §3.3 carry `skos:broader` and `skos:inScheme` edges in `closure`, and §3.3 says that a concept outside its operand's schemes gives `U`; §5.4 names the witness source, which `due2-profiles.md` §3 makes explicit, and gives `U` for a value that does not fit its operator. **v0.22** (2026-10-17, `decisions/0013`, #64): §3 says that `constraint_value` does not depend on how the policy writes a set right operand. **v0.21** (2026-10-17, `decisions/0012`, #56): §6.4 says that parts which are not the same expression or its complement stay separate variables, and what that costs; §9 open decision 6 names distinct values of a single-valued field. **v0.20** (2026-10-17, #59): §6.4 says that relation and party parts are keyed like constraint parts, so atoms share a literal as `decisions/0011` #2 assumes. **v0.19** (2026-10-17, `decisions/0011`): §6.4 says what "the `U` atoms whose completion changes the outcome" are, the atoms with a pivotal literal; §3.5 adds `verdict_range`, the least and greatest completion verdict of an `Indeterminate`; §3.7 names remedies as open (#61). **v0.18** (2026-10-16, issue #57): §3.5 says which atom `eliminated` names as `by_atom` under each rule; §3.7 says how the corpus projects `verdict_basis` and `eliminated` to authored IRIs, and that a role's atoms collapse when they share a source. **v0.17** (2026-10-16, `decisions/0010`): the new §3.7 makes the trace the explanation; the new law L10 (explicability) is in §8; §3.5 names the rule values `eliminated` records; §3.6 points to stage 1's lineage. **History:** v0.4–v0.16 are in git — every commit cites the sections it touched — and in `decisions/0003`–`0008`. v0.16 recorded an evaluation once, in `evaluation`, sharing the case's `seq` with `event` (§7.1).

**Coherence updates, 2026-10-10** (after `decisions/0002`): L9 restated as a refinement — conditional-duty hoisting splits one unknown into correlated findings completed independently, so the equality as previously written cannot hold under unknowns; L6 scoped to §6.2's conflict eliminations, because `eliminated` now also records `violated_precondition` removals (§3.5, §6.1), which give a closed route visibility in `verdict_basis` (role `closed`); the absent conflict term takes a selected profile's declared default first (normalisation spec §3); §5.3's no-guard sentence scoped to the parent relation.

## `correctness-strategy.md`

**Changes in v0.10** (2026-10-19, `decisions/0021`): §4.8, the formal model, states the claims M, K, F, W, and P, with their evidence and instruments; the formal model replaces the Dafny `Den` in §1.1, §3, §4.2, and §7; §8 builds the enumerator first and adds the formal model as step 6; §9 #11.

**Changes in v0.9** (2026-10-17, `decisions/0016`): §4.3's properties pair only completed parts; an opaque part is a variable of its own.

**v0.8** (2026-10-17, #48): slow `I`'s variable cap is set by measurement, at 64 (§3).

**Changes in v0.7** (2026-10-17, `decisions/0011`): an `Indeterminate`'s pivotal `unknown` atoms and its `verdict_range` are checked against brute force over the completions, in clingo-i (§4.1) and in W3 (§4.5).

**Changes in v0.6** (2026-10-16, `decisions/0010`): the explanation is checked as the verdict is. L10 (explicability) joins the trace properties (§4.6). The corpus asserts `verdict_basis` and `eliminated` at the authored level, and clingo-i returns them (§4.1; #57, #59). W1 stage 2's lineage gives every atom its authored source (§4.3).

**Changes in v0.5** (2026-10-16, `decisions/0009`): the L9 oracle and the generator are a clingo program over flattened ODRL, in place of a Python direct interpreter; the production evaluator is unchanged (`decisions/0002` #1, the `decisions/0006` bakeoff); §3, §4.1, §5, §8 rewire; RRULE recurrence deferred (occurrence-dependent scenarios report `unsupported: recurrence`).

**Changes in v0.4** (2026-10-16): §8 step 1 restated — the strategy is adopted, and the one open item (#10) is set at step 6; the register-tracking convention is stated once in `due2-architecture.md` §11.

**Changes in v0.3:** `I` comes in two modes, slow first (§3); the disagreement protocol (§6) and the generator coverage check (§5) adopted.

**Changes in v0.2:** critical features and the three testing modes decided (§1.1): atomization, evaluation, and case history get bounded-exhaustive, generated, and differential testing. Case history added as a component (§4.7, risk R10). Parser sharing decided (§4.1). Invalid-input twins for every generator (§5).
**Companions:** `ways-of-working.md` (the discipline and the tools: types, contracts, Hypothesis, tiering, Dafny) · `due2-architecture.md` §10 (the conformance suite) · `due2-workflows.md` §8 (laws L1–L10) · `odrl-compound-to-atomic-normalization.md` §8, §10 (stage-1 invariants, `Den`, minimum suite) · `decisions/0002` (which oracles exist).

## `ways-of-working.md`

**Changes in v0.5, 2026-10-19** (`decisions/0021`): §9 follows Cedar's pattern, an executable model, proofs, and differential testing, in place of Dafny extraction; §6, §10, §11, and §12 drop their Dafny mentions.

**Changes in v0.4, 2026-10-17:** new §15 — documentation: the cold reader, kinds of text (status kept out of reference), vocabulary, interfaces, worked examples, arguments with their steps, cross-references that name their document, code comments (PEP 257 for Python; clindocs blocks for ASP), and the checks that enforce them: the generated reference (mkdocstrings and clindocs, provisional) and clingo-i's doc tests. §14.1 step 2 cites it.

**Changes, 2026-10-16:** new §14 — the development cycle (design, docs, test, code, verify), the backlog's structure (sub-issues, milestones), branches, and CI; §12 step 9 is done. §13's tracking narrowed to the picks still open (#4, #8); the register-tracking convention is stated once in `due2-architecture.md` §11. New §7.4: one shared suite for every spike (`spikes/README.md`); §11's basedpyright scope extended to `tests/`.

**Changes in v0.3:** new §2.4 — RDF at the boundary: parse and emit at the edges, plain frozen structures everywhere between.

**Coherence updates, 2026-10-10:** §9's blocker resolved — Dafny is installable here, and `decisions/0002` records the track (register #9, #12); §7.1's preservation property restated as the refinement of `due2-workflows.md` §8 L9, whose L9 oracle is a direct interpreter over the lifted (authored) form.

**Changes in v0.2:** §2.3 (where exhaustiveness actually pays), new §5.1 (absent / unknown / false), §7.1 (semantic-preservation property), §9 (verification retargeted at the normaliser), §10 (rewritten around the two-stage split; Rego/OPA added), §11 (generated-code rule generalised), §13 (register extended). Companion document: `due2-architecture.md`.

## `due2-profiles.md`

**Changes in v0.12** (2026-10-17, `decisions/0017`, #74): §5 rejects a logical constraint over the empty list.

**v0.11** (2026-10-17, `decisions/0013` amendment, #69): §4 rejects an empty list as a set right operand. **v0.10** (2026-10-17, `decisions/0016`): §3 says that only an `unresolved` value is completed. **v0.9** (2026-10-17, #68): §3 *Kinds* says what `rdfs:Literal` and `rdfs:Resource` admit. **v0.8** (2026-10-17, `decisions/0014`, `decisions/0015`, #52, #65): §2 gives an operand's type to the lowest layer that declares it, lets higher layers rebind only its source and property, and drops the order of profile modules; §3 defines kinds, compares values by kind when there is no range, and checks a binding's range against the read property's; §4 and §6 compare concepts under a declared SKOS concept scheme. **v0.7** (2026-10-17, `decisions/0013`, #64): §4 admits a set right operand written as repeated values as well as an RDF list, and rejects the forms with no reading. **v0.6** (2026-10-16): every DPROD-derived adoption is marked provisional against the vendored commit, pending a batch of upstream PRs (§1, §8, §9 #7; issue #35); §3's context table names `dprod:agent`, the `dprod:EvaluationContext` property (`dprod-contracts.ttl`) that the left operand `dprod:currentAgent` reads through `dprod:operandProperty` — the table lists properties, as its `dprod:clock` row does; §9 rows #2 and #5 are merged (issue #18). **History:** v0.3–v0.5 are in git; the substantive decisions are `decisions/0005`, and `decisions/0001` for the DPROD adoption itself.

## `due2-diagnostics.md`

**Changes in v0.6** (2026-10-20, #83): a cold read. Cross-document references name their document, in the prose and in the registry's "Defined in" column; the timing rows and `UnsupportedConstruct` cite sections that now state their rejections (`due2-profiles.md` §7, `odrl-compound-to-atomic-normalization.md` §3). No code, severity, stage, or condition changes. Earlier changes are in `docs/archive/changes.md`.

**Changes in v0.5** (2026-10-17, `decisions/0017`, #74): `MalformedConstraint` covers a logical constraint over the empty list.

**v0.4** (2026-10-17, `decisions/0013` amendment, #69): `MalformedConstraint` covers an empty list as a set right operand. **v0.3** (2026-10-17, `decisions/0014`, `decisions/0015`): new rows `ConflictingProfileDeclaration` (named in profiles §2 since v0.4 but never registered), `RetypedOperand`, and `OperandRangeMismatch`; `InvalidBinding` and `OperatorTypeMismatch` cover concept schemes. **v0.2** (2026-10-17, `decisions/0013`, #64): `MalformedConstraint` covers more than one right-operand value on an operator that is not set-based, and a set right operand that mixes a list with other values or gives two lists.

## `due2-architecture.md`

**Changes in v0.7** (2026-10-16): the tracking convention for every open-decision register is stated here, once (§11); the DPROD relation is marked provisional against the vendored commit, pending upstream PRs (§8.3). Earlier changes are in `docs/archive/changes.md`.

**History:** v0.4–v0.6 are in git; the substantive amendments are recorded in `decisions/0001`–`0003`.

## `odrl-compound-to-atomic-normalization.md`

Changes in 0.14 (2026-10-20, #83): a cold read, spelling `artifact`. §3 lists the constructs outside the fragment that `due2-diagnostics.md` rejects as `UnsupportedConstruct`, with the reason for each; §5.2 and §6.1 no longer say that §3 requires Rules to be named, which §3 does not; §6.2 says whose phrase “each Rule in the Policy” is and where DPROD's rule is compared; §8.1 names `ways-of-working.md` and says where `Den` is formalised (`correctness-strategy.md` §4.8). Admitted input, as the registry and `tools/check_corpus.py` already drew it, and generated identity are unchanged. Earlier changes are in `docs/archive/changes.md`.

Changes in 0.13: an anonymous target or assignee is admitted with the `AnonymousEntity` warning (§3); admitted input and generated identity are unchanged.

Changes in 0.12: selected profile modules as input (§3); profile policy subclasses and conflict default (§3); anonymous Rules admitted with local identity (§3, §5.1); policy identity by IRI or `odrl:uid` (§3); interiorisation fills only what a Rule leaves unstated, so `InteriorizationRelationConflict` cannot arise (§6.2). Changes in 0.11: §3 states that named Rules are stricter than ODRL. Changes in 0.10: named Rules and label-independent, local anonymous-node identity (§3, §5.2); RDFC-1.0 removed from the identity path (§5.2, §6.1); all three conflict values accepted, an absent term made explicit as `odrl:invalid` (§3); Rule-reference acyclicity (§6.3); preservation stated over a denotation and witnessed by lineage (§8). The profile version stays `1` because no artefact has been produced under it. Any later change to admitted input or generated identity bumps it.

## `conformance/README.md` § Coverage gaps

Earlier re-derivations: 2026-10-19, after `due2-nested-unknowns` (#81); 2026-10-17, after the negative case `due2-empty-logical-constraint` (`decisions/0017`), after the concept-scheme cases `due2-concept-purpose`, `due2-concept-purpose-prohibition`, `due2-concept-complement`, and their three negative cases (`decisions/0015`), and `due2-empty-right-operand` (`decisions/0013`, amendment), after `due2-unresolved-or-missing` and the change to `due2-shared-reads` (`decisions/0016`), after the operand-binding cases `due2-rebound-pay-amount`, `due2-retyped-operand`, and `due2-operand-range-mismatch` (`decisions/0014`), after `due2-repeated-right-operand` and `due2-malformed-right-operand` (`decisions/0013`), and after `due2-shared-reads` (`decisions/0012`); 2026-10-16, after the explanation fields (#57) and the OVAL refresh (#51).

## README § Status, as it stood on 2026-10-19

Specification and corpus only — no evaluator yet; every expected verdict is hand-derived. Open items are GitHub issues (labels `open-decision`, `corpus`, `verification`, `work-item`, `parked`), each pointing at the section that holds its source of truth. The first runner of the corpus is the semantics program (issue #9, `decisions/0009`) — a generic clingo program over flattened ODRL, the L9 oracle and the test generator, run first over the corpus's authored policies (the correctness strategy is adopted; the enumeration bounds remain open, #42). Its spike, `spikes/clingo-i/`, was built in increments (#45, #46, #59, #47–#50): the walking skeleton (#45), the complete driver (#46), the explanation (#59: `verdict_basis`, `eliminated`, and an `Indeterminate`'s pivotal `unknown` atoms and `verdict_range`, `decisions/0011`), constraints (#47: the authored trees under strong Kleene logic, bindings, reads, refinements, and typed `partOf`), the layered operand bindings of `decisions/0014` (#68), the constraint completion variables of `due2-workflows.md` §6.4 (#48), the opaque parts and `unknown_parts` of `decisions/0016` (#72), concept-scheme operands under `skos:broader` (#69, `decisions/0015`), and duties (#49: closure before conflict, deadlines, the frontier, `Pending`, and `unknown` duty findings, `decisions/0018`, `decisions/0019`) are done. It passes 400 of the corpus's 438 scenarios and declines the other 38, naming the feature: 37 depend on occurrences (`unsupported: recurrence`), and one states `exact: false`, past the `max_mixed` bound, for which the spike has no fallback (`decisions/0009`). The corpus gate (#50) closes #9: every scenario it runs agrees with its hand-derived answer, and the one disagreement found, a corpus error, is triaged (#76). Next, the formalisation review (#70). Then the W2/W3 bakeoff on relation-level vectors — Clingo and Elixir first, Python deferred (`decisions/0006`) — then W1 with the Dafny `Den` oracle (#8).
