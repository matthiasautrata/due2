# 0021 — Formalisation follows Cedar: an executable model, proofs, and differential testing

**Status:** Decided, 2026-10-19 (the owner: Dafny out; Lean first, Isabelle optional)
**Context documents:** `correctness-strategy.md` §3, §4.8, §8 · `ways-of-working.md` §9 · `due2-workflows.md` §6.4, §8 · `decisions/0002` #2–#4 · `decisions/0009` · `docs/archive/formalisation-review.md` · issues #70, #8, #23

## Question

Which formal methods does due2 use, on which claims, in what order, and how is the prover chosen?

`decisions/0002` put Dafny on the `Den` oracle (`odrl-compound-to-atomic-normalization.md` §8.1), with OCaml and Why3 as the upgrade and Lean as the fallback. Part of its reasoning was that Cedar moved from Dafny to Lean when SMT automation went brittle. Neither Cedar's paper nor AWS's account of it says so (`references.md` §7). A review of 2026-10-17, now archived as `formalisation-review.md`, named three theorems and ranked eight tools, but nothing adopted it. Since then the clingo-i spike has come to pass 400 of the corpus's 438 scenarios (its scorecard at commit 8d06c67, 2026-10-19), so the semantics to formalise exists.

## Decision

1. **The pattern is Cedar's verification-guided development.** due2 gets a small, readable model of its semantics, written in a prover. Proofs establish the model's properties. Differential testing compares the model with every implementation: clingo-i, and W1, W2, and W3 as each is built. The model is executable, so the object the proofs are about is the object the tests run. No production code is extracted from it.
2. **The claims are stated before any tool is chosen.** `correctness-strategy.md` §4.8 states four claims, each with its source sentence in the spec and the evidence for it: monotonicity (M), the completion key (K), frontier relevance (F), and the empty-basis waiver (W). It also states one open question, the listed frontier under unknowns (P), which is settled by a spec edit or a decision record rather than proved.
3. **Counterexamples come before proofs.** Each claim gets a small Alloy 6 model of its own, and a bounded-exhaustive search over clingo-i's program (#42, #44, #77; the amendment below narrows the search to M and W). A claim is taken to a prover only after the search has run at stated bounds without a counterexample. What a search finds is triaged by `correctness-strategy.md` §6.
4. **The prover is chosen by a spike, Lean 4 first.** The spike models M over the finding and resolution layers, without duties. An Isabelle/HOL spike on the same target is optional. It runs if Lean's result is poor, or later as a comparison. Each spike is scored on four things:
   - how readable the model is to a reader who knows `due2-workflows.md` §6 but not the prover;
   - the size of the proof and the time to check it;
   - whether the model runs under the spike harness (`spikes/README.md`), so that it can join the differential;
   - churn: the cost of re-checking after a representative spec change, such as adding a conflict strategy.

   The result is recorded as an amendment to this record.
5. **Dafny is out.** This supersedes `decisions/0002` #2–#4. The `Den` oracle becomes part of the chosen prover's model (issue #8). The OCaml and Why3 upgrade path is withdrawn, and so is Lean's place as a fallback. The Python `Den` oracle stays the first oracle for W1 stage 1 (`correctness-strategy.md` §4.2).
6. **Adequacy is not proved.** Whether due2 reads ODRL 2.2 and DPROD as intended cannot be a theorem. It is answered by the external suites' own answers, by a comparison against DPROD's formal semantics after #63's review (its `formal-semantics.md` is to be vendored first, with the re-sync of issue #35, so that the comparison can be repeated), and by Alloy's small-scope search over L1–L10 (`due2-workflows.md` §8).
7. **The production language is not decided here.** That remains the bakeoff's question (`decisions/0006`).

## Why

