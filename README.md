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
| `decisions/` | Decision records |
| `profiles/` | Shipped profile and binding modules, including vendored DPROD Contracts terms and example policies (`profiles/vendor/dprod/examples/`) |
| `conformance/` | The conformance corpus: RL2 use cases and DPROD examples in ODRL, with scenarios and expected verdicts |
| `tools/check_corpus.py` | Checks the corpus and any ODRL policy file against the admitted profile, without an evaluator |
| `Turning MDS Vendor Contracts into Internal Policies Approach and Decisions.md` | Turning MDS vendor contracts into internal policies: approach and decisions |
