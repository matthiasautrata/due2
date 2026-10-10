# due2

Specifications for due2, an ODRL policy evaluation runtime.

**Source of truth.** All due2 artefacts live in this git repository, `~/src/due2`. Copies elsewhere — the claude.ai project, chat attachments — are mirrors and may be stale. Change files here, commit, then refresh any mirror that needs it.

| Document | Covers |
|---|---|
| `due2-architecture.md` | What due2 is and why |
| `due2-workflows.md` | The three workflows and the reference data model, language-independent |
| `due2-profiles.md` | Profiles and the operand registry: how ODRL extensions are declared and evaluated, and DPROD Contracts compatibility |
| `odrl-compound-to-atomic-normalization.md` | Normalisation stage 1, normative |
| `ways-of-working.md` | Engineering discipline |
| `implementation-alternatives.md` | The 2026-10-10 W1 alternatives review: Python+Dafny, Lean, Clingo, OCaml+Why3 — what each buys, why the documented path stands, what triggers revisiting |
| `decisions/` | Decision records |
| `profiles/` | Shipped profile and binding modules, including vendored DPROD Contracts terms and example policies (`profiles/vendor/dprod/examples/`) |
| `conformance/` | The conformance corpus: RL2 use cases and DPROD examples in ODRL, with scenarios and expected verdicts |
| `conformance/odrl22-shape.ttl` | due2's SHACL encoding of the ODRL Information Model 2.2 — validates authored policies (compact and compound forms included), every constraint cited to its IM section |
| `conformance/odrl22-conformance.md` | The ODRL 2.2 conformance protocol, results, and the community-shape findings |
| `tools/check_corpus.py` | Checks the corpus and any ODRL policy file against the admitted profile, without an evaluator |
| `tools/check_odrl22.py` | Validates policies against ODRL 2.2 itself: `odrl22-shape.ttl` plus the vendored official vocabulary (`profiles/vendor/w3c/ODRL22.ttl`), via pyshacl |
| `Turning MDS Vendor Contracts into Internal Policies Approach and Decisions.md` | Turning MDS vendor contracts into internal policies: approach and decisions |
