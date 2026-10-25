# due2

due2 is the specification of a runtime for evaluating ODRL 2.2 policies. ODRL is the W3C language for saying who may, must, or must not do what with an asset. Given a policy, an access request, and a frozen snapshot of the state of the world (SOTW), due2 is to answer with one of five verdicts: `Permit`, `Deny`, `Pending` (permitted once listed duties are done, with every alternative route), `NotApplicable`, or `Indeterminate`. Evaluation is three-valued (Kleene logic). A fact that is missing, invalid, or in conflict is unknown, never false, and the verdict is `Indeterminate` exactly when settling the unknowns could change it (`decisions/0011`). Every decision is to carry the reasons that produced it, so that it can be replayed (`decisions/0010`).

This repository holds the specification, a conformance corpus with hand-derived expected verdicts, the checkers that keep both consistent, and one spike that runs the corpus. There is no production evaluator yet. Start with `docs/design/due2-architecture.md` §0, which gives the reading order and a glossary.

This repository is the only copy of due2's artefacts: change them here and commit.

## Layout

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
| `docs/design/due2-platform.md` | The components around the evaluator, their interfaces, the use cases they serve, and the migration from a predecessor system; all open |
| `docs/design/references.md` | The annotated bibliography: what was read, why, what was learned, and where it is used |
| **`docs/correctness/`** | **How we know it is right** |
| `docs/correctness/correctness-strategy.md` | Which check guards which risk, what each oracle is independent of, and what must exist before each component is coded; the claims the formal model proves (§4.8) |
| `docs/correctness/ways-of-working.md` | Engineering discipline: types, contracts, testing layers, tiering, the verification track |
| `docs/decisions/` | Decision records: each settles one question the specification depends on; `docs/decisions/README.md` lists them with their standing |
| `docs/briefings/` | Dated snapshots of the project for readers new to it, not maintained; its `README.md` lists them |
| `docs/archive/` | Documents no longer current, kept as history, with an index in its `README.md`: the implementation-alternatives reviews, the formalisation review, and the documents' earlier **Changes** entries |
| `profiles/` | Shipped profile and binding modules, including vendored DPROD Contracts terms and example policies (`profiles/vendor/dprod/examples/`) |
| `conformance/` | The conformance corpus — RL2 use cases, DPROD examples, translations of other evaluators' suites (`force-`, `oval-`, `w3c-fs-`), and due2-native cases (`due2-`) — with scenarios and hand-derived expected verdicts; coverage gaps in its `README.md` |
| `conformance/odrl22-shape.ttl` | due2's SHACL encoding of the ODRL Information Model 2.2 — validates authored policies (compact and compound forms included), every constraint cited to its IM section |
| `conformance/odrl22-conformance.md` | The ODRL 2.2 conformance protocol, results, and the community-shape findings |
| `conformance/external/` | Other evaluators' test suites, vendored unmodified (FORCE, OVAL, W3C ODRL CG examples), with provenance, triage, findings, and upstream defects in its `README.md` |
| `schema/` | The evaluator port in JSON Schema 2020-12, generated from `due2-workflows.md` §3 by `tools/gen_schema.py`; its `README.md` maps the spec's types to JSON Schema |
| `tools/check_corpus.py` | Checks the corpus and any ODRL policy file against the admitted profile, without an evaluator |
| `tools/check_odrl22.py` | Validates policies against ODRL 2.2 itself: `odrl22-shape.ttl` plus the vendored official vocabulary (`profiles/vendor/w3c/ODRL22.ttl`), via pyshacl |
| `tools/import_force.py` | One-shot translation of the FORCE suite into `force-*` corpus cases, with an independent due2 derivation |
| `formal/alloy/` | Alloy 6 models of the claims of `correctness-strategy.md` §4.8, run outside § Verify by `formal/alloy/run.sh`; scopes and run times in its `README.md` |
| `spikes/` | Candidate implementations, one directory each, run against the corpus by one shared suite; the contract, protocol, scorecard, and journal in its `README.md` |
| `tests/`, `tools/harness/` | The shared suite and its harness: corpus vectors, the comparator, the line protocol, scorecards (`pytest --backend=<spike>`) |
| `tools/spike_journal.py` | A spike's journal (effort, attempts, rewrites, bugs, checker diagnostics) and the cross-spike comparison table |
| `tools/check_completion.py` | Randomised check of the workflows §6.4 completion algorithm against brute force: canonical literals (v0.6), the `max_mixed` fallback, guarded duties (`decisions/0003`), deadlines with `violations = deny`, and `frontier_complete` by bounded enumeration (`decisions/0004`) |

