# due2 — Implementation Alternatives: W1 and the Verification Track

> **Archived.** This review was current on 2026-10-10. It is kept as history (`docs/archive/README.md`); its outcome is `decisions/0002`, as later amended and superseded in part (`docs/decisions/README.md`).

**Status:** Record of the 2026-10-10 alternatives review; normative decisions live in `decisions/0002-w1-implementation-and-verification.md`
**Companions:** `due2-architecture.md` (§2, §9–§10) · `due2-workflows.md` (§4, §8) · `odrl-compound-to-atomic-normalization.md` (§5, §8.1) · `ways-of-working.md` (§5.1, §9–§10) · `implementation-alternatives-ii.md` (the sequel: the host question, 2026-10-16)

This document records which technologies were considered for implementing and verifying W1 — the pipeline's highest-risk step — what each would have bought, why the documented path stands, and what would trigger revisiting each alternative. It exists so the choice is visible as considered, not defaulted. Four candidates were examined in depth: the documented path (Python + Dafny), Lean, Clingo/ASP, and OCaml + Why3. Three more (Kotlin, Flix, Soufflé) were considered and set aside.

---

## 1. The question, corrected

"Which language for W1" conflates four sub-problems with different shapes:

| | Sub-problem | Character |
|---|---|---|
| **A** | Parse and lift the authored graph into typed trees | Bounded plumbing; the input profile's invariants (forest shape, acyclic rule references, no named graphs) make it mechanical |
| **B** | Expansion: Cartesian product over action, relation, and party axes; constraint DNF including `xone` | The only genuine algorithmic content; `xone` over *n* constraints is worst-case exponential |
| **C** | Identity, lineage, canonical bytes: content-hash UUIDs, skolemisation, PROV-O, canonical N-Quads | Deterministic, unforgiving, purely functional |
| **D** | The preservation obligation: `Den(P0) ≅ Den(N(P0))` (normalisation spec §8.1) | The property that makes normalisation errors non-silent |

Two corrections follow. First, **complexity and risk are different**: B is where the work is, D is where the danger is — a mis-normalised policy evaluates cleanly and means something else (`ways-of-working.md` §9: verification effort follows the case analysis). Any proposal must say which of A–D it addresses. Second, **language performance is irrelevant to W1**: it is offline, runs once per policy version, and has an effectively unbounded budget (`ways-of-working.md` §10.1). Speed arguments select nothing here.

---

## 2. The two axes that decide

**Assurance class.** Not all "verification" is the same claim:

| Class | Tools | "Verified" means | Failure modes |
|---|---|---|---|
| SMT-backed deductive verification | Dafny, Why3 | a solver discharged each verification condition | timeout, `unknown`, solver-version brittleness, weakening the spec until it proves |
| Kernel-checked proof | Lean (and Rocq, Isabelle) | a proof term a small trusted kernel re-checks | none in the guarantee; all the cost is human |

**Semantic fit.** Does the component's semantics carry a truth-value gap? Where every question is a finite choice, an executable encoding can *be* the spec. Where unknowns must survive to the verdict — `U` findings, `Indeterminate`, `frontier_complete` — an encoding is an *implementation of* the semantics, checked against it, never a substitute for it. This axis decides where a logic engine may hold normative authority (§8).

---

## 3. The documented path — Python + rdflib, plus a Dafny oracle

**What stands.** All three workflows in Python; one language, one term model, one conformance suite; the corpus and `check_corpus.py` run unchanged. The standard objection — rdflib is slow and heavy — is a non-argument for an offline stage with an unbounded budget.

**Two scope corrections the review produced:**

- rdflib's role is *narrower* than "intake and conversion". The lift is immediate and lossless (`ways-of-working.md` §2.4), and serialisation, digests, and canonical bytes are first-party pure functions — the identity path deliberately does not use library canonicalisation (normalisation spec §5.2 removed RDFC-1.0 from it). rdflib parses; it must not emit.
- "Results → persistence" is the impure shell, outside W1's pure core, per the functional-core rule.

