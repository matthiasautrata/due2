# due2 — working notes for Claude Code

due2 is an ODRL 2.2 policy evaluation runtime: three-valued (Kleene) evaluation, five verdicts (`Permit`, `Deny`, `Pending` with a frontier of duty routes, `NotApplicable`, `Indeterminate`), and replayable decisions. This repository holds the specification, the conformance corpus, and the checkers. **There is no evaluator yet.** Every expected verdict is hand-derived.

Start with `README.md` (layout, verify commands, status), then `docs/design/due2-overview.md` (the big picture) and `docs/design/due2-architecture.md` §0 (reading order). Documents live under `docs/{spec,design,correctness,decisions}/` and cite each other by bare file name. `docs/briefings/` holds dated snapshots that are not updated after their date, so cite them for history only.

## Rules that are easy to break

- **The repo is the only source of truth.** No other copy is maintained: not the claude.ai project, not chat attachments.
- **Unknown is never false.** Missing, invalid, conflicting, or unresolved data makes a part `U`, and `U` survives to the verdict (`ways-of-working.md` §5.1). Every external evaluator gets this wrong (`conformance/external/README.md`); do not copy their behaviour.
- **Correctness strategy before code.** No component gets implementation code until its entry in `docs/correctness/correctness-strategy.md` §4 names its risks, oracles (and what each shares with the implementation), properties, golden vectors, generators, and done-gate.
- **Spec before code.** Spec text carries markers: **[D]** decided, **[O]** open (alternatives listed), **[F]** blocked externally. A design change lands as a spec edit, plus a record in `docs/decisions/` when it reverses or settles something load-bearing. The matching GitHub issue closes afterwards, with the commit cited. Open items live in issues (labels `open-decision`, `corpus`, `verification`, `work-item`, `parked`, plus `bug` for a fault in what is already specified or built), and each issue names its source-of-truth section.
- **Corpus cases** (`conformance/cases/<origin>-<name>/`, format in `conformance/README.md`):
  - every rule is named;
  - every left operand is bound;
  - every expected verdict carries a one- or two-sentence `why` derived from `due2-workflows.md` §5–§6;
  - a translated case keeps its origin's answer (`force_expected`, `oval_expected`, `w3c_expected`, …) and explains any difference in `notes`;
  - external suites under `conformance/external/` are vendored unmodified — never edit them;
  - re-derive the coverage-gap list in `conformance/README.md` (and issue #2) when cases change.
- **Every increment** follows `ways-of-working.md` §14: design, docs, test, code, verify. Its issue states the design and the gate; a multi-increment item is a parent issue with sub-issues and a milestone. Work by another model or agent arrives as a pull request, never a direct push to `main`.
- **Documentation is written for a cold reader** (`ways-of-working.md` §15): prose, docstrings, and ASP doc blocks alike. Use the skill in `.claude/skills/technical-writing/` whenever you write or review any of them. Status goes in issues, the journal, and README § Status, not in reference text. clingo-i's generated reference is built by MkDocs (mkdocstrings and clindocs) and checked by `tests/test_docs.py`.
- **Research gets an entry** in `docs/design/references.md`: the citation, what was read, what was learned, and where it is used. It may become a paper's bibliography.
- **Every commit:** every command in `README.md` § Verify passes: the checkers, strict basedpyright, ruff, and rumdl. A commit that changes only Markdown needs only `uv run rumdl check .` and `uv run pytest tests/test_doc_references.py tests/test_vocabulary.py`, plus clingo-i's `tests/test_docs.py` and MkDocs build when it touches `spikes/clingo-i/`. CI (`.github/workflows/verify.yml`) re-runs everything on every push. Push when done.

## Where the semantics live

| Question | Section |
|---|---|
| What a request, SOTW, corpus, and trace contain | `due2-workflows.md` §3 |
| When an atom applies; guards (`owed`) vs witness conditions | `due2-workflows.md` §5.2 |
| Fulfilment, deadlines, recurrence, instances | `due2-workflows.md` §5.3 |
| Candidates, conflict, frontier, verdict, completion over literals | `due2-workflows.md` §6 (§6.4 has the monotonicity proof) |
| Laws L1–L10 (property-test targets) | `due2-workflows.md` §8 |
| What explains a verdict; what a trace must let a reader re-derive | `due2-workflows.md` §3.7, L10 (`decisions/0010`) |
| Which `U` atoms an `Indeterminate` names; its `verdict_range` | `due2-workflows.md` §6.4 (`decisions/0011`) |
| Normalisation stage 1 (normative) | `odrl-compound-to-atomic-normalization.md` |
| Every rejection and warning code; which stage emits it | `due2-diagnostics.md` |
| Operand bindings, profiles, DPROD compatibility | `due2-profiles.md` |
| Engineering discipline (types, contracts, testing tiers) | `ways-of-working.md` |
| Which check guards which risk; oracles; per-component gates | `correctness-strategy.md` |
| What was read, why, and what it taught (the paper's bibliography) | `references.md` |

## Next

1. **The W2/W3 evaluator** (`decisions/0027`; its language is #104, Kotlin leading): relation-level vectors (#37; their format and the port schema are in `conformance/README.md` and `schema/`) and clingo-i's relation-level face (#41), the gate's oracle, then the evaluator as a spike under the shared suite, gated by `decisions/0006` #4. Record the `ways-of-working.md` §10.4 measurables for the agent workload before any performance work.
2. **W1**, the normaliser, in Python, whose 53 negative cases wait for it.
3. **Documentation house-cleaning (#83)**, interleaved.

Parked: the prover spike, Lean on M (#87), and `Den` in the prover (#8), until the evaluator reaches production (`decisions/0021`, amendment of 2026-10-24). The claims' evidence meanwhile is the Alloy models (#84) and the search over clingo-i (#85). clingo-i follows `decisions/0026` with #103.

Open beside these: the implementation-start tooling picks (#23). Parked: recurrence in clingo-i (#80), with recurrence itself (#119); the brute-force W3 (#38), which clingo-i's face replaces (`decisions/0027`, amendment of 2026-10-25).
