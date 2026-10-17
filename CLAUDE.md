# due2 — working notes for Claude Code

due2 is an ODRL 2.2 policy evaluation runtime: three-valued (Kleene) evaluation, five verdicts (`Permit`, `Deny`, `Pending` with a frontier of duty routes, `NotApplicable`, `Indeterminate`), and replayable decisions. This repository holds the specification, the conformance corpus, and the checkers. **There is no evaluator yet.** Every expected verdict is hand-derived.

Start with `README.md` (layout, verify commands, status), then `docs/design/due2-architecture.md` §0 (reading order). Documents live under `docs/{spec,design,correctness,decisions}/` and cite each other by bare file name.

## Rules that are easy to break

- **The repo is the only source of truth.** No other copy is maintained: not the claude.ai project, not chat attachments.
- **Unknown is never false.** Missing, invalid, conflicting, or unresolved data makes a part `U`, and `U` survives to the verdict (`ways-of-working.md` §5.1). Every external evaluator gets this wrong (`conformance/external/README.md`); do not copy their behaviour.
- **Correctness strategy before code.** No component gets implementation code until its entry in `docs/correctness/correctness-strategy.md` §4 names its risks, oracles (and what each shares with the implementation), properties, golden vectors, generators, and done-gate.
- **Spec before code.** Spec text carries markers: **[D]** decided, **[O]** open (alternatives listed), **[F]** blocked externally. A design change lands as a spec edit, plus a record in `docs/decisions/` when it reverses or settles something load-bearing. The matching GitHub issue closes afterwards, with the commit cited. Open items live in issues (labels `open-decision`, `corpus`, `verification`, `work-item`, `parked`), and each issue names its source-of-truth section.
- **Corpus cases** (`conformance/cases/<origin>-<name>/`, format in `conformance/README.md`):
  - every rule is named;
  - every left operand is bound;
  - every expected verdict carries a one- or two-sentence `why` derived from workflows §5–§6;
  - a translated case keeps its origin's answer (`force_expected`, `oval_expected`, `w3c_expected`, …) and explains any difference in `notes`;
  - external suites under `conformance/external/` are vendored unmodified — never edit them;
  - re-derive the coverage-gap list in `conformance/README.md` (and issue #2) when cases change.
- **Every increment** follows `ways-of-working.md` §14: design, docs, test, code, verify. Its issue states the design and the gate; a multi-increment item is a parent issue with sub-issues and a milestone. Work by another model or agent arrives as a pull request, never a direct push to `main`.
- **Documentation is written for a cold reader** (`ways-of-working.md` §15): prose, docstrings, and ASP doc blocks alike. Use the skill in `.claude/skills/technical-writing/` whenever you write or review any of them. Status goes in issues, the journal, and README § Status, not in reference text. clingo-i's generated reference is built by MkDocs (mkdocstrings and clindocs) and checked by `tests/test_docs.py`.
- **Research gets an entry** in `docs/design/references.md`: the citation, what was read, what was learned, and where it is used. It may become a paper's bibliography.
- **Every commit:** every command in `README.md` § Verify passes: the checkers, strict basedpyright, ruff, and rumdl. CI (`.github/workflows/verify.yml`) re-runs them on every push. Push when done.

## Where the semantics live

| Question | Section |
|---|---|
| What a request, SOTW, corpus, and trace contain | `due2-workflows.md` §3 |
| When an atom applies; guards (`owed`) vs witness conditions | workflows §5.2 |
| Fulfilment, deadlines, recurrence, instances | workflows §5.3 |
| Candidates, conflict, frontier, verdict, completion over literals | workflows §6 (§6.4 has the monotonicity proof) |
| Laws L1–L10 (property-test targets) | workflows §8 |
| What explains a verdict; what a trace must let a reader re-derive | workflows §3.7, L10 (`decisions/0010`) |
| Which `U` atoms an `Indeterminate` names; its `verdict_range` | workflows §6.4 (`decisions/0011`) |
| Normalisation stage 1 (normative) | `odrl-compound-to-atomic-normalization.md` |
| Every rejection and warning code; which stage emits it | `due2-diagnostics.md` |
| Operand bindings, profiles, DPROD compatibility | `due2-profiles.md` |
| Engineering discipline (types, contracts, testing tiers) | `ways-of-working.md` |
| Which check guards which risk; oracles; per-component gates | `correctness-strategy.md` |
| What was read, why, and what it taught (the paper's bibliography) | `references.md` |

## Next

The correctness strategy is adopted (`correctness-strategy.md` §9); its one open item (register #10, the enumeration bounds, issue #42) is set when the enumerator exists (§8 step 6). Next, issue #9 (milestone "clingo-i: corpus runner", increments #45, #46, #59, #47–#50; #45, the walking skeleton, #46, the complete driver, and #59, the explanation with `verdict_range` and the pivotal `unknown` atoms of `decisions/0011`, are done, and #47, constraints, is next): the semantics program (`decisions/0009`) — a generic clingo program over flattened ODRL — built as the first spike against the shared suite (`spikes/README.md`; journal sessions, attempts, bugs, and checker runs as you go), in `spikes/clingo-i/`, implementing `interpret`: the driver makes a syntactic flatten of the vector's authored policy to facts (no expansion, no DNF — those are the program's rules); slow mode first — one answer set per completion of the unknown literals, a verdict definite iff cautious-entailed, declining above a variable cap (correctness-strategy §3); every runnable scenario is the first gate (occurrence-dependent scenarios report `unsupported: recurrence`; the 10 negative cases wait for W1). Then the W2/W3 backend bakeoff (`decisions/0006`, milestone "W2/W3 bakeoff") on relation-level vectors (#36), against the brute-force W3 (#38): Clingo (#41) and Elixir (#40) first; Python (#39) is deferred, not withdrawn, until the production evaluator is written. Then #8, the Dafny `Den` oracle (`decisions/0002`). Implementation-start tooling picks still open: issue #23 (#4, #8).