**The deficit, and its fix.** Python cannot express D. Property tests catch the bugs you think of; they do not prove the absence of the class (`ways-of-working.md` §1). The fix already in the adoption sequence (step 11) is Dafny in **oracle mode** (`ways-of-working.md` §9, mode 1): verify the `Den` oracle and the expansion functions, extract to Python, keep the extraction in the test tree as differential ground truth. The long-standing installation blocker is resolved: Dafny ships Homebrew bottles for Apple Silicon (4.11.0, .NET 8 + Z3), so the mode-1 entry point is unblocked.

**Why Dafny and not something stronger, first.** The `Den` oracle is a page of definitions with list and bounds obligations — program-level, where SMT automation is at its best. Starting with a proof assistant there pays human cost before knowing whether automation suffices.

---

## 4. Lean

**The precedent.** AWS Cedar is the industry's flagship verified policy engine, and cedar-spec formalises it in Lean 4: authorizer order-indifference, default-deny, sound policy slicing, sound typechecking, and a sound-and-complete symbolic compiler to SMT. Cedar's published trajectory is the load-bearing fact for us: they began with Dafny, found SMT automation *brittle precisely on metatheoretic properties* (timeouts on minor program or solver changes), and moved the metatheory to Lean — reporting the Lean specification outperforming the Dafny one on verification time and differential-testing throughput (POPL SRC 2024, "A Lean Formalization of Cedar").

**The match.** due2's headline obligation — `Den(P0) ≅ Den(N(P0))`, a bijection between two derived finite structures, universally quantified over inputs — is exactly the metatheory shape Cedar abandoned SMT automation for. A Lean development would model the lifted tree and `Den` over abstract terms, implement the expansion as total functions, prove the preservation theorem, and compile natively. Cedar's playbook, applied to our risky step. If a *method showcase* is ever commissioned, this is it: a kernel-checked preservation proof for the transformation the architecture calls the risky half.

**Why it is the fallback, not the first move.**

- Cost: proof engineering is a specialism; effort is 3–10× on the verified portion even in the friendlier tools, and higher in Lean, front-loaded.
- No deployment path: nothing in a bank runtime executes Lean; the artifact is demonstrative.
- **Proofs decay:** a Lean development is a specification artifact that must be pinned to spec versions and regenerated when they change — the same vendored-artifact discipline as any generated output (`ways-of-working.md` §11). Left unpinned, it proves the previous spec.
- The verified core covers D over abstract terms; A and C — parsing, hashing, canonical bytes — stay unverified plumbing around it. "A verified normalizer binary" overstates; the theorem covers `Den`, not the artifact boundary.

**Trigger.** Adopt when both SMT routes stall on the preservation metatheorem — Cedar's own signal, reproduced here.

---

## 5. Clingo / ASP

The most tempting reframing, examined twice and settled: **ASP is native where semantics is finite choice, and wrong where the truth-value gap is load-bearing.**

**Where it is sound.**

