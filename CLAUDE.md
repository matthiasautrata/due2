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
- **Every commit:** every command in `README.md` § Verify passes: the checkers, strict basedpyright, ruff, and rumdl. Push when done.

## Where the semantics live

| Question | Section |
|---|---|
| What a request, SOTW, corpus, and trace contain | `due2-workflows.md` §3 |
| When an atom applies; guards (`owed`) vs witness conditions | workflows §5.2 |
| Fulfilment, deadlines, recurrence, instances | workflows §5.3 |
| Candidates, conflict, frontier, verdict, completion over literals | workflows §6 (§6.4 has the monotonicity proof) |
| Laws L1–L9 (property-test targets) | workflows §8 |
| Normalisation stage 1 (normative) | `odrl-compound-to-atomic-normalization.md` |
| Every rejection and warning code; which stage emits it | `due2-diagnostics.md` |
| Operand bindings, profiles, DPROD compatibility | `due2-profiles.md` |
| Engineering discipline (types, contracts, testing tiers) | `ways-of-working.md` |
| Which check guards which risk; oracles; per-component gates | `correctness-strategy.md` |

## Next

Settle the remaining `correctness-strategy.md` §9 items. Then issue #9: the L9 oracle, a Python direct interpreter over the authored (lifted) form. Slow mode first: it completes unknown literals by the workflows §6.4 definition, enumerating every assignment below a cap (correctness-strategy §3), and runs the corpus; first target, all 99 positive cases (the 8 negative ones wait for W1). Then the W2/W3 backend bakeoff (`decisions/0006`): Python, Elixir, and Clingo on relation-level vectors, which first needs the collection encoding (issue #3). Then #8, the Dafny `Den` oracle (`decisions/0002`). Tooling picks still open at implementation start: issue #23.
