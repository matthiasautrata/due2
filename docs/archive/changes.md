# Earlier changes

Each specification and design document opens with a **Changes** line for its latest version. The entries it replaced are kept here, newest first, verbatim as they stood. Section numbers in an entry refer to the document as it was then. Git has the full history: every commit names the sections it touched. The section before the last keeps the coverage-gap list's earlier re-derivations. The last section keeps README's Status paragraph as it stood before it was rewritten to describe only the present.

## `due2-workflows.md`

**Changes in v0.52** (2026-10-26, `decisions/0045`): an evaluation has no config, so `decide` takes three inputs and a case holds no config id (§3.4, §3.5, §7.1). Prohibit-overrides is the fixed rule across policies (§6.2). A violated obligation is reported and never denies (§6.1, §6.4, L7). A duty's attester replaces the signer record (§5.3). `max_mixed` and `max_frontier_vars` are constants (§3.4). Every recorded answer is admitted (§3.3). Earlier changes are in `docs/archive/changes.md`.

**Changes in v0.51** (2026-10-26, `decisions/0043`, `decisions/0044`): world hierarchy edges reach the case as `closure` events, one answer per module and request entity, and the latest answer replaces an earlier one (§3.3, §7.1). An event carries the version of the source that answered, which W2 never reads (§7.1). Earlier changes are in `docs/archive/changes.md`.

