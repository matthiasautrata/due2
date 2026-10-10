# 0002 — W1 stays Python; verification enters as a Dafny oracle; Clingo is out of the evaluator pipeline

**Status:** Decided, 2026-10-10
**Context documents:** `implementation-alternatives.md` (the full review this records) · `ways-of-working.md` §9–§10 · `due2-architecture.md` §9–§10, §11 · `odrl-compound-to-atomic-normalization.md` §8.1 · `Turning MDS Vendor Contracts into Internal Policies Approach and Decisions.md`

## Question

W1 is the pipeline's highest-risk step: every semantically interesting rewrite happens there, and a mis-normalised policy still evaluates cleanly — it simply means something else. Which implementation and verification technology should build it? Candidates examined: the documented path (Python + Dafny), Lean, Clingo/ASP as a unified executable semantics, and OCaml + Why3, with Kotlin, Flix, and Soufflé considered and set aside.

## Decision

1. **All three workflows stay Python.** rdflib is confined to parsing at the input boundary; serialisation, digests, and canonical bytes remain first-party pure functions (`ways-of-working.md` §2.4). No second implementation language enters the runtime.
2. **Dafny enters as oracle only** (`ways-of-working.md` §9.1, mode 1), scoped to the `Den` oracle (`odrl-compound-to-atomic-normalization.md` §8.1) and the stage-1 expansion functions. Extracted Python lives in the test tree and is never deployed.
3. **OCaml + Why3 is the designated upgrade**, adopted if Dafny's automation stalls on the stage-1 obligations — the brittleness signal Cedar itself hit and acted on.
4. **Lean is the recorded fallback** for the preservation metatheorem, not a current candidate. It is also the flagship option if a method showcase is ever wanted: a kernel-checked `Den(P0) ≅ Den(N(P0))` is the Cedar playbook applied to due2.
5. **Clingo/ASP is excluded from the evaluator pipeline.** Its one native fit is pre-W1: the MDS mapper's ambiguity stage, where cautious/brave reasoning over reading choices is exactly the semantics that document specifies. That use belongs to the MDS project if and when it proceeds. Any future clingo backend for W2/W3 is admitted only as a backend under the conformance suite (`due2-architecture.md` §10), which means passing the explicit `Indeterminate` vectors.
6. **`xone` expansion is decided eager** (architecture §11 #1, by default): disjuncts become atoms, the exact-count limit check fails pathological policies before materialising (`odrl-compound-to-atomic-normalization.md` §6.1 phase 6), and no set-valued match-key machinery is built until a real policy demands it.
7. **The L9 interpreter is named** (`ways-of-working.md` §13 #12): the Dafny-extracted `Den` oracle for stage 1, plus a Python reference evaluator for stage 2 and W2/W3, until a verified backend passes the corpus.
8. Kotlin, Flix, Soufflé, and Rust are recorded as set aside, with reasons, in `implementation-alternatives.md` §7.

## Why

- **W1's complexity and its risk are different sub-problems.** The algorithmic content is the Cartesian and DNF expansion; the risk is the preservation obligation — the property that makes errors non-silent. Tools rank by which of the two they address, and only the verification routes touch the second (`implementation-alternatives.md` §1).
- **Assurance class, not language, is the first axis** (§2): SMT-backed deductive verification (Dafny, Why3) against kernel-checked proof (Lean). The second axis is semantic fit: where a component's semantics carries a truth-value gap, an executable encoding is a backend, not a spec (§8).
- **Cedar's published experience settles the sequencing within the verification class**: SMT automation served program-level properties well and went brittle exactly on metatheory, which pushed Cedar to Lean (§4). due2's first artifact — the `Den` oracle — is program-level, so Dafny first; the preservation theorem is metatheory-shaped, so Lean is the named fallback.
- **The clingo audit is the empirical answer to "one engine everywhere"** (§5): the showcase encoding, checked against `due2-workflows.md` §5–§6, collapsed `U` and `F` through negation-as-failure, dropped the `violated` status, and had no completion layer — precisely the loss architecture §10 predicts for a port. Where ASP is sound — finite reading choices with no gap — it stays, in the MDS mapper.
- **`xone` is a theoretical weak spot and a practical non-issue** in the policies we actually encounter; the limit check already bounds it, so the decision is to keep expansion eager and revisit only on evidence.

## Consequences

- The verification track is unblocked: Dafny is installable in this environment (`brew install dafny`, Apple-Silicon bottle), resolving the standing blocker in `ways-of-working.md` §9.
- The first spike artifact is the `Den` model itself, in whatever vehicle — mechanising it pays back by finding underspecification in §6 even if no tool is ever adopted.
- Architecture §11 #1 and #6 and ways-of-working §13 #9 and #12 move from open to decided; the registers now say so.
- The MDS ambiguity stage has a named implementation candidate for its stage-0 tool, parked with that project.

## Revisit when

- Dafny's automation stalls on the stage-1 obligations (timeouts, solver-version sensitivity) → adopt OCaml + Why3, same oracle scope.
- Both SMT routes stall on the preservation metatheorem → Lean, per Cedar's own trajectory.
- A method showcase is commissioned → Lean, targeting `Den(P0) ≅ Den(N(P0))` over an abstract term model.
- The MDS project starts → clingo spike for the readings stage (cautious/brave), as a separate workstream.
- The first pathological `xone` policy appears in a real corpus → set-valued match keys (architecture §11 #1 reopens).
