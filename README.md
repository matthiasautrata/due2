# due2

Specifications for due2, an ODRL policy evaluation runtime.

**Source of truth.** All due2 artefacts live in this git repository (`github.com/matthiasautrata/due2`); clone it anywhere. No other copy is maintained — the claude.ai project holds only a pointer here. Change files here and commit.

| Document | Covers |
|---|---|
| `CLAUDE.md` | Working notes for Claude Code: the rules that are easy to break, where the semantics live, what's next |
| `due2-architecture.md` | What due2 is and why |
| `due2-workflows.md` | The three workflows and the reference data model, language-independent |
| `due2-profiles.md` | Profiles and the operand registry: how ODRL extensions are declared and evaluated, and DPROD Contracts compatibility |
| `odrl-compound-to-atomic-normalization.md` | Normalisation stage 1, normative |
| `ways-of-working.md` | Engineering discipline |
| `implementation-alternatives.md` | The 2026-10-10 W1 alternatives review: Python+Dafny, Lean, Clingo, OCaml+Why3 — what each buys, why the documented path stands, what triggers revisiting |
| `decisions/` | Decision records: 0001 RL2 as donor · 0002 W1 in Python with a Dafny oracle · 0003 duty guards stay on the duty |
| `profiles/` | Shipped profile and binding modules, including vendored DPROD Contracts terms and example policies (`profiles/vendor/dprod/examples/`) |
| `conformance/` | The conformance corpus — RL2 use cases, DPROD examples, translations of other evaluators' suites (`force-`, `oval-`, `w3c-fs-`), and due2-native cases (`due2-`) — with scenarios and hand-derived expected verdicts; coverage gaps in its `README.md` |
| `conformance/odrl22-shape.ttl` | due2's SHACL encoding of the ODRL Information Model 2.2 — validates authored policies (compact and compound forms included), every constraint cited to its IM section |
| `conformance/odrl22-conformance.md` | The ODRL 2.2 conformance protocol, results, and the community-shape findings |
| `tools/check_corpus.py` | Checks the corpus and any ODRL policy file against the admitted profile, without an evaluator |
| `tools/check_odrl22.py` | Validates policies against ODRL 2.2 itself: `odrl22-shape.ttl` plus the vendored official vocabulary (`profiles/vendor/w3c/ODRL22.ttl`), via pyshacl |
| `conformance/external/` | Other evaluators' test suites, vendored unmodified (FORCE, OVAL, W3C ODRL CG examples), with provenance, triage, findings, and upstream defects in its `README.md` |
| `tools/import_force.py` | One-shot translation of the FORCE suite into `force-*` corpus cases, with an independent due2 derivation |
| `tools/check_completion.py` | Randomised check of the workflows §6.4 completion algorithm against brute force: canonical literals (v0.6), the `max_mixed` fallback, and guarded duties (`decisions/0003`) |
| `Turning MDS Vendor Contracts into Internal Policies Approach and Decisions.md` | Turning MDS vendor contracts into internal policies: approach and decisions |

## Verify

Python 3.9+ with `rdflib` and `pyshacl` (verified with Python 3.9.6, rdflib 7.5.0, pyshacl 0.31.0). All four must pass before a commit.

```bash
python3 tools/check_corpus.py conformance/cases                      # admissibility + case format
python3 tools/check_corpus.py profiles/vendor/dprod/examples/*.ttl   # vendored DPROD policies
python3 tools/check_odrl22.py --all                                  # ODRL 2.2 validity (SHACL)
python3 tools/check_completion.py                                    # §6.4 completion vs brute force
```

## Status

Specification and corpus only — no evaluator yet; every expected verdict is hand-derived. Open items are GitHub issues (labels `open-decision`, `corpus`, `verification`, `work-item`, `parked`), each pointing at the section that holds its source of truth. Next: the L9 oracle, a Python direct interpreter over the authored form that runs the corpus (issue #9), then the Dafny `Den` oracle (#8).
