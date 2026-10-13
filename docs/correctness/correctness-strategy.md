# due2 — Correctness Strategy

**Status:** Draft v0.3, 2026-10-11. Every item that is new here is marked **[O]** until adopted.

**Changes in v0.3:** `I` comes in two modes, slow first (§3); the disagreement protocol (§6) and the generator coverage check (§5) adopted.

**Changes in v0.2:** critical features and the three testing modes decided (§1.1): atomization, evaluation, and case history get bounded-exhaustive, generated, and differential testing. Case history added as a component (§4.7, risk R10). Parser sharing decided (§4.1). Invalid-input twins for every generator (§5).
**Companions:** `ways-of-working.md` (the discipline and the tools: types, contracts, Hypothesis, tiering, Dafny) · `due2-architecture.md` §10 (the conformance suite) · `due2-workflows.md` §8 (laws L1–L9) · `odrl-compound-to-atomic-normalization.md` §8, §10 (stage-1 invariants, `Den`, minimum suite) · `decisions/0002` (which oracles exist).

Markers as in the companions: **[D]** decided · **[O]** open, alternatives listed · **[F]** blocked on an external unknown.

---

## 0. Why this document exists

The pieces of a testing approach are already in the repository, but they are spread over five documents. Nowhere does one place say which check guards against which failure, what each oracle is independent of, or what has to exist before a component is coded. This document says those three things. It does not restate the laws, invariants, or tools. It cites them.

"Correctness" rather than "testing": tests are one instrument among several here. Others are hand derivations, a direct interpreter, a denotational oracle, a randomised check of a proof, and machine-checked extraction. What has to be planned is the argument that the implementation means what the spec says, and tests are only part of it.

---

## 1. The rule: strategy before code **[D]** (2026-10-11)

No component gets implementation code until its entry in §4 states:

1. **Risks.** Which classes of §2 the component can cause.
2. **Oracles.** What decides the right answer, and what each oracle shares with the implementation (§3).
3. **Properties.** The laws and invariants it must satisfy, which run as properties.
4. **Golden vectors.** Hand-derived inputs and outputs, positive and negative.
5. **Generators.** Which inputs the property tests draw, and how we know they reach the hard cases (§5).
6. **Done.** The gate the component passes before anything downstream builds on it.

An entry can be short. It still has to exist and be reviewed before code. Writing the oracle and the properties first is also the cheapest spec review there is: each ambiguity they surface is a spec edit, not a bug fix later.

### 1.1 Critical features **[D]** (2026-10-11)

Three features carry the weight of the system, and each gets the strongest treatment below: **bounded-exhaustive**, **generated**, and **differential** testing together, not one of them.

| Feature | Components | Why critical |
|---|---|---|
| **Atomization** | W1 stage 1 (normaliser) and stage 2 (builder) | Every semantically interesting rewrite happens here, and a mistake is silent (R1) |
| **Evaluation** | W2 and W3 | Where `U` is preserved or lost (R2) and where completion decides (R3) |
| **Case history** | The ledger: recording, replay, re-evaluation (architecture §7, workflows §7) | The audit answer — what was decided, when, on which inputs, and why — must be reproducible years later (R6, R10) |

The three testing modes are:

- **Bounded-exhaustive.** Over a deliberately tiny vocabulary — for example two actions, two targets, two parties, two facts each drawn from all five statuses, policies of up to three rules with up to two constraints — enumerate *every* input, not a sample. Most defects show up on small inputs ("small-scope hypothesis"), and enumeration guarantees none of them is skipped. The bounds are set per feature by what finishes in the slow tier, and the PR tier runs a smaller bound.
- **Generated.** Hypothesis over larger inputs, with the generators of §5.
- **Differential.** Every critical component has an independent counterpart, and both run on every exhaustive and generated input:

| Implementation | Counterpart |
|---|---|
| W1 stage 1 | `Den` (Python, then Dafny) through the lineage bijection |
| W1 + W2 + W3 | `I`, the direct interpreter (L9) |
| W3 | Brute-force W3 over every completion of the findings |
| Replay of a recorded evaluation | The original trace, byte for byte |
| Re-evaluation of a case history | A from-scratch evaluation over the current inputs |
| Any second backend | The first |

Negative inputs are part of all three modes: the enumerator and the generators also produce invalid policies, and the expected result is the rejection with its diagnostic.

---

## 2. What can go wrong

The ranking is by how silent the defect is, not how likely it is.

