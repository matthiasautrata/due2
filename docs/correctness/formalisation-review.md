# due2 — Formalisation review (2026-10-17)

**Status:** Review input, 2026-10-17. **Not adopted.** Nothing here changes a [D] item. It is material for when the semantics program covers enough of the corpus to be worth formalising. Its own trigger is about 100 passing vectors; clingo-i passed 29 of 397 at `f5dc357`, and 172 of 406 at `e301c46`.
**Companions:** `correctness-strategy.md` (the adopted plan; §4.5 cites `check_completion.py`) · `decisions/0002` (W1 in Python with a Dafny oracle) · `decisions/0009` (the semantics as a clingo program) · `implementation-alternatives.md` (the 2026-10-10 review of Python+Dafny, Lean, Clingo, OCaml+Why3) · `spikes/clingo-i/DESIGN.md`.

The user brought this review in on 2026-10-17. §1–§4 keep its substance. §5 records what was checked against the repository at `f5dc357`, and again at `e301c46` when the trigger was reached. §3 marks each deficit's state at `e301c46`. §6 lists what adopting any part would touch.

---

## 1. Four obligations, not two

| | Obligation | Provable? |
|---|---|---|
| **A** | **Adequacy:** the profile's reading of ODRL 2.2 and DPROD is the intended one | **No.** It is interpretative and empirical; a proof cannot reach intent. |
| **B** | **Coherence:** the semantics is total, stratified and law-abiding, and its definitions agree with each other | Yes, but A is not a premise: a consistent semantics can be consistently wrong. |
| **C** | **Algorithm ⊨ definition:** the two-extreme computation equals ∀-completion; `exact`; `frontier_complete` | **Yes.** This is the whole proof-shaped content. |
| **D** | **Code ⊨ algorithm:** the `.lp` files and the pipeline implement C | Partly provable, mostly differential: a translation, not a theorem. |

A is the obligation that matters most ("does the profile and semantics make sense"), and it cannot be proven. C and D are different objects, and the repository proves neither. `check_completion.py`, which all of C's evidence rests on, checks an abstract flat model ("flat conjunctions, unguarded obligations, no recurrence"), so the differential shares its shape with the algorithm it checks: a common-mode risk (R3, R4).

## 2. Recommendation: prove the algebra, not the code

