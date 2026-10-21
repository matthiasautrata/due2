# due2 — working notes for Claude Code

due2 is an ODRL 2.2 policy evaluation runtime: three-valued (Kleene) evaluation, five verdicts (`Permit`, `Deny`, `Pending` with a frontier of duty routes, `NotApplicable`, `Indeterminate`), and replayable decisions. This repository holds the specification, the conformance corpus, and the checkers. **There is no evaluator yet.** Every expected verdict is hand-derived.

Start with `README.md` (layout, verify commands, status), then `docs/design/due2-architecture.md` §0 (reading order). Documents live under `docs/{spec,design,correctness,decisions}/` and cite each other by bare file name. `docs/briefings/` holds dated snapshots that are never updated, so cite them for history only.

## Rules that are easy to break

- **The repo is the only source of truth.** No other copy is maintained: not the claude.ai project, not chat attachments.
- **Unknown is never false.** Missing, invalid, conflicting, or unresolved data makes a part `U`, and `U` survives to the verdict (`ways-of-working.md` §5.1). Every external evaluator gets this wrong (`conformance/external/README.md`); do not copy their behaviour.
- **Correctness strategy before code.** No component gets implementation code until its entry in `docs/correctness/correctness-strategy.md` §4 names its risks, oracles (and what each shares with the implementation), properties, golden vectors, generators, and done-gate.
- **Spec before code.** Spec text carries markers: **[D]** decided, **[O]** open (alternatives listed), **[F]** blocked externally. A design change lands as a spec edit, plus a record in `docs/decisions/` when it reverses or settles something load-bearing. The matching GitHub issue closes afterwards, with the commit cited. Open items live in issues (labels `open-decision`, `corpus`, `verification`, `work-item`, `parked`), and each issue names its source-of-truth section.
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
- **Every commit:** every command in `README.md` § Verify passes: the checkers, strict basedpyright, ruff, and rumdl. CI (`.github/workflows/verify.yml`) re-runs them on every push. Push when done.

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

1. **Formalisation (#70, `decisions/0021`).** The claims M, K, F, W, and P are stated in `correctness-strategy.md` §4.8. The bounded-exhaustive spaces over clingo-i exist (#44, `spikes/clingo-i/DESIGN.md` § Tests). Next, search for counterexamples with a small Alloy model per claim and bounded-exhaustive testing (#77), and triage what they find (§6). Then spike Lean on M; Isabelle is optional. Record the spike's result as an amendment to `decisions/0021`. The chosen prover takes over `Den` (#8).
2. **Documentation house-cleaning (#83)**, interleaved with #70.
3. **The W2/W3 bakeoff** (`decisions/0006`, milestone "W2/W3 bakeoff"): relation-level vectors (#36, #37) and the brute-force W3 (#38), then Clingo (#41) and Elixir (#40). Python (#39) is deferred until the production evaluator is written.
4. **W1**, the normaliser, whose 27 negative cases wait for it.

Open beside these: recurrence in clingo-i (#80); the implementation-start tooling picks (#23).