- **Cedar's results favour the combination over either half.** While writing the proofs, Cedar's team found 4 bugs. Differential random testing and property-based testing found 21 more (Disselkoen et al. 2024, §1). Proofs make the claims precise, and testing finds most defects. Extraction would close the gap between model and code by construction, and differential testing closes most of it more cheaply, without tying production to the prover's code generator.
- **The model has to run.** A model that only states theorems cannot test clingo-i or W1. Lean compiles its models: Cedar's Lean authorizer runs in about 6 µs per request, and all of Cedar's proofs check in about 3 minutes (Disselkoen et al. 2024, §3). Isabelle reaches the same point through code generation.
- **Counterexamples first is cheaper and more honest.** One claim has a known gap: the completion key merges only identical and complementary parts, so it admits a completion in which `x ≤ 5` and `x > 7` are both `F`, which no value of `x` gives (`due2-workflows.md` §6.4, issue #25). W has only an informal argument behind it (`spikes/clingo-i/DESIGN.md`), and P is a question still open (`decisions/0019`). A small-scope search finds such holes in minutes, and a failed proof attempt finds them slowly.
- **Lean first, at the owner's choice.** Lean has Cedar's published precedent, and it is both a prover and a programming language. Isabelle may need less proof effort for this kind of finite combinatorics, and the spike scoring can show whether it does.
- **Dafny's place was a sequence that no longer holds.** `decisions/0002` chose Dafny because `Den` is program-shaped, with Lean held back for the metatheory. M, K, and F are metatheory, and one prover for both keeps one toolchain and one model.

## Alternatives

- **Dafny for `Den`, a second prover for the theorems.** Two toolchains and two models of overlapping semantics, for no gain the spikes cannot measure.
- **Extraction from Rocq or Isabelle** (review vehicle 3). The L9 oracle would be generated from the proved semantics. It is rejected because the differential reaches nearly the same assurance, and `decisions/0009` already makes a hand-written clingo program the L9 oracle.
- **Direct SMT on bounded instances** (Z3 or cvc5). Cheap, but it has no kernel and proves only what fits the bound. The bounded-exhaustive search already covers that ground.
- **Isabelle first.** A reasonable choice that the owner did not make. It stays open through the optional spike.
- **Kleene-annotated Datalog** (review vehicle 8). State the finding layer as Datalog annotated with the three-valued Kleene lattice, a K-relation in the style of Green, Karvounarakis and Tannen (`references.md` §2), and take stratification, determinism, and monotonicity from standard results. It is not a rival to the prover but a way to write the model: the Lean spike may adopt it for M if it shortens the proof.

## Consequences

- `correctness-strategy.md` gains §4.8, the formal model as a component, with the claims. Its §3 and §8 change to match, and the slow tier runs the model's proofs and its differential.
- `ways-of-working.md` §9 is rewritten around this record. Its Dafny guidance goes.
- `formalisation-review.md` moves to `docs/archive/`. Its claims, and its two deficits still open, live on in `correctness-strategy.md` §4.8.
- The driver's value table in clingo-i had four obligations that `decisions/0002` would have given to Dafny: dense ranks preserve order and are equal exactly when the values are; sums follow XSD 1.1 Appendix E; int32 overflow is handled by ranking; every unplaceable value has a reason. The value table is where clingo-i's real bugs have appeared. Its obligations become property tests first, and a target for the chosen prover once the spike has priced proofs (issue #70).
- Two choices in `due2-workflows.md` §6.4 are justified by monotonicity: `invalid` voids the policy rather than making it `Indeterminate`, and `violations = deny` treats a violated obligation as a prohibition. Whether the spec should mark them as chosen for provability, rather than as readings of ODRL or DPROD, is an open question (issue #70).
- Issue #70 becomes a milestone with sub-issues. Issue #8 is re-scoped to `Den` in the chosen prover.

## Revisit when

- Neither spike gives a model that a reader of `due2-workflows.md` §6 can follow → reconsider the prover, or keep only the Alloy models and the bounded-exhaustive search.
- The differential cannot keep model and implementation in step, for example because the model cannot run on corpus-sized inputs → consider extraction.
- A claim that the search has cleared fails in the prover → the search's bounds were too small; widen them before trusting other cleared claims.

## Amendment (2026-10-22, the search over clingo-i)

Item 3 gave every claim both a small Alloy 6 model and a bounded-exhaustive search over clingo-i's program. The owner narrowed the search on 2026-10-22, in #85: it covers M and W only. Each claim still gets its Alloy model, and a claim goes to the prover after its Alloy model, and for M and W the search, have run at stated bounds without a counterexample.

- **M stays.** clingo-i and its brute-force oracle both enumerate every completion (`spikes/clingo-i/DESIGN.md` § Data flow, `spikes/clingo-i/TESTS.md`), so neither uses the two-extreme shortcut that M justifies and that W2 and W3 will use. The search computes the verdict range as *Computing it* in `due2-workflows.md` §6.4 does, enumerating the mixed variables and setting the uniform ones to the two extremes, and checks that it equals the range over every completion, on the spaces of `spikes/clingo-i/TESTS.md`. That covers duties and `violations = deny`, on the semantics clingo-i implements. Neither `check_completion.py`, which runs an abstract model, nor the Lean spike (#87), which leaves duties out, covers them.
- **W gets one attempt** (#77). The shape it needs, a definite verdict with an empty basis, joins the shapes the slow spaces must reach. If they reach it, the property is checked over them. If they do not, #77 is parked, and the argument in `spikes/clingo-i/DESIGN.md` § `resolve.lp` stays W's evidence. W guards `tools/check_corpus.py`'s check of hand-derived bases, not an evaluator, so it does not justify widening the spaces.
- **K leaves the search.** clingo-i and its oracle use the same completion key, so a search that compares them cannot find the key wrong (`correctness-strategy.md` §4.8). Only a model that derives each part's value from an operand value tests it, which is what the Alloy model does (#84).
- **F leaves the search.** It is left to its Alloy model and the prover. The W2/W3 bakeoff compares each backend's frontier with clingo-i's (#38, #40, #41), so a search over clingo-i alone adds little.
- **P is unchanged.** It is a question, settled by a spec edit or a decision record (decision item 2), and was never a search target.