| # | Defect class | Why it is dangerous | Where it can arise |
|---|---|---|---|
| R1 | **Silent meaning change in W1.** A mis-normalised policy still evaluates cleanly; it just means something else. | No crash, no `Indeterminate`; only a preservation check sees it | W1 stages 1–2 |
| R2 | **`U` collapse.** Unknown treated as false (or true) somewhere between a fact and the verdict. | Every external evaluator does this (`conformance/external/README.md`); it is the most natural bug to write | W2 parts, Kleene connectives, W3 completion |
| R3 | **Completion error.** Wrong variable sharing (the canonical-literal key), wrong uniform/mixed classification, unsound `max_mixed` fallback. | Turns a correct `Indeterminate` into a definite verdict, or the reverse | W3 §6.4 |
| R4 | **Spec error.** The prose is wrong or underspecified, and the implementation copies it faithfully. | Every oracle derived from the same prose shares it | All |
| R5 | **Corpus error.** A hand-derived expected verdict is wrong. | 99 positive and 8 negative cases, none of whose verdicts has been machine-checked yet | `conformance/cases/` |
| R6 | **Nondeterminism and identity drift.** Output depends on tuple order, hash seed, locale, or unrelated edits. | Breaks replay (workflows §7) and the ledger | W1 identity, trace serialisation |
| R7 | **Boundary leak.** W2 reads another atom's finding; W3 reads the request or SOTW. | Invalidates the parallelism and the completion argument | W2, W3 |
| R8 | **Unexplained divergence from an origin evaluator.** | Undermines the compatibility claims | Translated cases |
| R10 | **Case-history corruption.** An earlier decision is edited instead of superseded; an evaluation does not pin enough to replay; a normaliser upgrade silently changes old answers; an as-of query answers from today's policy. | The audit question gets a plausible wrong answer | The ledger, re-evaluation |
| R9 | **Generator blind spots.** Properties pass because the generators never produce the hard inputs. | False confidence, the most expensive kind | All property tests |

---

## 3. Oracles and their independence

An oracle is only as useful as it is independent. The question for each one is what it *shares* with the implementation, because a defect in the shared part is invisible to it.

| Oracle | Decides | Independent of | Shares (common-mode risk) | Status |
|---|---|---|---|---|
| Hand-derived corpus (99 positive cases plus 8 negative, `why` per scenario) | End-to-end verdict, frontier, obligations | All code | The prose; the deriver's reading of it (R4, R5) | **[D]**, exists |
| External suites' own answers (`force_expected`, …) | The origin's semantics | due2's prose | Nothing; differences are explained in `notes` | **[D]**, exists |
| L9 direct interpreter `I` over the lifted form | The pipeline's verdict (L9) | W1's rewriting and the corpus relations | Prose of workflows §5–§6; the canonical-literal key; the parser, if shared (§4.1) | **[D]** (`decisions/0002`), issue #9 |
| `Den` (normalisation §8.1), Python, then Dafny | Stage 1, invariant 3 | §6's algorithm: memoization, fan-out, Atomic Policy construction | `Sel` | **[D]**, issue #8 |
| `tools/check_completion.py` | §6.4's two-extreme computation against brute force | Everything else | Its abstract model: flat conjunctions, unguarded obligations, no recurrence | **[D]**, exists |
| Laws L1–L9, invariants 1–10 | Metamorphic relations; no expected output needed | The expected outputs | The law statements themselves | **[D]**, properties to write |

**Principle: the oracle implements the definition, the implementation implements the algorithm.** **[D]** (2026-10-11) Wherever the spec gives both a definition and an efficient way to compute it, the oracle uses the definition. Concretely:

- `I` has two modes over one interpreter, differing only in how they complete unknowns.
  - **Slow `I`, built first.** It enumerates every assignment of the literal variables (the definition at the top of workflows §6.4), with no uniform/mixed split and no two-extreme computation. Above a variable cap (for example 16) it declines rather than falling back. Against slow `I`, a pipeline disagreement exposes R3 as well as R1; with the shortcut inside, a flaw in the monotonicity argument would be invisible.
  - **Fast `I`, later.** It uses §6.4's computation, so it has no cap and can run large generated inputs. Slow and fast `I` are differentially tested against each other below the cap, which checks the shortcut on authored policies.
- The `Den` oracle has no memoization or fan-out bookkeeping, as §8.1 already requires.
- A brute-force W3 (every completion of the actual findings) is the differential target for the production W3, as `check_completion.py` is for the abstract model.

**When oracles disagree** (§6), the corpus is not automatically right. `I` running the corpus is the first second derivation the 99 hand-derived verdicts have ever had, which makes it as much a check on R5 as on any code.