- *The MDS ambiguity stage* (pre-W1). The MDS document specifies: "treated as permitted only if every reading permits it, and as forbidden if any reading forbids it." That is literally cautious and brave entailment over a finite choice space; clingo's `--cautious` (intersection of stable models) and `--brave` (union) compute it natively from choice rules over reading dimensions. This is the strongest clingo use case found, it upgrades the MDS doc's own stage 2/3, and it belongs to the MDS project.
- *W1 integrity constraints.* Closed-world reasoning is legitimate there — the input is a closed graph — and constraints like `:- reaches(X, X)` (cycle = UNSAT = reject) and consequence-depth bans are exact and elegant. The interiorisation default ("fill only what a rule leaves unstated") is correct stratified negation.
- *The frontier encoding.* Non-domination by strict-subset comparison (`A ⊆ B ∧ B ⊈ A`) is exactly `due2-workflows.md` §6.3 and is expressible in a few rules. (An earlier variant using weak constraints was wrong: sum-minimising is a declared *total* order — "fewest duties" — which `due2-workflows.md` §6.3 explicitly refuses to impose without `config.preference`. The frontier's honest output is all incomparable alternatives.)

**Where it fails, as evidenced by the showcase encodings themselves, checked against §5–§6:**

- `outstanding(D) :- duty_instance(D), not fulfilled(D)` collapses `F` and `U` through negation-as-failure. The spec's instance status has four values; the `violated` status (deadline comparison) is absent entirely. The `U` duty must surface as `unknown`, and unknown findings are *completed*, never defaulted (`due2-workflows.md` §6.4).
- No completion layer: a `Forbid` with finding `U` must eliminate nothing and make the verdict `Indeterminate`. The encodings return definite verdicts. `frontier_complete` is unexpressed.
- The load-bearing parts of W1 — skolemisation with parent-scoped digests, `frame()`/SHA-256 identity, canonical byte order, the lineage bijection — are functional (hashes, folds, orderings), not relational. Under any logic-engine architecture they live in host-language foreign functions; the "unified logic core" keeps the easy half and concedes the hard half.
- Architecture §10 predicted exactly this: "explicit `Indeterminate` cases … asserted per backend. **This is the property most likely to be silently lost in a port.**" The audit found the predicted loss on the first attempt.

**The observation that ends the debate.** The pitch says ODRL is "intrinsically non-monotonic — a permission active unless overridden." But due2's override is explicit — read from the policy's `conflict` term — and that explicitness is what makes the verdict a *provably monotone* map from completions (`due2-workflows.md` §6.4), which is why `Indeterminate` costs two evaluations instead of 2ⁿ. due2 proves monotonicity where ASP offers non-monotonicity; default negation is not this system's natural semantics, and its closed-world default is the one behaviour `ways-of-working.md` §5.1 exists to override everywhere.

**Verdict.** Excluded from the evaluator pipeline. In as the MDS stage-0 tool. Any future clingo backend for W2/W3 enters as a backend under the conformance suite — which means a three-valued encoding (paired truth atoms plus a completion layer) that must pass the `Indeterminate` vectors.

---

## 6. OCaml + Why3

Structurally the same animal as the Dafny route — verify in WhyML, discharge verification conditions with SMT solvers, extract — with three differences:

- **Multi-prover, not Z3-singular.** Why3 dispatches to Alt-Ergo, CVC5, Z3, and others (Coq/Isabelle/PVS for residue). This addresses directly the single-solver brittleness Cedar documented. The platform's industrial lineage is real: it backs Frama-C's WP plugin and SPARK's GNATprove, and Alt-Ergo serves Atelier-B and Airbus's CAVEAT. (One correction for the record: CompCert is Coq-extracted, not Why3 — a review input misattributed it.)
- **Native extraction to OCaml** (`why3 extract -D ocaml64`), making the whole route one coherent ML-family language: spec, proof, extraction, execution. Of all candidates, this is the only one whose artifact can graduate from test-tree oracle to a deployable W1 implementation without changing language.
- **WhyML's own learning cost**, and the same assurance class as Dafny: SMT-backed, no kernel. The metatheorem will fight automation here too.

**Role.** Designated upgrade: adopted if Dafny's automation stalls on the stage-1 obligations — the Cedar brittleness signal — at which point the same oracle scope moves to Why3 and the extraction becomes OCaml rather than Python.

---

## 7. Considered and set aside

- **Kotlin.** Real exhaustiveness, immutability, nominal typing — but not a verification language: the same defect classes as disciplined Python, at the price of a second language, a second RDF stack, and a duplicated term model. It answers the W2/W3 hot-path question (`ways-of-working.md` §10.3), not the W1 risk question.
- **Flix.** Genuine fit — first-class Datalog constraints for closure and fixpoint work, a Hindley-Milner type-and-effect system that enforces purity, no paradigm sprawl — but it buys elegance on B and C, nothing on D, and it is a niche research language as an environment bet.
- **Soufflé Datalog.** Real strengths: compiles to C++, native provenance trees. But its functor-synthesised keys are content-addressed, the opposite of due2's nominal identity discipline (`due2-workflows.md` §2: two tuples with equal content and different ids never merge), and its provenance is rule-derivation trees, not the PROV-O sidecar with authored/effective/generated mappings. Credible for closure computation; not the free corpus-plus-lineage lunch claimed.
- **Rust via PyO3.** Already recorded as a hot-stage option in `ways-of-working.md` §10.3; irrelevant to W1's unbounded-budget offline stage, and no Rust toolchain is approved in this environment.

---

## 8. Where specification authority lives

The review's architectural conclusion, worth recording independently of any tool:

> **Authority follows the gap.** Where a component's semantics has no truth-value gap — finite choices, every case decided — the executable logic program can *be* the spec: the MDS readings stage qualifies. Where the gap is load-bearing — W2's `U` findings, W3's `Indeterminate` and `frontier_complete` — the prose, the laws, and the corpus are the spec, and every engine, however elegant, is a backend admitted only by passing the suite (`ways-of-working.md` §10.2).

The underlying principle: *executability confers no authority; proved or tested correspondence does.* Cedar's model is authoritative not because it runs but because theorems were proved about it and differential testing connects it to production. "The code is the spec" always smuggles a second-order obligation — the correspondence between what was meant and what the code says — and that obligation needs either a proof or a corpus. due2 has the corpus; that is what makes it the constitution.

---

## 9. Sequencing and further steps

1. **Mechanise `Den` first**, in whatever vehicle. The §8.1 definition was written small and independent of §6 precisely to be an oracle; formalising it finds every ambiguity prose has deferred. This pays back even if no verification tool is ever adopted.
2. **Dafny oracle, scoped to `Den` + expansion functions**, extraction in the test tree (`ways-of-working.md` §9, mode 1). Weekend-scale probe; answers the proof-cost open items with numbers.
3. **Why3 on the Cedar signal** — Dafny automation stalling — same scope, OCaml extraction.
4. **Lean on the metatheory signal** — both SMT routes stalling on preservation — or on commission of a method showcase.
5. **Clingo for MDS stage 0** when that project starts, as its own workstream.
6. **`xone` stays eager**, bounded by the existing exact-count limit check; set-valued match keys are built only when a real policy demands them.

**Addendum (2026-10-10, coherence review).** Two clarifications recorded in the `decisions/0002` amendment: the L9 oracle is a *direct interpreter over the lifted (authored) form* — a W2/W3 evaluator over the corpus checks L1–L8 but cannot play `I`, which reads authored policies as written — and L9 is restated as a refinement: equality when every finding is definite; under unknowns, hoisting splits one fact into correlated findings completed independently, so the pipeline may say `Indeterminate` where the direct interpreter decides, and exact completion over the shared fact (workflows §9 #6) is what would restore equality. The Dafny scope itself is unchanged. *(Superseded 2026-10-11: workflows v0.6 restored equality through canonical literals, and `decisions/0003` withdrew hoisting itself.)*

## 10. What stays open

- The conformance suite's backend parameterisation remains the standing obligation (`ways-of-working.md` §10.2): a second backend must port a parser, not a semantics.
- The DPROD `Indeterminate`-on-`invalid` alternative and the exact shared-fact completion remain open as before (`due2-workflows.md` §9) — unaffected by this review.
- Whether the MDS project proceeds at all decides its clingo candidate's fate, not this review.
- The host question — the standing Python path vs an Elixir/BEAM alternative under changed assumptions (human-primary authoring, multi-user deployment, no tooling limits) — is the sequel's: `implementation-alternatives-ii.md`. This review's scope was W1's vehicle.

---

## References

- cedar-spec, the Lean 4 formalization of Cedar: `github.com/cedar-policy/cedar-spec` (cedar-lean) — authorizer order-indifference, default-deny, slicing soundness, sound-and-complete symbolic compilation.
- *A Lean Formalization of Cedar*, POPL SRC 2024 — Cedar's Dafny→Lean migration; SMT brittleness on metatheory; Lean/Dafny performance comparison.
- Why3 1.8 documentation (`why3.org`) — WhyML, multi-prover dispatch, `extract -D ocaml64`; Frama-C WP and SPARK/GNATprove usage.
- Potassco User Guide (`potassco.org`) — stable-model semantics, `--cautious`/`--brave`, choice rules, weak constraints.
- Dafny installation (`dafny.org`, Homebrew `dafny` 4.11.0) — Apple-Silicon bottles, .NET 8, Z3.
- `mds-vendor-contracts.md` — the readings/cautious-translation semantics the MDS stage-0 clingo candidate implements.