Documents cite each other by file name (`due2-workflows.md` §5) and decision records as `decisions/NNNN`. Every file name under `docs/` is unique except `README.md`, which is cited with its path (`docs/decisions/README.md`).

## Verify

Managed with `uv` and Python 3.14+ (`.python-version`, `pyproject.toml`, which also configures the linters). All must pass before a commit; CI (`.github/workflows/verify.yml`) runs them on every push and pull request (`ways-of-working.md` §14.3).

```bash
uv run python tools/check_corpus.py conformance/cases                      # admissibility + case format
uv run python tools/check_corpus.py profiles/vendor/dprod/examples/*.ttl   # vendored DPROD policies
uv run python tools/check_odrl22.py --all                                  # ODRL 2.2 validity (SHACL)
uv run python tools/check_completion.py                                    # due2-workflows.md §6.4: completion vs brute force
uv run pytest                                                              # the spike harness's tests (spikes/README.md); cited documents resolve
uv run basedpyright                                                        # strict typing (ways-of-working.md §4)
uv run ruff check . && uv run ruff format --check .                        # Python lint and format (ways-of-working.md §11)
uv run rumdl check .                                                       # Markdown lint (ways-of-working.md §11)
(cd spikes/clingo-i && uv run pytest && uv run basedpyright \
  && uv run ruff check . && uv run ruff format --check . \
  && uv run --group docs mkdocs build --strict)                            # spike clingo-i's own tests, checks, and generated reference
uv run pytest --backend=clingo-i                                           # the corpus through clingo-i (#9)
```

## Status

- **Specification and corpus.** The corpus has 165 cases. Every expected verdict is hand-derived. `tools/check_corpus.py` checks each case's format and that its policy stays within the admitted profile. The 51 negative cases are policies that W1 must reject, and they wait for W1.
- **The semantics program.** `spikes/clingo-i/` evaluates the corpus's authored policies with a generic clingo program (`decisions/0009`), which serves as the oracle for the evaluator to come. It passes 419 of the 457 scenarios it is given and declines the other 38, naming the feature: 37 depend on the occurrences of a recurring duty (`unsupported: recurrence`, #80, parked with #119), and one is past the `max_mixed` bound, for which the spike has no fallback. Its tests check it against a brute-force oracle on generated draws and on every input of nine bounded spaces, which together expose each of its twenty-three mutants (#44). The spaces also check two claims of `correctness-strategy.md` §4.8, monotonicity (M) and the basis waiver (W), with no counterexample (#85).
- **Formal models.** The Alloy 6 models of claims K, M, F, W and P (`formal/alloy/`) find no counterexample at their stated scopes, now that `decisions/0023` has closed the gap they found in the completion key. P was an open question until `decisions/0026` settled the listed frontier; clingo-i follows it with #103.
- **External review.** An outside reader reviewed `dc232b5` (`docs/briefings/due2-review-2026-10-24.md`). Its nine findings, #109 to #117, are settled, each by a decision record or a spec edit (#118). A follow-up review of `beb7c5f` (`docs/briefings/due2-review-2026-10-25.md`) confirms that disposition and reports seven new findings, #120 to #127, open under #128.
- **Next.** The follow-up review's findings, in the order of #128. Then the W2/W3 evaluator (its language is #104), gated by relation-level vectors and by clingo-i's relation-level face as oracle (#41, `decisions/0027`), then W1 in Python. The prover spike is parked (`decisions/0021`).

Open items are GitHub issues, labelled `open-decision`, `corpus`, `verification`, `work-item`, or `parked`, and also `bug` when they record a fault in what is already specified or built. Each names the section that holds its source of truth.