---

## 4. Per component

Ordered as they will be built (§8). Each entry is the §1 plan. "Before code" lists the items that must exist first.

### 4.1 The L9 oracle `I` (issue #9)

- **Risks.** R4 and R5, surfaced. R2 in its own Kleene evaluation.
- **Oracles for the oracle.** The corpus (99 positive cases), with disagreements triaged per §6. Its own laws: `I` must satisfy L4 (information monotonicity) and L5 (prohibition monotonicity) on generated inputs; failing them means `I` or the spec is wrong.
- **Properties.** L4 and L5 on `I`. Exhaustive Kleene truth tables for `and`, `or`, `xone`, and `dprod:not` over `{T, F, U}`, which are small enough to enumerate.
- **Golden vectors.** The corpus. Slow `I` must decide every case below the cap; a case above it is reported, not skipped silently.
- **Generators.** None needed for the first gate. The §5 generators come in for L9 against the pipeline (§4.3).
- **Parser.** **[D]** (2026-10-11) `I` and W1 share the RDF-to-lifted-tree parser. Because L9 cannot see a parser bug, the parser is tested on its own: round trip (parse, render, parse gives the same tree), invariance under triple order and blank-node labels, and agreement with `tools/check_corpus.py` and `tools/check_odrl22.py` on what it accepts and rejects, over the corpus, the vendored policies, and the external suites.
- **Done.** 99 of 99 positive cases agree, or each disagreement has a triage record (§6) that landed as a commit to the case, the spec, or `I`.

### 4.2 W1 stage 1: the normaliser