Extract the roughly 150 lines of mathematics that carry the risk: findings → candidates → eliminations → frontier → verdict. Prove three theorems about it in a kernel-checked prover. Prove the functional parts (`Den`, expansion, the driver's value table) with SMT, as already planned. Answer A by falsification and comparison, never by proof.

Each theorem is a literal sentence of the spec:

- **M (monotonicity).** §6.4: "the verdict is monotone in every finding", so the two-extreme computation is exact over all 2ⁿ completions. The evidence today is five hand-written cases and 20,000 random instances. M is load-bearing: if it is false, the evaluator returns wrong definite verdicts. It needs induction over arbitrary finite atom sets, the metatheory shape for which Cedar moved from Dafny to Lean.
- **K (the completion key).** §6.4's exactness rests on "identical or complementary operand bindings share one variable". K makes two claims:
  - *soundness*: the key never merges parts whose truth values can differ under a real value; if it did, a definite verdict would be wrong;
  - *one-sidedness*: the remaining independent parts only ever yield `Indeterminate`, which is what makes L9's refinement direction true.

  K is false in general, and the spec says so (`x ≤ 5` vs `x > 7`; §9 #6, issue #25). Formalising K first gives a precise, machine-checked statement of that hole in place of a paragraph.
- **F (frontier relevance).** §6.4: "no other unknown can move the frontier while the verdict stands". The monotonicity argument cannot reach it, because a frontier is a set, not a point on the chain. Its evidence is 942 instances out of 50,000. It is the least-proven claim in the spec and the best single target.

**Vehicles, ranked by fit:**

1. **Isabelle/HOL.** The best fit for this shape: finite relational combinatorics, `inductive` and `fun` definitions, `auto` and Sledgehammer for the case analyses. Less proof engineering than Lean for M, K and F. It was absent from the 2026-10-10 review.
2. **Lean 4.** The same theorems at a higher up-front cost. It has the precedent (cedar-spec), and it reads best as a method showcase. Choose it for credibility, not for least effort.
3. **Extraction from Rocq or Isabelle.** The structural fix for D: write the semantics once as a total definition and extract the L9 oracle mechanically. "Code = algorithm" is then true by construction. Lean's code generation is the weak leg, which argues for Rocq or Isabelle here.
4. **Dafny or WhyML.** Keep them where `decisions/0002` puts them: `Den`, stage-1 expansion, and the driver's value table. The value table's obligations are list-and-bounds programs, where SMT automation is strongest:
   - dense ranks are order-preserving, and equal iff the values are equal;
   - sums follow XSD 1.1 Appendix E;
   - int32 overflow is handled by ranking;
   - every unplaceable value has a reason.

   This is also where the only two real bugs so far turned up: rdflib's lossy `NORMALIZE_LITERALS`, and a `re.Match` slice in `values.duration` (86 vectors).
5. **Direct SMT** (Z3 or cvc5, SMT-LIB, quantifiers over a finite domain). The cheapest route to solver-discharged proofs of bounded instances of M, K and F. It has no kernel, and it is brittle, as Cedar found.
6. **Alloy 6, bounded model finding.** Not a prover, and that is the point. Within minutes it can falsify L1–L10, the profile invariants, and the "`Indeterminate` that shouldn't be" class, over small scopes. Its relational core matches the workflows appendix "Why tuples" almost one to one: atoms, relations, ⊆/⊊ frontiers, partial orders. **This is the instrument for A.**
7. **K or Maude (rewriting logic).** The semantics *is* the artefact, with LTL model checking and an interactive prover. A real fit, but a heavy toolchain with no ecosystem here.
8. **Kleene-annotated Datalog** (the cheapest of all). State the finding layer as Datalog annotated with the three-valued Kleene lattice, a K-relation in the provenance-semiring style (Green, Karvounarakis and Tannen, `references.md` §2). Stratification, unique-model determinism and monotonicity then follow from standard results, and only the ODRL-specific parts (the key, the conflict strategies, the frontier) need fresh proofs. `decisions/0009` #3 already says "the evaluation layer is stratified Datalog". This makes that claim the formulation instead of a footnote, and makes M nearly free.

**For A, three instruments and no proof:**

1. A delta against DPROD's `formal-semantics.md`, with exceptions 1–6 restated as explicit refinement claims. That document is not vendored, so a comparison due2 leans on a dozen times cannot currently be repeated.
2. Alloy and other small-scope falsification of L1–L10.
3. The external suites' own answers (already in place).

**The external formal semantics are inputs, not authorities** (the user, 2026-10-17). RL2's (`~/src/RL2`), DPROD Contracts' (`formal-semantics.md`), and OVAL's (the Southampton papers, arXiv 2509.05139, 2603.12926 and 2607.15987, `references.md` §1) are each well-intended. That does not make them correct. Before due2 relies on any of them for adequacy, each gets a careful review of its own, issue #63. DPROD's points in the right direction but is not trusted: expect suggestions and fixes to send upstream. due2 already adopts some of its rules unchanged (`due2-profiles.md` §8, for example one binding per left operand, its §6.2), and those adoptions are subject to the same review.

**An uncomfortable finding.** The proof obligation has already bent the semantics. Two choices are each justified in §6.4 by "otherwise … breaks monotonicity": `invalid` voids the policy rather than making it `Indeterminate`, and `violations = deny` treats a violated obligation as a prohibition. A formal spec should record these as chosen for provability, not as readings of ODRL or DPROD.

## 3. Deficits found reading the code

1. **`decisions/0009`'s Kleene obligation is half-built.** There is no `#max` in `lp/`, only conjunction (`#min`). Disjunction (`fulfilled` over witnesses, §5.3) and the `dprod:not` involution are not implemented. Neither are constraint parts, and with them the whole correlated-variable key that K is about. The 29 passes never exercise disjunction or negation.
   - *At `e301c46`:* partly fixed. Constraint parts, disjunction (`#max` in `compare.lp`), and `dprod:not` landed with #47 (`6b67c98`). The key has not. `completion.lp` completes target and party parts, which share variables by request field (`decisions/0012`). A `u` constraint part declines the vector (`completion`, 47 vectors at `e301c46`), and its key, the shared variables of `due2-workflows.md` §6.4, is issue #48's work.
2. **"Fails loudly" stops at the finding layer.** The integrity constraints cover `holds` and `cval` per item, and `verdict`. Nothing constrains `atom_effect`, `atom_policy` or `atom_rule`. A rule referenced by both `odrl:permission` and `odrl:prohibition` would give one atom id two effects, silently. Since `effect` is part of §3.1's atom key, that is a corrupt corpus accepted without a diagnostic.
   - *At `e301c46`:* fixed by #59 (`5f3e22d`). `explain.lp` requires exactly one `atom_effect`, `atom_policy`, and `atom_rule` for every atom.
3. **Cross-policy elimination is not recorded as one.** `deny :- forbidding(X), not eliminated(X)` folds §6.2's cross-policy rule into the verdict instead of recording an elimination with its rule. §3.5 records every elimination with its rule, so `eliminated` cannot be derived from the program as written. #59 has to add it.
   - *At `e301c46`:* fixed by #59 (`5f3e22d`). `explain.lp` records every removal as `elim(X, Y, Strat)`, the cross-policy one under `"prohibit-overrides"`. `structure.lp` admits one policy, so no vector reaches that rule; `test_combination_rows_on_facts` runs it on hand-written facts.
4. **The differential is not the definition.** The abstract model in `check_completion.py` (flat conjunctions, no nested constraints, no recurrence) is shared with the algorithm it checks. M, F and the `max_mixed` fallback are each checked against a model, not against §6.4, and each failure mode is a wrong definite verdict.
   - *At `e301c46`:* still open. `check_completion.py` keeps its own abstract model (one policy; `Permit` and `Forbid` atoms; duties guarded by literals over the same variables), not the semantics clingo-i implements.
5. **The oracle has no audited ground.** The mapping from rule blocks to spec sections is prose in `DESIGN.md`, and nothing checks it: the `% workflows §6.1` comments are outside the cross-reference sweeps. Since `decisions/0009` makes the program a second semantics, encoding faithfulness is the largest structural gap, and running the corpus cannot close it.
   - *At `e301c46`:* still open. `tests/test_docs.py` checks the doc blocks and their references, but no test maps a rule block to the spec section it encodes.

## 4. Order of operations

The order matters more than the choice of vehicle.

1. **Lift `check_completion.py` to the real semantics, or prove it an abstraction of it.** Otherwise the proof subject and the differential subject are different objects.
2. **Finish `decisions/0009` #3 in code** (disjunction, `dprod:not`, constraints and the key) before formalising anything. Do not formalise a semantics that declines 93% of the corpus, and do not let a proof bless rules that don't exist.
3. **Then M, K and F.** Isabelle first; Lean if the goal is the showcase; extraction from Rocq or Isabelle if the goal is one artefact. Pin the development to a spec version: a proof that outlives its spec proves the previous one.
4. **Dafny or WhyML on `Den`, expansion and the value table**, as already sequenced (`decisions/0002`, issue #8). That is where bugs have actually appeared.
5. **A stays empirical:** the DPROD delta (vendor the document), Alloy for L1–L10, the external suites. Do not attempt a proof of adequacy.

**Decision rule.**

- Showcase or credibility → Lean 4.
- Least proof effort for the same theorems → Isabelle/HOL.
- Spec = oracle, with no correspondence gap → extraction from Rocq or Isabelle.
- Counterexamples this week → Alloy, plus bounded-exhaustive testing over the real semantics.

Revisit all of it when the program clears about 100 vectors. The object to formalise does not exist yet, and the first payoff of formalising, surfacing spec ambiguity (R4, R5), was largely collected by writing `DESIGN.md`.

## 5. Checked against the repository (2026-10-17)

**At `f5dc357`:**

| Claim | Checked | Result |
|---|---|---|
| clingo-i at `f5dc357`: 397 vectors, 29 pass, 368 unsupported | `uv run pytest --backend=clingo-i` | Confirmed |
| No verification toolchain on the development machine | `command -v` for lean, dafny, why3, z3, cvc5, isabelle, alloy | Confirmed: none installed |
| §3 #1: no disjunction in `lp/` | `rg '#max\|#sum' lp/` | Confirmed: only `#min` and `#count` |
| §3 #2: integrity constraints only on items and the verdict | `rg '^:-' lp/` | Confirmed (`kleene.lp`). The double-effect atom was not reproduced. |
| §3 #3: cross-policy denial without an `eliminated` row | `lp/resolve.lp` lines 11–16 | Confirmed: `eliminated/1` exists within a policy only |
| `formal-semantics.md` is not vendored | `profiles/vendor/dprod/` | Confirmed: only the two `.ttl` files and the examples |
| `violations = deny` justified by monotonicity | workflows §6.4 | Confirmed, and already recorded as DPROD exception 6 (`due2-profiles.md` §8.2); the "chosen for provability" framing is new |
| `invalid` voiding justified by monotonicity | workflows §6.2, §6.4 | Checked at `e301c46`; see below |

**At `e301c46`** (2026-10-17, when the trigger was reached):

| Claim | Checked | Result |
|---|---|---|
| clingo-i at `e301c46`: 406 vectors, 172 pass, 234 unsupported | `spikes/clingo-i/scorecard.json` (`a731e76`) | Confirmed. The largest decline reasons are a constraint on a node that is not a rule (83), `odrl:duty` (48), completion (47), `odrl:obligation` (41), and `rdf:value` (15). |
| No verification toolchain | `command -v`, as above | Confirmed: none installed |
| §3 #1: disjunction and `dprod:not` | `rg '#max' lp/` | Fixed: `compare.lp` takes the Kleene disjunction with `#max`. The key is still missing (#48). |
| §3 #2: one-value constraints on the structure | `rg '^:-' lp/` | Fixed: `explain.lp` lines 20–22 |
| §3 #3: cross-policy elimination recorded | `lp/explain.lp`, `elim/3` | Fixed: the cross-policy rule is recorded with its strategy. Only hand-written facts reach it, because `structure.lp` admits one policy. |
| `formal-semantics.md` is not vendored | `profiles/vendor/dprod/` | Confirmed: the `.ttl` files, the examples, and the shapes only (#35) |
| `invalid` voiding justified by monotonicity | `due2-architecture.md` §6.2 (the 2026-10-11 [D] entry); workflows §6.4 | Partly. The [D] entry gives two reasons: voiding is ODRL's reading (the policy does not govern), and it keeps the verdict monotone. So monotonicity is not its only justification. Workflows §6.4 adds that reading `invalid` as `Indeterminate` would put a value outside the chain, so that parked alternative would need its own argument. `violations = deny`, by contrast, cites monotonicity as its only reason (workflows §6.4; DPROD exception 6). |

The trigger's count is met, but the declines fall where theorems K and F apply. K needs the completion key (#48). F needs the frontier, and clingo-i declines `odrl:duty` and `odrl:obligation` (89 vectors). So §4's steps 1 and 2 still come first. On 2026-10-17 the user set the order: finish the clingo-i corpus runner (issue #9), then take up this review, counterexamples first (§4's decision rule: Alloy, plus bounded-exhaustive testing over the real semantics). Issue #70 holds that work.

## 6. What adopting a part would touch

- **Extraction (vehicle 3)** would revisit `decisions/0009` (the hand-written program as the L9 oracle) and possibly `decisions/0002`, so it needs a decision record.
- **M, K, F in a prover** add a component to `correctness-strategy.md` §4 and a register item for the tool. Issue #23 holds the tooling picks.
- **§3 #2 and #3** are spike defects. #3 is already #59's work; #2 is a small integrity constraint.
- **§4 #1** amends `correctness-strategy.md` §4.5 ("Abstract model extended").
- **Vendoring `formal-semantics.md`** goes with issue #35 (the DPROD re-sync).
- **Reviewing the external semantics** (RL2, DPROD, OVAL) is issue #63, before the DPROD delta is used as evidence for A.
- **The provability framing** for `violations = deny` and `invalid` would be a spec note in workflows §6.4 and in `due2-profiles.md` §8.2.