**Changes in v0.50** (2026-10-26, `decisions/0040`, `decisions/0041`, `decisions/0042`, #137, #138, #139): the SOTW keeps each source's answer, `attribution` is dropped, and W2 combines the admitted answers of a property (§3.3, §5.4); `admit_age` is dropped, because keeping values current is the SOTW service's job (§3.4). The evaluator computes `evaluation` and `diagnostic` too, so it returns the whole trace (§3.5). A case fixes its request, corpus, config, and pins, and an evaluation records only its SOTW and outcome (§7.1). Earlier changes are in `docs/archive/changes.md`.

**Changes in v0.49** (2026-10-26, `decisions/0039`, #136): the lineage is a collection with relations of its own (§3.6), one per policy version and normaliser version, found by the policy store and never merged; §2 counts six collections, and §3.7 and L10 read the lineage of each policy in the corpus. Earlier changes are in `docs/archive/changes.md`.

**Changes in v0.48** (2026-10-26, `decisions/0038`, #107): an id that no author chose is minted, not derived (§2, §3.1). A case fixes its corpus (§7.1). A duty instance is keyed by its atom and occurrence (§3.3, §3.5, §5.3), `alt_id` is a position (§3.5, §6.3), `discharges` is two fields (§3.3, §5.3), and W1 is deterministic up to renaming of minted ids (§4).

**Changes in v0.47** (2026-10-26, `decisions/0037`, #134): W1 emits no RDF. Stage 1's output stays inside W1 (§2, §4), and `root` names the root atoms of stage 1 (§3.1). Earlier changes are in `docs/archive/changes.md`.

**Changes in v0.46** (2026-10-26, `decisions/0036` amendment, #132): agreement between the corpora of the policies evaluated together is a precondition of their union, checked when a policy is published, so the union never fails (§4). Earlier changes are in `docs/archive/changes.md`.

**Changes in v0.45** (2026-10-26, `decisions/0036`, #130): no named node's id includes its policy (§3.1, `atom.atom_id`). An atom's policies are in `root`, which becomes `(atom_id, policy_id)`, with a tuple for each policy that states the atom, and `atom` drops `policy_id`. A constraint's attachment moves out of `constraint` into `atom_constraint` and `duty_constraint`, which holds the clause number, so a named constraint is one tuple. A shared permission or prohibition takes part once in each of its policies, and remains while any of these entries survives; `eliminated` gains `policy_id` (§3.5, §6.2). A duty that several policies state as an obligation is in force when any of them matches the request (§5.1, §5.2, L2). The corpus of policies evaluated together is the union of their corpora, and two corpora that say different things of one node are `IdentityConflict` (§4). §6.4's proof covers an atom with several entries, and §3.7 follows.

**Changes in v0.44** (2026-10-25, `decisions/0032` amendment, #121): a duty atom's id identifies what it asks for, by stage 1's construction extended with what stage 2 adds (§3.1, §4), and replaces `binding_key`, which is dropped. A `member` instance is its duty atom; W2 mints an instance id from the atom's id with the request subject when the subject is the performer, the `reference` for a `grant` instance, and the occurrence (§5.3). `instance_key` is an `Id` (§3.3, §3.5).

**Changes in v0.43** (2026-10-25, `decisions/0035`, #120): the parts of a duty's witness conditions are recorded per witness, in the new relations `witness_basis` and `witness_part` (§3.5), and `basis` gains `predicate` in its key. The W2 signature lists `unknown_part` and both new relations (§5); §3.7, §5.1–§5.4, and L10 follow. W3 reads neither new relation: a `fulfilled` finding is a completion variable of its own (§6.4).

**Changes in v0.42** (2026-10-24, #116): §3.1 states the invariants that every id in a corpus tuple names a policy, atom, or constraint that the corpus holds, and that an atom has `relation_value` exactly when it has `relation`. No rule changes.

**Changes in v0.41** (2026-10-24, #114): laws L2, L3, L6, and L7 are restated, since each was false as written (§8). §6.4's monotonicity proof says how a candidate that a violated precondition closes or reopens passes through §6.2, and §3.5 and §6.4 say what `verdict.exact` means. No rule changes. Earlier changes are in `docs/archive/changes.md`.

**Changes in v0.40** (2026-10-24, `decisions/0032`, #113): `instance` gains `passed`, whether the instance's deadline has passed, which W3 reads where a completion makes an `unknown` instance unfulfilled (§3.5, §5.3, §6.4), and W3's signature lists `instance` (§6). A grant-scoped instance key is the digest of `binding_key` and `request.reference`, so each atom of an authored duty has its own instance, and `discharges` names the grant by the digest of `source_duty` and `request.reference` (§3.3, §5.3). Earlier changes are in `docs/archive/changes.md`.

**Changes in v0.39** (2026-10-24, `decisions/0031`, #112): a verdict is the answer of the policies supplied, as written, whatever their class; over an offer, `Permit` says that its terms permit the action, not that it has been accepted (§6.4). §3.1 says that `policy` keeps no class. Earlier changes are in `docs/archive/changes.md`.

**Changes in v0.38** (2026-10-24, `decisions/0030`, #111): each evaluation of a case runs with the case's request, with `at` moved to the evaluation's `effective_at` when it is earlier, so a re-evaluation asks at its own time (§3.2). §7.1's `evaluation` relation names the request it ran with, and the latest evaluation is the case's current answer. Earlier changes are in `docs/archive/changes.md`.

**Changes in v0.37** (2026-10-24, `decisions/0029`, #110): under `invalid`, a void policy loses its permissions and prohibitions and keeps its root obligations, so under `violations = deny` a violated one still denies (§6.2). §6.4's proof covers the void's obligations, and a `Deny` from a violated obligation is explained by role `obligation` (§6.4). Earlier changes are in `docs/archive/changes.md`.

**Changes in v0.36** (2026-10-24, `decisions/0028`, #109): a duty stays one atom, and its condition is kept in clauses. `constraint` gains `clause`, present on the constraints of an `Oblige` atom (§3.1). The guards hold, or a witness satisfies the witness conditions, when some clause of that kind holds (§5.1–§5.3), and §3.5, §3.6, §4, §6.4, and L9 say so. Earlier changes are in `docs/archive/changes.md`.

**Changes in v0.35** (2026-10-24, #36): every field of §3 has a value type, and §2 adds `Instant`, `Flag`, `Count`, `Digest`, and `String`. A policy's profiles move to `policy_profile`, one tuple per IRI, and `policy.version` is the digest of the authored policy. `config` gains `max_mixed` and `max_frontier_vars`, which change the trace, and loses `preference`, whose form is open (#5). `eliminated`, `dominated`, and `verdict_basis` are keyed by all of their fields, since one atom or alternative can have several removers, dominators, or roles. `request.reference` is a `String`, since a caller's identifier need not be an IRI. `decisions/0004` is amended.

**Changes in v0.34** (2026-10-24, `decisions/0026`, #84): under unknowns, §6.3 lists the non-dominated routes that suffice, those within which every completion has an open route, where v0.33 listed only the routes of the candidates that are ready or pending whatever the unknowns are; §6.4 says how W3 computes them, within `max_frontier_vars` and beyond it, and §3.5's `alternative` follows.

**Changes in v0.33** (2026-10-23, `decisions/0024`, #101): an absolute deadline and the instants of a request and a SOTW have a timezone (§3.1–§3.3, §5.3, §5.4), and §5.4 lists a `dateTime` without a timezone, or a `date` with one, as a value that does not fit. Earlier changes are in `docs/archive/changes.md`.

**Changes in v0.32** (2026-10-23, `decisions/0023`, #84): §6.4 adds the concept reading to the completion key, since an operand with a concept scheme reads `eq` as ⊑ and one without reads it as identity; *What stays approximate* corrects its example: the completion no value gives is `x ≤ 5` and `x > 7` both `T`, not both `F` (#25). Earlier changes are in `docs/archive/changes.md`.

**Changes in v0.31** (2026-10-22, #83): a length pass. Dates leave the headings; the results of `tools/check_completion.py` are cited from the records that hold them; text repeated within §3.3, §6.4, §7, §9, and the appendix is cut. No semantics change. Earlier changes are in `docs/archive/changes.md`.

**Changes in v0.30** (2026-10-20, #83): a cold read. Cross-document references name their document; history markers leave the reference text; §6.4 cites `tools/check_completion.py` for the two-extremes check in place of an unrecorded one; §9 lists the open rows with their issues and states rows 1 and 8 as resolved, keeping the row numbers. No semantics change. Earlier changes are in `docs/archive/changes.md`.

**Changes in v0.29** (2026-10-19, #81): §3.5 says which `U` leaves of a nested constraint `unknown_part` names: those that some `T` or `U` atom reads, which follows from atoms being the disjuncts of the constraint DNF; nothing else changes.

**Changes in v0.28** (2026-10-18, `decisions/0018`, #49): §5.3 says that each member bears a duty whose bearer is a party collection, so the witness's actor is the request subject when the subject is a member; §6's opening says that the one duty finding W3 reads before conflict is a violated precondition, which closes its route (§6.1).

**Changes in v0.27** (2026-10-17): §6.4 says that the completion key compares right operands as written terms, so the datatype is part of the key through them, and that two terms with one value are two variables.

**Changes in v0.26** (2026-10-17, `decisions/0016` amendment, #73): §3.5 restricts `unknown_part` to the findings that are not `F`, so that it does not depend on which certainly-`F` atoms an index skips (§5.5); §3.7 follows.

**Changes in v0.25** (2026-10-17, `decisions/0016`, #71): §6.4 completes only unresolved values, and every other `U` part is opaque, a variable of its own that is never paired; §3.5 adds `unknown_part`, every `U` part with what it reads and why, which §5.4 records, §6 gives W3, and §3.7 adds to the explanation; §6.4 says that `verdict_basis` names the atoms that carry a definite verdict in every completion, possibly none; L4 and L9 are restated. **v0.24** (2026-10-17, #68): §5.4 gives a `U` from a value basis kind `fact` only when a state property's status caused it, and kind `constraint` otherwise. **v0.23** (2026-10-17, `decisions/0015`, #52): §3.1 and §3.3 carry `skos:broader` and `skos:inScheme` edges in `closure`, and §3.3 says that a concept outside its operand's schemes gives `U`; §5.4 names the witness source, which `due2-profiles.md` §3 makes explicit, and gives `U` for a value that does not fit its operator. **v0.22** (2026-10-17, `decisions/0013`, #64): §3 says that `constraint_value` does not depend on how the policy writes a set right operand. **v0.21** (2026-10-17, `decisions/0012`, #56): §6.4 says that parts which are not the same expression or its complement stay separate variables, and what that costs; §9 open decision 6 names distinct values of a single-valued field. **v0.20** (2026-10-17, #59): §6.4 says that relation and party parts are keyed like constraint parts, so atoms share a literal as `decisions/0011` #2 assumes. **v0.19** (2026-10-17, `decisions/0011`): §6.4 says what "the `U` atoms whose completion changes the outcome" are, the atoms with a pivotal literal; §3.5 adds `verdict_range`, the least and greatest completion verdict of an `Indeterminate`; §3.7 names remedies as open (#61). **v0.18** (2026-10-16, issue #57): §3.5 says which atom `eliminated` names as `by_atom` under each rule; §3.7 says how the corpus projects `verdict_basis` and `eliminated` to authored IRIs, and that a role's atoms collapse when they share a source. **v0.17** (2026-10-16, `decisions/0010`): the new §3.7 makes the trace the explanation; the new law L10 (explicability) is in §8; §3.5 names the rule values `eliminated` records; §3.6 points to stage 1's lineage. **History:** v0.4–v0.16 are in git — every commit cites the sections it touched — and in `decisions/0003`–`0008`. v0.16 recorded an evaluation once, in `evaluation`, sharing the case's `seq` with `event` (§7.1).

**Coherence updates, 2026-10-10** (after `decisions/0002`): L9 restated as a refinement — conditional-duty hoisting splits one unknown into correlated findings completed independently, so the equality as previously written cannot hold under unknowns; L6 scoped to §6.2's conflict eliminations, because `eliminated` now also records `violated_precondition` removals (§3.5, §6.1), which give a closed route visibility in `verdict_basis` (role `closed`); the absent conflict term takes a selected profile's declared default first (normalisation spec §3); §5.3's no-guard sentence scoped to the parent relation.

## `correctness-strategy.md`

**Changes in v0.21** (2026-10-26, #23): §7 names the workflows of the tiers; the slow tier's runs the Alloy models and clingo-i's slow bounds. Earlier changes are in `docs/archive/changes.md`.

**Changes in v0.20** (2026-10-26, `decisions/0039`, #136): §4.3's lineage bullet names the lineage relation that L10 reads, and §4.6 reads the lineage of each policy. Earlier changes are in `docs/archive/changes.md`.

**Changes in v0.19** (2026-10-26, `decisions/0038`, #107): §4.2 drops invariant 10 (*Locality*), and the model-based tests of §4.7 open a new case on an amendment.

**Changes in v0.18** (2026-10-26, #83): §8 lists only the steps that remain, and §9 says in one line where each resolved row is settled; the steps taken and the rows' statements moved to `docs/archive/correctness-strategy-completed.md`. No rule changes. Earlier changes are in `docs/archive/changes.md`.

**Changes in v0.17** (2026-10-26, `decisions/0037`, #134): §4.2's invariant 7 is that an all-atomic policy normalises to itself, and §3's `Den` row no longer names Atomic Policy construction. No rule changes.

**Changes in v0.16** (2026-10-25, `decisions/0027` amendment of 2026-10-25, #38, #41): clingo-i's slow mode, read through its relation-level face (#41), replaces the brute-force W3 (#38) as the W2/W3 evaluator's executable oracle, beside the vectors' hand-derived traces, in §3, §4.5, §7, §8, and §9; §4.5 states how a fallback is compared with it. Earlier changes are in `docs/archive/changes.md`.

**Changes in v0.15** (2026-10-24, #114): §4.4 and §4.5 follow the restated laws L2, L3, L6, and L7 and give each law's first property-test cases; §4.7's *pinning suffices* excepts the `evaluation` tuple.

**Changes in v0.14** (2026-10-24, `decisions/0030`, #111): §4.7 adds the property that an access evaluation's `at` is never earlier than its `effective_at`, and that its request differs from its case's only in `at`; a moved `at` is a cause of a verdict transition. Earlier changes are in `docs/archive/changes.md`.

**Changes in v0.13** (2026-10-23, `decisions/0023`, #84): §4.8's claim K cites `decisions/0023` and gains the Alloy models as evidence. No rule changes. Earlier changes are in `docs/archive/changes.md`.

**Changes in v0.12** (2026-10-22, #83): a length pass. Dates leave the headings and markers; §4.1 drops the history of the clingo audit; §4.5 and §9 state `check_completion.py`'s coverage once; §4.8's R9 risk points at claim W; §8 step 1 no longer names row 10; §9 rows 2, 3, 5, and 10 cite their sections instead of restating them, and row 10 cites clingo-i's measured bounds instead of copying them. No rule changes. Earlier changes are in `docs/archive/changes.md`.

**Changes in v0.11** (2026-10-20, #83): a cold read. Cross-document references name their document; status markers and struck-through items leave §3, §4.2, §4.5, §4.7, §7, and §8; §3 restates why `I` running the corpus checks R5; §9 lists the open rows with their issues and states rows 1–9 below the table, keeping the row numbers. No rule changes. Earlier changes are in `docs/archive/changes.md`.

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

**Changes in v0.9** (2026-10-26, `decisions/0038`, #107): §2.4 drops the canonical N-Quads term form, which no id is computed from any more, and says that a digest is a collection id. Earlier changes are in `docs/archive/changes.md`.

**Changes in v0.8** (2026-10-26, `decisions/0037`, #134): §2.4 names one RDF boundary, the input; W1 emits no RDF. Earlier changes are in `docs/archive/changes.md`.

**Changes in v0.7** (2026-10-22, #83): a length pass. Dates leave the headings and markers; §4 drops a recommendation its pick overrides; §7.1 and §11 lose history; §13 states the resolved rows more briefly. No rule changes. Earlier changes are in `docs/archive/changes.md`.

**Changes in v0.6** (2026-10-20, #83): a cold read. §4 no longer calls its tool undecided; §2.2 names the diagnostics document; §10.2, §10.3, §11, §12, and §14.3 lose their status and history markers; §13 lists the open rows with their issues and states the resolved rows below the table, row 12 as `decisions/0009` and `decisions/0021` leave it; §15 states its reason without the history. No rule changes. Earlier changes are in `docs/archive/changes.md`.

**Changes in v0.5, 2026-10-19** (`decisions/0021`): §9 follows Cedar's pattern, an executable model, proofs, and differential testing, in place of Dafny extraction; §6, §10, §11, and §12 drop their Dafny mentions.

**Changes in v0.4, 2026-10-17:** new §15 — documentation: the cold reader, kinds of text (status kept out of reference), vocabulary, interfaces, worked examples, arguments with their steps, cross-references that name their document, code comments (PEP 257 for Python; clindocs blocks for ASP), and the checks that enforce them: the generated reference (mkdocstrings and clindocs, provisional) and clingo-i's doc tests. §14.1 step 2 cites it.

**Changes, 2026-10-16:** new §14 — the development cycle (design, docs, test, code, verify), the backlog's structure (sub-issues, milestones), branches, and CI; §12 step 9 is done. §13's tracking narrowed to the picks still open (#4, #8); the register-tracking convention is stated once in `due2-architecture.md` §11. New §7.4: one shared suite for every spike (`spikes/README.md`); §11's basedpyright scope extended to `tests/`.

**Changes in v0.3:** new §2.4 — RDF at the boundary: parse and emit at the edges, plain frozen structures everywhere between.

**Coherence updates, 2026-10-10:** §9's blocker resolved — Dafny is installable here, and `decisions/0002` records the track (register #9, #12); §7.1's preservation property restated as the refinement of `due2-workflows.md` §8 L9, whose L9 oracle is a direct interpreter over the lifted (authored) form.

**Changes in v0.2:** §2.3 (where exhaustiveness actually pays), new §5.1 (absent / unknown / false), §7.1 (semantic-preservation property), §9 (verification retargeted at the normaliser), §10 (rewritten around the two-stage split; Rego/OPA added), §11 (generated-code rule generalised), §13 (register extended). Companion document: `due2-architecture.md`.

## `due2-profiles.md`

**Changes in v0.24** (2026-10-26, `decisions/0045`): there is no config. §3 *Admissibility*: the orchestrator records answers only from the sources registered for a property, so W2 combines every recorded answer. §6 adds the role `due2:attester`, played by `due2:attestingParty`, which names whose evidence counts for a duty. §7 *Violations and access*: a violated obligation never denies. §8.2 exception 6 covers every case where DPROD denies for a violation. Earlier changes are in `docs/archive/changes.md`.

**Changes in v0.23** (2026-10-26, `decisions/0040`, #137): §3 *Admissibility* keeps `admit_source`, which W2 applies when it combines the answers of several sources, and drops `admit_age`, because keeping values current is the SOTW service's job. Earlier changes are in `docs/archive/changes.md`.

**Changes in v0.22** (2026-10-26, `decisions/0038`, #107): §7 keys `activation` by the duty atom, and §8.1 says that an anonymous rule's identity is minted. Earlier changes are in `docs/archive/changes.md`.

**Changes in v0.21** (2026-10-25, #127): §8.1 states which DPROD examples pass unchanged, and why the others are rejected. Earlier changes are in `docs/archive/changes.md`.

**Changes in v0.20** (2026-10-25, #126): §5 rejects logical constraints whose members form a cycle.

**Changes in v0.19** (2026-10-25, #125): §4 and §7 reject a temporal literal whose lexical form names no value of its datatype.

**Changes in v0.18** (2026-10-24, `decisions/0034`, #117): §5 rejects a logical constraint with more than one operand property.

**Changes in v0.17** (2026-10-24, `decisions/0033`, #115): §2 rejects a declared profile that due2 has no module for.

**Changes in v0.16** (2026-10-23, `decisions/0024`, `decisions/0025`, #101, #102): §4 gives a `dateTime` a timezone and a `date` none, and rejects an operator of one left value over a set-valued operand; §7's absolute deadline has a timezone.

**Changes in v0.15** (2026-10-22, #83): a length pass. Dates leave the reference text; §1 and §9 #7 state DPROD's provisional status once, in §8; §4's sentence on warnings is shorter; §7 cites exception 6 instead of restating it; §8.2 cites EKGF/dprod#285 for the gaps reported upstream. No semantics change. Earlier changes are in `docs/archive/changes.md`.

**Changes in v0.14** (2026-10-22, `decisions/0022`, #100): §5 rejects a logical constraint whose list names a node twice, and an `odrl:xone` with two members, neither a logical constraint, of the same content. Earlier changes are in `docs/archive/changes.md`.

**Changes in v0.13** (2026-10-20, #83): a cold read. §1 says where `formal-semantics.md`, RL2's documents, the IM, and the Vocabulary are; cross-document references name their document, the §2 table's included; history markers leave the reference text, and §3's account of an earlier draft becomes the reason for the present rule; §7 states the timing rejections the registry cites, and names a case where exception 6 diverges; §8.1 says which property `dprod:currentAgent` reads; §8.1's collection-refinement row drops the MDS mapper, a separate project; §9 lists the open rows with their issues and states rows 5 and 6 as closed, keeping the row numbers. No semantics change. Earlier changes are in `docs/archive/changes.md`.

**Changes in v0.12** (2026-10-17, `decisions/0017`, #74): §5 rejects a logical constraint over the empty list.

**v0.11** (2026-10-17, `decisions/0013` amendment, #69): §4 rejects an empty list as a set right operand. **v0.10** (2026-10-17, `decisions/0016`): §3 says that only an `unresolved` value is completed. **v0.9** (2026-10-17, #68): §3 *Kinds* says what `rdfs:Literal` and `rdfs:Resource` admit. **v0.8** (2026-10-17, `decisions/0014`, `decisions/0015`, #52, #65): §2 gives an operand's type to the lowest layer that declares it, lets higher layers rebind only its source and property, and drops the order of profile modules; §3 defines kinds, compares values by kind when there is no range, and checks a binding's range against the read property's; §4 and §6 compare concepts under a declared SKOS concept scheme. **v0.7** (2026-10-17, `decisions/0013`, #64): §4 admits a set right operand written as repeated values as well as an RDF list, and rejects the forms with no reading. **v0.6** (2026-10-16): every DPROD-derived adoption is marked provisional against the vendored commit, pending a batch of upstream PRs (§1, §8, §9 #7; issue #35); §3's context table names `dprod:agent`, the `dprod:EvaluationContext` property (`dprod-contracts.ttl`) that the left operand `dprod:currentAgent` reads through `dprod:operandProperty` — the table lists properties, as its `dprod:clock` row does; §9 rows #2 and #5 are merged (issue #18). **History:** v0.3–v0.5 are in git; the substantive decisions are `decisions/0005`, and `decisions/0001` for the DPROD adoption itself.

## `due2-diagnostics.md`

**Changes in v0.17** (2026-10-26, `decisions/0036`, #130): `IdentityConflict` covers two policies normalised together whose corpora say different things of one node, found by the union, a step after stage 2 (§1).

**Changes in v0.16** (2026-10-25, #126): `MalformedConstraint` covers logical constraints whose members form a cycle.

**Changes in v0.15** (2026-10-25, #125): `OperatorTypeMismatch` and `InvalidTiming` cover a temporal literal whose lexical form names no value of its datatype.

**Changes in v0.14** (2026-10-25, #129): `MisplacedConstraint` covers a refinement or a constraint outside its vocabulary domain on any node, a party that a profile's own role names among them.

**Changes in v0.13** (2026-10-25, `decisions/0034`, #124): `LiteralEntity` covers every `rdfs:subPropertyOf` descendant of `odrl:function` and `odrl:relation`, a profile's own party roles among them.

**Changes in v0.12** (2026-10-25, `decisions/0034` amendment, #122, #123): `UnsupportedConstruct` covers `odrl:assignerOf` and `odrl:assigneeOf`; `InvalidActionHierarchy` covers a blank action node without `rdf:value`.

**Changes in v0.11** (2026-10-24, `decisions/0034`, #117): new rows `InvalidActionHierarchy` and `LiteralEntity`; `UnsupportedConstruct` covers `odrl:hasPolicy`; `MalformedConstraint` covers a logical constraint with more than one operand property.

**Changes in v0.10** (2026-10-24, `decisions/0033`, #115): new rows `ReplacedPolicy` and `UnrecognisedProfile`; `UndeclaredProfile` names the code that rejects a policy whose profile has no due2 module.

**Changes in v0.9** (2026-10-23, `decisions/0024`, `decisions/0025`, #101, #102): `OperatorTypeMismatch` covers a `dateTime` right operand without a timezone, a `date` right operand with one, and every operator of one left value over a set-valued operand; `InvalidTiming` covers a deadline without a timezone.

**Changes in v0.8** (2026-10-22, `decisions/0022`, #100): `MalformedConstraint` covers a logical constraint whose list names a node twice, and an `odrl:xone` with two members, neither a logical constraint, of the same content. Earlier changes are in `docs/archive/changes.md`.

**Changes in v0.7** (2026-10-20, #93): new row `MisplacedConstraint`; `InvalidNesting` is checked and covers every Rule edge outside the subject the ODRL vocabulary gives it, and a node in two Rule classes; `UnsupportedConstruct` covers an `odrl:constraint` on the Policy. Earlier changes are in `docs/archive/changes.md`.

**Changes in v0.6** (2026-10-20, #83): a cold read. Cross-document references name their document, in the prose and in the registry's "Defined in" column; the timing rows and `UnsupportedConstruct` cite sections that now state their rejections (`due2-profiles.md` §7, `odrl-compound-to-atomic-normalization.md` §3). No code, severity, stage, or condition changes. Earlier changes are in `docs/archive/changes.md`.

**Changes in v0.5** (2026-10-17, `decisions/0017`, #74): `MalformedConstraint` covers a logical constraint over the empty list.

**v0.4** (2026-10-17, `decisions/0013` amendment, #69): `MalformedConstraint` covers an empty list as a set right operand. **v0.3** (2026-10-17, `decisions/0014`, `decisions/0015`): new rows `ConflictingProfileDeclaration` (named in profiles §2 since v0.4 but never registered), `RetypedOperand`, and `OperandRangeMismatch`; `InvalidBinding` and `OperatorTypeMismatch` cover concept schemes. **v0.2** (2026-10-17, `decisions/0013`, #64): `MalformedConstraint` covers more than one right-operand value on an operator that is not set-based, and a set right operand that mixes a list with other values or gives two lists.

## `due2-architecture.md`

**Changes in v0.18** (2026-10-26, `decisions/0046`): §7's first re-evaluation trigger is an explicit call per case, with no subscription. Earlier changes are in `docs/archive/changes.md`.

**Changes in v0.17** (2026-10-26, `decisions/0045`): there is no config, so `decide` takes the corpus, the request, and the SOTW (§2, §7). §6.2 fixes prohibit-overrides across policies, and a void policy's violated obligation is reported, not denied. A duty's attester names whose evidence counts (§3). §0's worked example is the case's `Permit` scenario, with the violated delivery reported. Earlier changes are in `docs/archive/changes.md`.

**Changes in v0.16** (2026-10-26, `decisions/0040`, `decisions/0042`, #137, #139): §7 says that a case and its evaluations together pin their inputs (`decisions/0042`), and §8 harvests RL2's admissibility by source but not its freshness filter, which is the SOTW service's job (`decisions/0040`). Earlier changes are in `docs/archive/changes.md`.

**Changes in v0.15** (2026-10-26, `decisions/0038`, #107): §3 says that an anonymous rule's identity is minted, and §7 that an amendment reaches an earlier request through a new case, what evidence for a grant names, and that the re-evaluation trigger is a change of facts or evidence. Earlier changes are in `docs/archive/changes.md`.

**Changes in v0.14** (2026-10-26, `decisions/0036`, #130): the in-force row of §0 says that an obligation is in force when one of the policies that state it matches. Earlier changes are in `docs/archive/changes.md`.

**Changes in v0.13** (2026-10-24, `decisions/0030`, #111): §7's case flow says that a re-evaluation asks at its own time, with the request's `at` moved to its `effective_at`.

**Changes in v0.12** (2026-10-24, `decisions/0029`, #110): §6.2 says that a void policy keeps its root obligations, and names the departure from ODRL's reading. Earlier changes are in `docs/archive/changes.md`.

**Changes in v0.11** (2026-10-24, `decisions/0028`, #109): §4 item 3 makes only a root rule's DNF disjuncts atoms; a duty's become clauses of its one atom, and the blowup budget's exact count includes them. Earlier changes are in `docs/archive/changes.md`.

**Changes in v0.10** (2026-10-24, #83): §0's reading order and directory map name `due2-platform.md`, `schema/`, `spikes/`, and `formal/`. No design changes.

**Changes in v0.9** (2026-10-22, #83): a length pass. Dates and version history leave the reference text; §0's walk-through drops clingo-i's status; §4 item 5 states the rejected alternative in one sentence; §10 cites L9 instead of restating it. No design changes.

**Changes in v0.8** (2026-10-20, #83): §0's walk-through follows all six rules of its case; §8.1 opens with what it covers, and SKOS concept schemes are decided; §9 describes the execution choice as `decisions/0002` and `decisions/0006` leave it; §10 states semantic preservation and its oracles in the present tense; §11 drops the four resolved rows and names each open row's issue; references name their documents. Earlier changes are in `docs/archive/changes.md`.

**Changes in v0.7** (2026-10-16): the tracking convention for every open-decision register is stated here, once (§11); the DPROD relation is marked provisional against the vendored commit, pending upstream PRs (§8.3). Earlier changes are in `docs/archive/changes.md`.

**History:** v0.4–v0.6 are in git; the substantive amendments are recorded in `decisions/0001`–`0003`.

## `due2-platform.md`

**Changes in v0.14** (2026-10-26, `decisions/0045`, `decisions/0046`): `decide` takes three inputs, and the connector registry, keyed by property and source, decides whose answers a case records (§1.4, §2.4). §1.3 tells apart the two relations named `evaluation`, and §2.3 drops the configured rule for violated obligations. Publication is a workflow of its own (§2.11). A case changes only by explicit calls, among them `record_facts`, `refresh`, `reevaluate`, and `reopen` (§2.6). Earlier changes are in `docs/archive/changes.md`.

**Changes in v0.13** (2026-10-26, `decisions/0043`, `decisions/0044`): `resolve` and `edges` return the source's version with each answer, and `edges` answers per request entity with the edges on the paths up from it (§2.4). Earlier changes are in `docs/archive/changes.md`.

**Changes in v0.12** (2026-10-26, `decisions/0040`, `decisions/0041`, `decisions/0042`, #137, #138, #139): each state fact is one source's answer, the evaluator combines the admitted ones, and the SOTW service keeps values current (§1.4, §2.4, §2.6, §3.1, §5 #7). `decide` returns the whole trace, and the orchestrator builds no part of it (§2.2, §2.6). A case fixes its request, corpus, config, and pins, so `create_case` takes all four (§2.2, §2.6, §2.10). Earlier changes are in `docs/archive/changes.md`.

**Changes in v0.11** (2026-10-26, `decisions/0039`, #136): §2.3 finds a policy's lineage by the policy, its version, and the normaliser version, and §2.10 says how explanation reaches it. Earlier changes are in `docs/archive/changes.md`.

**Changes in v0.10** (2026-10-26, `decisions/0038`, #107): a case fixes its corpus, so `create_case` takes one, and an amended policy reaches an earlier request through a new case (§2.2, §2.6, §2.11, §3.3, §3.5). Evidence names its grant in two fields (§3.2). `put_corpus` renames the ids W1 minted for a published node's parts to the published ones (§2.3), and a policy version is a minted id (§2.3).

**Changes in v0.9** (2026-10-26, `decisions/0037`, #134): §2.3 and §5 #1 say "per root atom", since stage 1 builds no Atomic Policy. Earlier changes are in `docs/archive/changes.md`.

**Changes in v0.8** (2026-10-26, `decisions/0036` amendment, #132): §2.3 publishes one policy's corpus at a time, refuses one that disagrees with a published corpus, and returns the union of exactly the selected policies' corpora; §5 #1 no longer asks which sets of policies get a corpus. Earlier changes are in `docs/archive/changes.md`.

**Changes in v0.7** (2026-10-24, `decisions/0033`, #115): §2.3 says that the store selects the replacement of a replaced policy, never the policy it replaces.

**Changes in v0.6** (2026-10-24, `decisions/0032`, #113): §3.2 says that evidence names the grant it answers, the authored duty and the request's `reference`, not an instance key.

**Changes in v0.5** (2026-10-24, `decisions/0031`, #112): §2.3 says that offers are selected like any other policy, and §3.1 shows a `Permit` over an offer as "this offer permits you to proceed". Earlier changes are in `docs/archive/changes.md`.

**Changes in v0.4** (2026-10-24, `decisions/0030`, #111): §2.6 says that a case's request is fixed except for `at`, which each evaluation moves to its own time, and that the orchestrator never sends an access evaluation an `at` earlier than its `effective_at`. Earlier changes are in `docs/archive/changes.md`.

**Changes in v0.3** (2026-10-24, #83): edited for a cold reader: terms defined, the case workflow called the orchestrator throughout, the worked example marked as an illustration, and repetitions cut. §2.5 states what the specification says about a failed hierarchy lookup. No design changes.

## `odrl-compound-to-atomic-normalization.md`

Changes in 0.25 (2026-10-26, `decisions/0038`, #107): every id that no author chose is minted, not computed from content (§5.2). `source_digest` and invariant 10 (*Locality*) are dropped, values are no longer ordered for expansion (§6.3), and W1 is deterministic up to the renaming of minted ids (§8, invariant 6).

Changes in 0.24 (2026-10-26, `decisions/0037`, #134): `N(P0)` is internal to W1 and never serialised (§1, §4). The `atomic-policy` and `activity` id domains and the Atomic Policy node are dropped, and each atomic root Rule occurrence is a root atom of the authored policy (§5.2, §6.4). The lineage is recorded as tuples, without PROV-O (§7), and invariant 7 says that an all-atomic policy normalises to itself (§8). Earlier changes are in `docs/archive/changes.md`.

Changes in 0.23 (2026-10-26, `decisions/0036` amendment, #132): §1 defines `EvalSet` over the union of agreeing corpora, and §5.1 says that a policy that disagrees with a published one is rejected when it is published. Earlier changes are in `docs/archive/changes.md`.

Changes in 0.22 (2026-10-26, `decisions/0036`, #130): §5.2 says that an anonymous node is identified by its place, so two anonymous nodes in different places are distinct, and that sharing is stated by naming. §5.1's rule that distinct resources do not claim one identity extends to the policies normalised together.

Changes in 0.21 (2026-10-25, #129): §3 places a refinement and a constraint by the vocabulary's domains: a constraint on anything other than a Policy or a Rule, and a refinement on anything other than an Action or a collection, are rejected, whatever property reaches the node.

Changes in 0.20 (2026-10-25, `decisions/0034`, #124): §3 reads the properties whose value must be a resource from the vocabularies, as `odrl:function`, `odrl:relation`, and their `rdfs:subPropertyOf` descendants, so a profile's own party roles are covered.

Changes in 0.19 (2026-10-25, `decisions/0034` amendment, #122, #123): §3 defines a refined action by its `rdf:value`, whatever its node kind, rejects a blank action node without one, and rejects `odrl:assignerOf` and `odrl:assigneeOf` with `UnsupportedConstruct`.

Changes in 0.18 (2026-10-25, `decisions/0032` amendment, #121): §5.2 notes the two id domains that stage 2 and W2 mint under its namespace. No rule changes.

Changes in 0.17 (2026-10-24, `decisions/0034`, #117): §3 requires two properties of the ODRL Information Model that the vocabulary's domains do not state: Assets and Parties are resources (`LiteralEntity`), and every action reaches `odrl:use` or `odrl:transfer` (`InvalidActionHierarchy`); it rejects `odrl:hasPolicy` with `UnsupportedConstruct`.

Changes in 0.16 (2026-10-24, `decisions/0033`, #115): §3 rejects a Policy with `dct:isReplacedBy` (`ReplacedPolicy`) and a declared profile that due2 has no module for (`UnrecognisedProfile`).

Changes in 0.15 (2026-10-20, #93): §3 requires every constraint and every Rule to sit where the ODRL vocabulary places it, and rejects a misplaced one with `MisplacedConstraint` or `InvalidNesting`; a constraint on the Policy itself joins the constructs rejected as `UnsupportedConstruct`; §6.3 and §10 follow. Admitted input narrows; generated identity is unchanged. Earlier changes are in `docs/archive/changes.md`.

Changes in 0.14 (2026-10-20, #83): a cold read, spelling `artifact`. §3 lists the constructs outside the fragment that `due2-diagnostics.md` rejects as `UnsupportedConstruct`, with the reason for each; §5.2 and §6.1 no longer say that §3 requires Rules to be named, which §3 does not; §6.2 says whose phrase “each Rule in the Policy” is and where DPROD's rule is compared; §8.1 names `ways-of-working.md` and says where `Den` is formalised (`correctness-strategy.md` §4.8). Admitted input, as the registry and `tools/check_corpus.py` already drew it, and generated identity are unchanged. Earlier changes are in `docs/archive/changes.md`.

Changes in 0.13: an anonymous target or assignee is admitted with the `AnonymousEntity` warning (§3); admitted input and generated identity are unchanged.

Changes in 0.12: selected profile modules as input (§3); profile policy subclasses and conflict default (§3); anonymous Rules admitted with local identity (§3, §5.1); policy identity by IRI or `odrl:uid` (§3); interiorisation fills only what a Rule leaves unstated, so `InteriorizationRelationConflict` cannot arise (§6.2). Changes in 0.11: §3 states that named Rules are stricter than ODRL. Changes in 0.10: named Rules and label-independent, local anonymous-node identity (§3, §5.2); RDFC-1.0 removed from the identity path (§5.2, §6.1); all three conflict values accepted, an absent term made explicit as `odrl:invalid` (§3); Rule-reference acyclicity (§6.3); preservation stated over a denotation and witnessed by lineage (§8). The profile version stays `1` because no artefact has been produced under it. Any later change to admitted input or generated identity bumps it.

## `conformance/README.md` § Coverage gaps

Re-derived 2026-10-26, after `decisions/0045` removed the config (five scenarios removed, one added to `due2-grant-signers`), and after `due2-violated-precondition-beside-permission` was added.

Earlier re-derivations: 2026-10-25, after `due2-assigner-of` and `due2-assignee-of` (#122), `due2-action-without-value` and `due2-refined-action-skolem` (#123), `due2-literal-bearer` (#124), `due2-constrained-bearer` (#129), `due2-impossible-operand`, `due2-impossible-deadline`, and `due2-week-duration` (#125), and `due2-constraint-cycle` (#126).; 2026-10-24, after `due2-literal-party`, `due2-and-or`, `due2-two-right-operand-references`, `due2-action-without-parent`, `due2-action-two-parents`, and `due2-has-policy` (#117); 2026-10-24, after `due2-datetime-no-timezone`, `due2-date-with-timezone`, `due2-eq-over-set`, `due2-deadline-no-timezone`, and `due2-mixed-duration` (#116); 2026-10-24, after `due2-replaced-policy` and `due2-unrecognised-profile` (#115); 2026-10-24, after `due2-unknown-fulfilment-deadline` and `due2-grant-two-targets` (#113); 2026-10-24, after `due2-reevaluation-moves-at` (#111); 2026-10-24, after `due2-void-keeps-obligation` (#110); 2026-10-24, after `due2-duty-disjunction` (#109); 2026-10-22, after the repeated-member cases of #100; 2026-10-20, after the placement cases of #93; 2026-10-19, after `due2-nested-unknowns` (#81); 2026-10-17, after the negative case `due2-empty-logical-constraint` (`decisions/0017`), after the concept-scheme cases `due2-concept-purpose`, `due2-concept-purpose-prohibition`, `due2-concept-complement`, and their three negative cases (`decisions/0015`), and `due2-empty-right-operand` (`decisions/0013`, amendment), after `due2-unresolved-or-missing` and the change to `due2-shared-reads` (`decisions/0016`), after the operand-binding cases `due2-rebound-pay-amount`, `due2-retyped-operand`, and `due2-operand-range-mismatch` (`decisions/0014`), after `due2-repeated-right-operand` and `due2-malformed-right-operand` (`decisions/0013`), and after `due2-shared-reads` (`decisions/0012`); 2026-10-16, after the explanation fields (#57) and the OVAL refresh (#51).

## README § Status, as it stood on 2026-10-19

Specification and corpus only — no evaluator yet; every expected verdict is hand-derived. Open items are GitHub issues (labels `open-decision`, `corpus`, `verification`, `work-item`, `parked`), each pointing at the section that holds its source of truth. The first runner of the corpus is the semantics program (issue #9, `decisions/0009`) — a generic clingo program over flattened ODRL, the L9 oracle and the test generator, run first over the corpus's authored policies (the correctness strategy is adopted; the enumeration bounds remain open, #42). Its spike, `spikes/clingo-i/`, was built in increments (#45, #46, #59, #47–#50): the walking skeleton (#45), the complete driver (#46), the explanation (#59: `verdict_basis`, `eliminated`, and an `Indeterminate`'s pivotal `unknown` atoms and `verdict_range`, `decisions/0011`), constraints (#47: the authored trees under strong Kleene logic, bindings, reads, refinements, and typed `partOf`), the layered operand bindings of `decisions/0014` (#68), the constraint completion variables of `due2-workflows.md` §6.4 (#48), the opaque parts and `unknown_parts` of `decisions/0016` (#72), concept-scheme operands under `skos:broader` (#69, `decisions/0015`), and duties (#49: closure before conflict, deadlines, the frontier, `Pending`, and `unknown` duty findings, `decisions/0018`, `decisions/0019`) are done. It passes 400 of the corpus's 438 scenarios and declines the other 38, naming the feature: 37 depend on occurrences (`unsupported: recurrence`), and one states `exact: false`, past the `max_mixed` bound, for which the spike has no fallback (`decisions/0009`). The corpus gate (#50) closes #9: every scenario it runs agrees with its hand-derived answer, and the one disagreement found, a corpus error, is triaged (#76). Next, the formalisation review (#70). Then the W2/W3 bakeoff on relation-level vectors — Clingo and Elixir first, Python deferred (`decisions/0006`) — then W1 with the Dafny `Den` oracle (#8).