- **Risks.** R1, R6.
- **Before code.** ~~The case format needs negative cases.~~ Done 2026-10-11: `expected_rejection` (`conformance/README.md`), with codes from `due2-diagnostics.md`. `force-01` … `force-07` and `due2-witness-outside-duty` are the first; the rest of normalisation §10's negative vectors are a coverage gap.
- **Oracles.** `Den` through the lineage bijection (invariant 3). Golden vectors from normalisation §10.
- **Properties.** Invariants 6 (determinism over permuted triples, JSON-LD order, and blank-node labels), 7 (idempotence), and 10 (locality: an unrelated edit changes no output IRI). Invariant 8 as exact-limit success and limit-plus-one failure.
- **Done.** The §10 minimum suite passes, `Den` agrees on every positive vector and on generated policies, and the Dafny `Den` (issue #8) follows as the second, machine-checked oracle.

### 4.3 W1 stage 2: the builder (lifted form to relations)

- **Risks.** R1 (DNF, `xone`, `dprod:not` pushed inward, instantiation), R3 (the canonical-literal key is derived here).
- **Oracles.** `I`, through L9 on generated policies.
- **Properties.** L9. Complement pairs (`eq`/`neq`, `lt`/`gteq`, `lteq`/`gt`, `isAnyOf`/`isNoneOf`) map to one variable with opposite polarity, and identical parts map to one variable. The atom-count limit fails before any output.
- **Done.** L9 holds on the `fast` and `nightly` Hypothesis profiles (`ways-of-working.md` §7.2), and the corpus runs through W1 without rejections other than expected ones.

### 4.4 W2: evaluate

- **Risks.** R2 above all, then R7.
- **Golden vectors.** The **status matrix**: for every operator and every fact status (`resolved`, `missing`, `invalid`, `conflict`, `unresolved`), the part's truth value, enumerated exhaustively. A non-`resolved` status gives `U`, with no exceptions (`ways-of-working.md` §5.1). This is the primary defence against R2 and is cheap to make complete. The same for request parameters (absent means `missing`) and for absent parties and targets (workflows §3.2).
- **Properties.** L2 (an atom's finding is unchanged by other atoms), L3 (prefetch neutrality), L8 (skip soundness). Plan coverage: W2's `read` is within `plan(corpus, request)` for every generated and corpus evaluation (workflows §3.3). Duty instances and statuses against the workflows §5.3 table, over generated deadlines and recurrences.
- **Done.** The status matrix is complete and passing, the properties hold, and the corpus's `obligations` agree.

### 4.5 W3: resolve

- **Risks.** R3, R7.
- **Oracles.** A brute-force W3 over every completion of the actual findings (§3), capped by variable count. `I` end to end.
- **Properties.** L4–L7. `verdict.exact = true` whenever the mixed-variable count is at most `max_mixed`, and a fallback verdict that is never definite where brute force says `Indeterminate`. Golden vectors at `max_mixed` and at `max_mixed + 1` (`due2-max-mixed`).
- **Abstract model extended.** **[D]** `check_completion.py` now models deadlines, violated preconditions, `violations = deny` (fourth phase) and the listed frontier against every completion's (fifth phase). It found no mismatch. `frontier_complete` is computed by bounded enumeration over the relevant unknowns (`decisions/0004`), which the fifth phase checks against the definition, fallback included. Multi-policy conflict under `invalid` waits for the brute-force W3 differential. Nested constraints are left to the brute-force W3 differential and slow `I`.
- **Done.** The differential against brute-force W3 is clean on both profiles; the corpus passes, including `frontier` and `verdict_basis`.

### 4.6 Trace and replay

- **Risks.** R6.
- **Properties.** L1: identical trace bytes across tuple-order permutations, `PYTHONHASHSEED` values, and locales, run as a matrix in the PR tier. Replay of every recorded evaluation gives the same digests (workflows §7).
  - *Normaliser upgrade.* Replaying recorded evaluations under a new normaliser version is a regression check, outside the ledger: the same inputs giving a different verdict is a defect, or an intended change that carries a decision record. Every changed verdict is reported; the ledger is never written.

### 4.7 Case history: the ledger

- **Risks.** R10, R6.
- **Before code.** **[O]** The ledger has no data model at the level of workflows §3: architecture §7 says what an evaluation pins and how re-evaluation behaves, but not the relations or the as-of query. That has to be specified first, in `due2-workflows.md`, because the properties below are stated over it. Settled so far (2026-10-13):
  - a case is created when a request is made, and its id is the thread identity; evaluations are events on the case, and a transition is two successive evaluations of one case, not a record of its own;
  - time is bitemporal: validity time (`request.at`) and decision time (`sotw.effective_at`), plus the time an event was recorded;
  - an evaluation's SOTW is the case's snapshot: the answers it recorded, with their values, not timestamps into a source; a pure `plan` sweep lists them before evaluation, and the case records answers, never the datasets behind them (workflows §3.3);
  - exercise events (access taken under a permit) are out of scope for now.

  The model itself is expected to follow the entity-event pattern: a case and the timeline of events on it.
- **Oracle.** A from-scratch evaluation over the current inputs. Re-evaluation, whichever trigger is chosen (architecture §7, issue #14), must agree with it.
- **Properties.**
  - *Replay.* Every recorded evaluation, re-run under its pinned normaliser versions, gives byte-identical traces.
  - *Pinning suffices.* Re-running with the SOTW cut down to the evaluation's recorded reads gives the same trace (a consequence of L3); an evaluation that needs more than it pinned is a defect.
  - *Append-only.* No operation changes an earlier event; re-evaluation adds an evaluation to the case.
  - *Both directions.* Transitions occur in both directions — `Pending` to `Permit` on evidence, `Permit` to `Deny` on a changed fact or policy — and only resolving unknowns, with nothing else changed, never moves one definite verdict to another (L4).
  - *Two clocks.* An as-of query for an earlier decision answers from that evaluation, unaffected by later policy amendments, SOTW revisions, or normaliser upgrades.
- **Model-based.** A Hypothesis stateful machine (`ways-of-working.md` §7.1) drives event sequences — request, submit evidence, change or resolve a fact, amend a policy, upgrade the normaliser, re-evaluate, query as-of — against a reference model that recomputes everything from scratch. Sequences are also enumerated exhaustively up to a small length.
- **Done.** The stateful machine and the enumerated sequences are clean, and every corpus scenario that awaits a duty has a history case that carries it through to its next verdict. That needs a case-format extension: one case, a sequence of SOTW revisions, an expected verdict per revision.

---

## 5. Generators **[O]** (coverage check **[D]**, 2026-10-11)

The Hypothesis strategies for policies, requests, and SOTWs are shared by every component in §4. They are a first-class artefact and get reviewed like spec text, because a blind spot in them (R9) silently weakens every property at once.

Requirements:

- **Biased towards unknowns.** Draw fact status uniformly over all five statuses rather than mostly `resolved`. A generator that rarely produces `U` cannot find R2 or R3.
- **Correlated by construction.** Reuse operands deliberately: identical parts, complement pairs, and one fact read both ways across rules. Mixed variables appear only when a generator aims for them.
- **Structurally complete.** Nested `and`, `or`, `xone`, and `dprod:not`; shared duties; guarded duties; deadlines and recurrences; all three conflict strategies; `violations = deny`.
- **Valid and invalid.** Each generator has a twin that produces near-miss invalid inputs — one rule left unnamed, an operand unbound, a cycle, a limit exceeded by one — with the expected rejection.
- **Shared with the enumerator.** The bounded-exhaustive enumerator of §1.1 and the Hypothesis generators draw from one description of the input space, so the two cannot drift apart.
- **Measured.** Each run reports a histogram of which features it exercised, using the feature list behind the coverage-gap list in `conformance/README.md`. A feature with zero hits fails the run. This makes R9 visible rather than assumed.

---

## 6. When sources disagree **[D]** (2026-10-11)

A disagreement between the corpus and `I`, between `I` and the pipeline, or between an origin's answer and due2's is a finding about the spec until shown otherwise.

1. **Never edit an expected verdict so the code passes.**
2. Re-derive the answer by hand from the spec sections the case's `why` cites.
3. If the spec is ambiguous or wrong: edit the spec, with a decision record if the change is load-bearing (CLAUDE.md), then fix the case or the code.
4. If the case is wrong: fix it, rewrite its `why`, and say what changed in `notes`.
5. If the code or oracle is wrong: fix it and add the input as a committed `@example` or corpus case. This is the ratchet of `ways-of-working.md` §7.3.

Each disagreement leaves a commit that names it.

---

## 7. Gates

The tier placement is `ways-of-working.md` §8. What each tier runs, as the pieces come to exist:

| Tier | Runs |
|---|---|
| Every commit (today) | The commands in `README.md` § Verify: four checkers, plus type checking and lint |
| PR | The above, plus: the corpus through every backend, including `I`; the status matrix and Kleene tables; bounded-exhaustive enumeration at small bounds; Hypothesis `fast` for L1–L9 and the stage-1 invariants; the L1 determinism matrix |
| Slow | Bounded-exhaustive enumeration at full bounds; Hypothesis `nightly`; the brute-force W3 differential at larger sizes; mutation testing on W2, W3, and the builder; the Dafny `Den` check. Results feed the ratchet, not the gate |

---

## 8. Sequence

1. Settle the open items of §9.
2. ~~Case-format extension for negative cases~~ (done 2026-10-11).
3. The status matrix and Kleene truth tables, as data. They are spec as much as tests, and `I` uses them first.
4. Slow `I` (issue #9). Run the corpus and triage per §6. Fast `I` follows once W3's computation is specified in code form.
5. The input-space description, the bounded-exhaustive enumerator, and the generators (§1.1, §5), with the coverage histogram.
6. W1 stage 1 with the Python `Den` oracle; the Dafny `Den` follows (issue #8).
7. W1 stage 2, gated by L9 against `I`.
8. W2, then W3, each gated as in §4.4 and §4.5.
9. The ledger data model (§4.7), then the ledger, gated by the stateful machine.

---

## 9. Open decisions register

| # | Decision | Section | Recommendation |
|---|---|---|---|
| 1 | Strategy before code, as a standing rule | §1 | **Resolved 2026-10-11:** adopted (CLAUDE.md) |
| 2 | Oracles implement definitions; `I` completes by enumeration with a cap | §3 | **Resolved 2026-10-11:** slow `I` (enumeration, capped) first, fast `I` (§6.4's computation) later, differentially tested against each other |
| 3 | `I` and W1 share the parser | §4.1 | **Resolved 2026-10-11:** shared, and tested on its own |
| 4 | Negative cases in the case format | §4.2 | **Resolved 2026-10-11:** `expected_rejection` plus the diagnostic registry (`due2-diagnostics.md`); 8 cases |
| 5 | `check_completion.py` scope (`violations = deny`, `frontier_complete`) vs relying on the brute-force W3 | §4.5 | **Resolved 2026-10-11:** extend it now for both (done); brute-force W3 differential later; nested constraints via that and slow `I` |
| 6 | Generator coverage histogram as a failing check | §5 | **Resolved 2026-10-11:** adopted |
| 7 | The disagreement protocol | §6 | **Resolved 2026-10-11:** adopted |
| 8 | Critical features and the three testing modes | §1.1 | **Resolved 2026-10-11:** atomization, evaluation, case history; bounded-exhaustive, generated, and differential |
| 9 | A ledger data model in `due2-workflows.md` | §4.7 | Specify before ledger code. Partly settled 2026-10-13 (§4.7): case as thread identity, bitemporal, SOTW as the case's snapshot, plan before evaluate, exercise out of scope; entity-event model to follow |
| 10 | Bounds for the exhaustive enumeration, per feature and per tier | §1.1 | Set by measurement once the enumerator exists |
