# due2

Specifications for due2, an ODRL policy evaluation runtime.

**Source of truth.** All due2 artefacts live in this git repository (`github.com/matthiasautrata/due2`); clone it anywhere. No other copy is maintained — the claude.ai project holds only a pointer here. Change files here and commit.

| Path | Covers |
|---|---|
| `CLAUDE.md` | Working notes for Claude Code: the rules that are easy to break, where the semantics live, what's next |
| `.claude/skills/technical-writing/` | The procedure, templates, and review checklist for writing any prose, docstring, or ASP doc block (`ways-of-working.md` §15) |
| `.github/` | CI (`workflows/verify.yml` runs § Verify), issue forms (`corpus`, `open-decision`, `work-item`, and a disagreement between an implementation and a hand-derived verdict, `correctness-strategy.md` §6), the pull-request template, and Dependabot |
| **`docs/spec/`** | **Normative semantics** |
| `docs/spec/due2-workflows.md` | The three workflows and the reference data model, language-independent; laws L1–L10; the trace as explanation (§3.7) |
| `docs/spec/due2-profiles.md` | Profiles and the operand registry: how ODRL extensions are declared and evaluated, and DPROD Contracts compatibility |
| `docs/spec/odrl-compound-to-atomic-normalization.md` | Normalisation stage 1 |
| `docs/spec/due2-diagnostics.md` | The diagnostic registry: every code W1 rejects or warns with, its stage, and its defining section |
| **`docs/design/`** | **What due2 is, why, and the alternatives weighed** |
| `docs/design/due2-architecture.md` | What due2 is and why; reading order and glossary (§0) |
| `docs/design/implementation-alternatives.md` | The 2026-10-10 W1 alternatives review: Python+Dafny, Lean, Clingo, OCaml+Why3 — what each buys, why the documented path stands, what triggers revisiting |
| `docs/design/implementation-alternatives-ii.md` | The 2026-10-16 host comparison: the standing Python path vs an Elixir/BEAM host with a rented Rust door — decision rule and flip triggers |
| `docs/design/references.md` | The annotated bibliography: what was read, why, what was learned, and where it is used |
| `docs/design/mds-vendor-contracts.md` | Turning MDS vendor contracts into internal policies: approach and decisions (parked, issue #24) |
| **`docs/correctness/`** | **How we know it is right** |
| `docs/correctness/correctness-strategy.md` | Which check guards which risk, what each oracle is independent of, and what must exist before each component is coded |
| `docs/correctness/formalisation-review.md` | Review input, not adopted (2026-10-17): which obligations are provable, which theorems (monotonicity, the completion key, frontier relevance), which vehicles, in what order; deficits found in clingo-i |
| `docs/correctness/ways-of-working.md` | Engineering discipline: types, contracts, testing layers, tiering, the verification track |
| `docs/decisions/` | Decision records: 0001 RL2 as donor · 0002 W1 in Python with a Dafny oracle · 0003 duty guards stay on the duty · 0004 `frontier_complete` by bounded enumeration · 0005 set-based operators read after Salas–Pareti · 0006 W2/W3 backend bakeoff · 0007 collections are JCS JSON · 0008 the ledger: one case per request · 0009 the semantics live in a clingo program (the L9 oracle and generator) · 0010 the trace is the explanation · 0011 an `Indeterminate` is explained by its pivotal literals and its range · 0012 the same read is one completion variable · 0013 repeated right-operand values on a set-based operator are the same set as a list · 0014 an operand's type belongs to the layer that declares it · 0015 an operand may compare concepts under a SKOS hierarchy |
| `profiles/` | Shipped profile and binding modules, including vendored DPROD Contracts terms and example policies (`profiles/vendor/dprod/examples/`) |
| `conformance/` | The conformance corpus — RL2 use cases, DPROD examples, translations of other evaluators' suites (`force-`, `oval-`, `w3c-fs-`), and due2-native cases (`due2-`) — with scenarios and hand-derived expected verdicts; coverage gaps in its `README.md` |
| `conformance/odrl22-shape.ttl` | due2's SHACL encoding of the ODRL Information Model 2.2 — validates authored policies (compact and compound forms included), every constraint cited to its IM section |
| `conformance/odrl22-conformance.md` | The ODRL 2.2 conformance protocol, results, and the community-shape findings |
| `conformance/external/` | Other evaluators' test suites, vendored unmodified (FORCE, OVAL, W3C ODRL CG examples), with provenance, triage, findings, and upstream defects in its `README.md` |
| `tools/check_corpus.py` | Checks the corpus and any ODRL policy file against the admitted profile, without an evaluator |
| `tools/check_odrl22.py` | Validates policies against ODRL 2.2 itself: `odrl22-shape.ttl` plus the vendored official vocabulary (`profiles/vendor/w3c/ODRL22.ttl`), via pyshacl |
| `tools/import_force.py` | One-shot translation of the FORCE suite into `force-*` corpus cases, with an independent due2 derivation |
| `spikes/` | Candidate implementations, one directory each, run against the corpus by one shared suite; the contract, protocol, scorecard, and journal in its `README.md` |
| `tests/`, `tools/harness/` | The shared suite and its harness: corpus vectors, the comparator, the line protocol, scorecards (`pytest --backend=<spike>`) |
| `tools/spike_journal.py` | A spike's journal (effort, attempts, rewrites, bugs, checker diagnostics) and the cross-spike comparison table |
| `tools/check_completion.py` | Randomised check of the workflows §6.4 completion algorithm against brute force: canonical literals (v0.6), the `max_mixed` fallback, guarded duties (`decisions/0003`), deadlines with `violations = deny`, and `frontier_complete` by bounded enumeration (`decisions/0004`) |

Documents cite each other by file name (`due2-workflows.md` §5) and decision records as `decisions/NNNN`; names are unique under `docs/`.

## Verify

Managed with `uv` and Python 3.14+ (`.python-version`, `pyproject.toml`, which also configures the linters). All must pass before a commit; CI (`.github/workflows/verify.yml`) runs them on every push and pull request (`ways-of-working.md` §14.3).

```bash
uv run python tools/check_corpus.py conformance/cases                      # admissibility + case format
uv run python tools/check_corpus.py profiles/vendor/dprod/examples/*.ttl   # vendored DPROD policies
uv run python tools/check_odrl22.py --all                                  # ODRL 2.2 validity (SHACL)
uv run python tools/check_completion.py                                    # workflows §6.4 completion vs brute force
uv run pytest                                                              # the spike harness's own tests (spikes/README.md)
uv run basedpyright                                                        # strict typing (ways-of-working.md §4)
uv run ruff check . && uv run ruff format --check .                        # Python lint and format (§11)
uv run rumdl check .                                                       # Markdown lint (§11)
(cd spikes/clingo-i && uv run pytest && uv run basedpyright \
  && uv run ruff check . && uv run ruff format --check . \
  && uv run --group docs mkdocs build --strict)                            # spike clingo-i's own tests, checks, and generated reference
uv run pytest --backend=clingo-i                                           # the corpus through clingo-i (#9)
```

## Status

Specification and corpus only — no evaluator yet; every expected verdict is hand-derived. Open items are GitHub issues (labels `open-decision`, `corpus`, `verification`, `work-item`, `parked`), each pointing at the section that holds its source of truth. Next: the semantics program (issue #9, `decisions/0009`) — a generic clingo program over flattened ODRL, the L9 oracle and the test generator, run first over the corpus's authored policies (the correctness strategy is adopted; the enumeration bounds remain open, #42). Its spike, `spikes/clingo-i/`, grows by increments (#45, #46, #59, #47–#50): the walking skeleton (#45), the complete driver (#46), the explanation (#59: `verdict_basis`, `eliminated`, and an `Indeterminate`'s pivotal `unknown` atoms and `verdict_range`, `decisions/0011`), and constraints (#47: the authored trees under strong Kleene logic, bindings, reads, refinements, and typed `partOf`), and the layered operand bindings of `decisions/0014` (#68) are done. It passes 174 of the corpus's 409 scenarios and declines the rest, naming the feature — mostly duties (#49); then a `u` constraint on an atom that is itself `u`, which needs a constraint completion variable (#48, next). Then the W2/W3 bakeoff on relation-level vectors — Clingo and Elixir first, Python deferred (`decisions/0006`) — then W1 with the Dafny `Den` oracle (#8).
