# due2 — Correctness Strategy

**Status:** v0.11 (2026-10-20). The rule of §1 is a standing rule of the repository (`CLAUDE.md`). An item marked **[O]** is proposed and not adopted.

**Changes in v0.11** (2026-10-20, #83): a cold read. Cross-document references name their document; status markers and struck-through items leave §3, §4.2, §4.5, §4.7, §7, and §8; §3 restates why `I` running the corpus checks R5; §9 lists the open rows with their issues and states rows 1–9 below the table, keeping the row numbers. No rule changes. Earlier changes are in `docs/archive/changes.md`.

Markers as in the companions: **[D]** decided · **[O]** open, alternatives listed · **[F]** blocked on an external unknown.

---

## 0. Why this document exists

The pieces of a testing approach are already in the repository, but they are spread over five documents. Nowhere does one place say which check guards against which failure, what each oracle is independent of, or what has to exist before a component is coded. This document says those three things. It does not restate the laws, invariants, or tools. It cites them.

"Correctness" rather than "testing": tests are one instrument among several here. Others are hand derivations, a direct interpreter, a denotational oracle, a randomised check of a proof, and machine-checked proofs. What has to be planned is the argument that the implementation means what the spec says, and tests are only part of it.

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
| **Case history** | The ledger: recording, replay, re-evaluation (`due2-architecture.md` §7, `due2-workflows.md` §7) | The audit answer — what was decided, when, on which inputs, and why — must be reproducible years later (R6, R10) |

The three testing modes are:

- **Bounded-exhaustive.** Over a deliberately tiny vocabulary — for example two actions, two targets, two parties, two facts each drawn from all five statuses, policies of up to three rules with up to two constraints — enumerate *every* input, not a sample. Most defects show up on small inputs ("small-scope hypothesis"), and enumeration guarantees none of them is skipped. The bounds are set per feature by what finishes in the slow tier, and the PR tier runs a smaller bound.
- **Generated.** Hypothesis over larger inputs, with the generators of §5.
- **Differential.** Every critical component has an independent counterpart, and both run on every exhaustive and generated input:

| Implementation | Counterpart |
|---|---|
| W1 stage 1 | `Den` (Python, then in the formal model, §4.8) through the lineage bijection |
| W1 + W2 + W3 | `I`, the direct interpreter (L9) |
| W3 | Brute-force W3 over every completion of the findings |
| Replay of a recorded evaluation | The original trace, byte for byte |
| Re-evaluation of a case history | A from-scratch evaluation over the current inputs |
| Any second backend | The first |
| clingo-i, and W1–W3 | The formal model (§4.8), on the layers it models |

Negative inputs are part of all three modes: the enumerator and the generators also produce invalid policies, and the expected result is the rejection with its diagnostic.

---

## 2. What can go wrong

The ranking is by how silent the defect is, not how likely it is.

| # | Defect class | Why it is dangerous | Where it can arise |
|---|---|---|---|
| R1 | **Silent meaning change in W1.** A mis-normalised policy still evaluates cleanly; it just means something else. | No crash, no `Indeterminate`; only a preservation check sees it | W1 stages 1–2 |
| R2 | **`U` collapse.** Unknown treated as false (or true) somewhere between a fact and the verdict. | Every external evaluator does this (`conformance/external/README.md`); it is the most natural bug to write | W2 parts, Kleene connectives, W3 completion |
| R3 | **Completion error.** Wrong variable sharing (the canonical-literal key), wrong uniform/mixed classification, unsound `max_mixed` fallback. | Turns a correct `Indeterminate` into a definite verdict, or the reverse | W3, `due2-workflows.md` §6.4 |
| R4 | **Spec error.** The prose is wrong or underspecified, and the implementation copies it faithfully. | Every oracle derived from the same prose shares it | All |
| R5 | **Corpus error.** A hand-derived expected verdict is wrong. | Every implementation is judged against the corpus, so a wrong answer there passes a wrong implementation and fails a right one | `conformance/cases/` |
| R6 | **Nondeterminism and identity drift.** Output depends on tuple order, hash seed, locale, or unrelated edits. | Breaks replay (`due2-workflows.md` §7) and the ledger | W1 identity, trace serialisation |
| R7 | **Boundary leak.** W2 reads another atom's finding; W3 reads the request or SOTW. | Invalidates the parallelism and the completion argument | W2, W3 |
| R8 | **Unexplained divergence from an origin evaluator.** | Undermines the compatibility claims | Translated cases |
| R10 | **Case-history corruption.** An earlier decision is edited instead of superseded; an evaluation does not pin enough to replay; a normaliser upgrade silently changes old answers; an as-of query answers from today's policy. | The audit question gets a plausible wrong answer | The ledger, re-evaluation |
| R9 | **Generator blind spots.** Properties pass because the generators never produce the hard inputs. | False confidence, the most expensive kind | All property tests |

---

## 3. Oracles and their independence

An oracle is only as useful as it is independent. The question for each one is what it *shares* with the implementation, because a defect in the shared part is invisible to it.

| Oracle | Decides | Independent of | Shares (common-mode risk) | Status |
|---|---|---|---|---|
| Hand-derived corpus (positive and negative cases, `why` per scenario) | End-to-end verdict, frontier, obligations | All code | The prose; the deriver's reading of it (R4, R5) | **[D]** |
| External suites' own answers (`force_expected`, …) | The origin's semantics | due2's prose | Nothing; differences are explained in `notes` | **[D]** |
| L9 direct interpreter `I`: the clingo semantics program over the authored form (`decisions/0009`) | The corpus's verdicts; with W1, the pipeline's verdict (L9) | W1's rewriting and the corpus relations | Prose of `due2-workflows.md` §5–§6; the canonical-literal key; the Turtle reader, shared with W1 (§4.1); the program's rules, if the Clingo backend (#41) reuses them | **[D]** (`decisions/0009`), issue #9 |
| `Den` (`odrl-compound-to-atomic-normalization.md` §8.1), Python, then in the formal model | Stage 1, invariant 3 | Its §6 algorithm: memoization, fan-out, Atomic Policy construction | `Sel` | **[D]**, issue #8 |
| The formal model (§4.8): a small executable model in a prover | The claims of `due2-workflows.md` §6.4, by proof; the verdict of every input it covers, by running | clingo-i's encoding and the algorithms of W1–W3 | The prose of `due2-workflows.md` §5–§6 and the formaliser's reading of it (R4); the reader that turns a vector into its input, chosen at the spike | **[D]** (`decisions/0021`), issue #70 |
| `tools/check_completion.py` | `due2-workflows.md` §6.4's two-extreme computation against brute force | Everything else | Its abstract model: flat conjunctions, unguarded obligations, no recurrence | **[D]** |
| Laws L1–L10, invariants 1–10 | Metamorphic relations; no expected output needed | The expected outputs | The law statements themselves | **[D]**, properties to write |

**Principle: the oracle implements the definition, the implementation implements the algorithm.** **[D]** (2026-10-11) Wherever the spec gives both a definition and an efficient way to compute it, the oracle uses the definition. Concretely:

- `I` is the clingo semantics program (`decisions/0009`); it has two modes over one program, differing only in how they complete unknowns.
  - **Slow, built first.** It enumerates every assignment of the literal variables (the definition at the top of `due2-workflows.md` §6.4), with no uniform/mixed split and no two-extreme computation — one answer set per assignment, a verdict definite iff cautious-entailed. Above a variable cap on the unknown literals it declines rather than falling back. The cap is 64, set by measurement in clingo-i (#48): at 64 variables the slowest measured shape, an `and` of tautologies (`x eq i or x neq i`), takes about 1.1 s, and at 128 about 7 s; the corpus needs at most 3. Against slow mode, a pipeline disagreement exposes R3 as well as R1; with the shortcut inside, a flaw in the monotonicity argument would be invisible.
  - **Fast, later.** It uses `due2-workflows.md` §6.4's computation, so it has no cap and can run large generated inputs. The two modes are differentially tested against each other below the cap, which checks the shortcut on authored policies.
- The `Den` oracle has no memoization or fan-out bookkeeping, as `odrl-compound-to-atomic-normalization.md` §8.1 requires.
- A brute-force W3 (every completion of the actual findings) is the differential target for the production W3, as `check_completion.py` is for the abstract model.

**When oracles disagree** (§6), the corpus is not automatically right. `I` running the corpus derives its hand-derived verdicts a second time from the same prose, so a disagreement exposes R5, a misreading, as readily as a defect in code.

---

## 4. Per component

Numbered in the order they were added; §8 gives the order they are built in. Each entry is the §1 plan. "Before code" lists the items that must exist first.

### 4.1 The semantics program: clingo over flattened ODRL (issue #9)

- **Risks.** R4 and R5, surfaced. R2 in its own Kleene evaluation. R9 when it generates its own vectors.
- **Encoding obligations** (`decisions/0009`): `U` is data — fact statuses, deadline comparisons, and witness timeliness arrive as facts; every part carries exactly one of `t/f/u`, enforced by an integrity constraint; Kleene connectives are min/max over `f < u < t`; no negation-as-failure anywhere a status can be unknown; the evaluation layer is stratified Datalog, with choice rules only in the completion and the generator. The 2026-10-10 audit encoding failed all of these.
- **Oracles for the program.** The corpus's positive cases, with disagreements triaged per §6 — its verdicts, and its `verdict_basis` and `eliminated` where a scenario asserts them (`due2-workflows.md` §3.7, #57, #59); the external suites' own answers. For an `Indeterminate`, the corpus asserts little, so the pivotal `unknown` atoms and the `verdict_range` (`decisions/0011`) are checked by a brute-force differential: a Hypothesis test that enumerates the completions in Python, flips each literal alone, and compares the result with the program's. It reads the generated rules, not the driver's facts, and shares only the spec's literal key (`due2-workflows.md` §6.4) with the program (`spikes/clingo-i/tests/test_brute_force.py`). Its own laws: L4 and L5 on generated inputs; the status matrix and Kleene tables as ASP facts, with the one-value integrity constraint making a forgotten rule a loud failure.
- **Driver.** **[D]** (2026-10-16, `decisions/0009`) The Python driver parses the Turtle and makes a purely syntactic flatten of the authored graph to facts — no lifting, no expansion, no DNF, which are the program's rules — and ranks compared values (32-bit integers; `decisions/0009` #4). It is not an evaluator. Because L9 cannot see a driver bug, it is tested on its own: round trip (facts back to a graph isomorphic to the input), invariance under triple order and blank-node labels, and agreement with `tools/check_corpus.py` and `tools/check_odrl22.py` on what it accepts, over the corpus, the vendored policies, and the external suites. Agreement is checked as follows: the driver parses the same files the checkers parse; it flattens and places every file that parses, which is a superset of what either checker accepts; and no file the checkers admit holds a literal the driver cannot place (`spikes/clingo-i/DESIGN.md` § Tests, #46). The driver reads lexical forms as written. The checkers read rdflib's normalised forms, which are lossy, so register #3's shared reader is shared up to that setting.
- **Golden vectors.** The corpus. Occurrence-dependent scenarios (8 cases use recurrence) report `unsupported: recurrence` loudly, not as passes; every other scenario is runnable.
- **Generators.** Coverage targets as choice rules plus constraints, `#minimize` for the smallest witness (§5). Self-generated vectors test other implementations, never the program itself.
- **Done.** Every runnable scenario agrees, or each disagreement has a triage record (§6) that landed as a commit to the case, the spec, or the program.

### 4.2 W1 stage 1: the normaliser

- **Risks.** R1, R6.
- **Before code.** Negative cases in the case format: `expected_rejection` (`conformance/README.md`), with codes from `due2-diagnostics.md`. The rejection codes with no negative case are listed in `conformance/README.md` § Coverage gaps; `odrl-compound-to-atomic-normalization.md` §10 names the stage-1 vectors.
- **Oracles.** `Den` through the lineage bijection (invariant 3). Golden vectors from `odrl-compound-to-atomic-normalization.md` §10.
- **Properties.** Invariants 6 (determinism over permuted triples, JSON-LD order, and blank-node labels), 7 (idempotence), and 10 (locality: an unrelated edit changes no output IRI). Invariant 8 as exact-limit success and limit-plus-one failure.
- **Done.** The minimum suite of `odrl-compound-to-atomic-normalization.md` §10 passes, `Den` agrees on every positive vector and on generated policies, and the formal model's `Den` (§4.8, issue #8) follows as the second, machine-checked oracle.

### 4.3 W1 stage 2: the builder (lifted form to relations)

- **Risks.** R1 (DNF, `xone`, `dprod:not` pushed inward, instantiation), R3 (the canonical-literal key is derived here).
- **Oracles.** `I`, through L9 on generated policies.
- **Properties.** L9. Complement pairs (`eq`/`neq`, `lt`/`gteq`, `lteq`/`gt`, `isAnyOf`/`isNoneOf`) map to one variable with opposite polarity, and identical parts map to one variable, when the parts are completed. An opaque part maps to a variable of its own (`due2-workflows.md` §6.4, `decisions/0016`). The atom-count limit fails before any output.
- **Lineage.** Every atom's lineage names its authored rule, its stage-1 selection tuple, its constraint disjunct, and its parameter binding (`due2-workflows.md` §3.6), which L10 needs.
- **Done.** L9 holds on the `fast` and `nightly` Hypothesis profiles (`ways-of-working.md` §7.2), and the corpus runs through W1 without rejections other than expected ones.

### 4.4 W2: evaluate

- **Risks.** R2 above all, then R7.
- **Golden vectors.** The **status matrix**: for every operator and every fact status (`resolved`, `missing`, `invalid`, `conflict`, `unresolved`), the part's truth value, enumerated exhaustively. A non-`resolved` status gives `U`, with no exceptions (`ways-of-working.md` §5.1). This is the primary defence against R2 and is cheap to make complete. The same for request parameters (absent means `missing`) and for absent parties and targets (`due2-workflows.md` §3.2).
- **Properties.** L2 (an atom's finding is unchanged by other atoms), L3 (prefetch neutrality), L8 (skip soundness). Plan coverage: W2's `read` is within `plan(corpus, request)` for every generated and corpus evaluation (`due2-workflows.md` §3.3). Duty instances and statuses against the `due2-workflows.md` §5.3 table, over generated deadlines and recurrences.
- **Done.** The status matrix is complete and passing, the properties hold, and the corpus's `obligations` agree.

### 4.5 W3: resolve

- **Risks.** R3, R7.
- **Oracles.** A brute-force W3 over every completion of the actual findings (§3), capped by variable count. `I` end to end.
- **Properties.** L4–L7. `verdict.exact = true` whenever the mixed-variable count is at most `max_mixed`, and a fallback verdict that is never definite where brute force says `Indeterminate`. Golden vectors at `max_mixed` and at `max_mixed + 1` (`due2-max-mixed`). For an `Indeterminate` (`decisions/0011`): the `unknown` atoms are exactly those with a pivotal literal, and `verdict_range` equals the least and greatest completion verdict, wherever `exact` is true; past the bound, every `U` atom is named and the range contains brute force's.
- **Abstract model extended.** **[D]** `check_completion.py` models deadlines, violated preconditions, `violations = deny` (fourth phase) and the listed frontier against every completion's (fifth phase). It found no mismatch. `frontier_complete` is computed by bounded enumeration over the relevant unknowns (`decisions/0004`), which the fifth phase checks against the definition, fallback included. Multi-policy conflict under `invalid` is left to the brute-force W3 differential. Nested constraints are left to the brute-force W3 differential and slow `I`.
- **Done.** The differential against brute-force W3 is clean on both profiles; the corpus passes, including `frontier`, `verdict_basis` and `verdict_range`.

### 4.6 Trace and replay

- **Risks.** R6.
- **Properties.** L1: identical trace bytes across tuple-order permutations, `PYTHONHASHSEED` values, and locales, run as a matrix in the PR tier. Replay of every recorded evaluation gives the same digests (`due2-workflows.md` §7). L10 on every generated and corpus evaluation (`due2-workflows.md` §3.7):
  - every reference in the trace resolves in the trace, the evaluation's inputs, or the lineage;
  - each finding is re-derived from its `basis`;
  - every atom in `verdict_basis` and `eliminated` has its findings and an authored source.

  The check is a pure function of the recorded collections, so it also runs over the ledger's recorded evaluations.
  - *Normaliser upgrade.* Replaying recorded evaluations under a new normaliser version is a regression check, outside the ledger: the same inputs giving a different verdict is a defect, or an intended change that carries a decision record. Every changed verdict is reported; the ledger is never written.

### 4.7 Case history: the ledger

- **Risks.** R10, R6.
- **Before code.** A ledger data model at the level of `due2-workflows.md` §3: it is `due2-workflows.md` §7.1 (`decisions/0008`). One case per request; facts, evidence, activations, and evaluations are append-only events on it; an evaluation's SOTW is the case's facts as of `effective_at`; earlier decisions are answered from their recorded evaluation. Exercise events (access taken under a permit) stay out of scope.
- **Oracle.** A from-scratch evaluation over the current inputs. Re-evaluation, whichever trigger is chosen (`due2-architecture.md` §7, issue #14), must agree with it.
- **Properties.**
  - *Replay.* Every recorded evaluation, re-run under its pinned normaliser versions, gives byte-identical traces.
  - *Pinning suffices.* Re-running with the SOTW cut down to the evaluation's recorded reads gives the same trace (a consequence of L3); an evaluation that needs more than it pinned is a defect.
  - *Append-only.* No operation changes an earlier event; re-evaluation adds an evaluation to the case.
  - *Both directions.* Transitions occur in both directions — `Pending` to `Permit` on evidence, `Permit` to `Deny` on a changed fact or policy — and only resolving unknowns, with nothing else changed, never moves one definite verdict to another (L4).
  - *Two clocks.* An as-of query for an earlier decision answers from that evaluation, unaffected by later facts, policy amendments, or normaliser upgrades.
- **Model-based.** A Hypothesis stateful machine (`ways-of-working.md` §7.1) drives event sequences — request, submit evidence, change or resolve a fact, amend a policy, upgrade the normaliser, re-evaluate, query as-of — against a reference model that recomputes everything from scratch. Sequences are also enumerated exhaustively up to a small length.
- **Done.** The stateful machine and the enumerated sequences are clean, and every corpus scenario that awaits a duty has a history case that carries it through to its next verdict. That needs a case-format extension: one case, a sequence of events, an expected verdict per evaluation.

### 4.8 The formal model (issue #70, `decisions/0021`)

The formal model is a small, executable model of due2's semantics, written in a prover. Proofs establish the claims below about it, and a differential compares it with clingo-i and with W1–W3 as each is built. It is an oracle, never a production evaluator, and no code is extracted from it. Claims M, K, F, and W go to the prover; P is a question the spec answers. Which prover is chosen by a spike on claim M, Lean 4 first (§9 #11).

- **Risks.** R3 and R4 above all: each claim below is an argument that a definite verdict is right, and a flaw in one makes a definite verdict wrong. R1 through `Den`, once `Den` moves into the model (#8). R9 in the bounded-exhaustive search, which proves nothing about a shape it never reaches (#77 is such a case).
- **Claims.** Each is a sentence of the spec, or a question one of its records leaves open. Every claim gets a small Alloy 6 model of its own and the bounded-exhaustive search over clingo-i first. It goes to the prover only after both have run at stated bounds without a counterexample.

  | Claim | Statement and source | Evidence |
  |---|---|---|
  | **M**, monotonicity | Under all three strategies and the default combination, "the verdict is monotone in every finding", so the two extreme completions bound every completion's verdict (`due2-workflows.md` §6.4). The proof's last case extends this to `violations = deny` | The proof by cases in `due2-workflows.md` §6.4. `check_completion.py`'s first, third, and fourth phases, 50,000 cases each, against its abstract model rather than the semantics clingo-i implements |
  | **K**, the completion key | Identical completed parts share one variable, and complementary ones share it with opposite polarity; an opaque part is a variable of its own (`due2-workflows.md` §6.4, `decisions/0012`, `decisions/0016`). Two claims: the key never merges parts whose truth values can differ under a value that fits (soundness), and the parts it leaves independent can only widen a verdict to `Indeterminate`, never make it a wrong definite one (one-sidedness). The key is not complete: `x ≤ 5` and `x > 7` stay independent (#25) | The argument in `due2-workflows.md` §6.4 and `decisions/0012`; corpus cases such as `due2-xone-unknown`. clingo-i's brute-force differential shares the key, so it is no evidence for it |
  | **F**, frontier relevance | For a definite `Pending`, only the unknowns of uncertain candidates and of `U` prohibitions can change the frontier: "no other unknown can move the frontier while the verdict stands" (`due2-workflows.md` §6.4, `decisions/0004`) | `check_completion.py`'s fifth phase: 942 definite `Pending` instances of 50,000, against the same abstract model |
  | **W**, the basis waiver | A definite `Permit` or `Deny` with an empty basis has a `U` finding that reads a paired leaf, whose operand is `unresolved` and is listed as an unknown part; so `tools/check_corpus.py` may waive the basis check exactly then (`spikes/clingo-i/DESIGN.md` § `resolve.lp`) | The argument in `DESIGN.md` and one explicit case. A search of 6,000 cases never reached the shape (#77) |
  | **P**, the listed frontier under unknowns | An open question, not a claim: the listed frontier (`due2-workflows.md` §6.3) can omit a route that every completion offers, because no single permission gives it. Should `due2-workflows.md` §6.3 list such a route? (`decisions/0019`) | Two clingo-i tests, named in `decisions/0019` |

  The laws L1–L10 (`due2-workflows.md` §8) also get Alloy models, as a test of adequacy rather than of the model (`decisions/0021` #6).
- **Before code.** The claims above. Each is restated in the model's terms and pinned to the spec version it states: a proof that outlives its spec version proves the previous one.
- **Oracles for the model.** clingo-i, through the spike harness (`spikes/README.md`), on the corpus and on the enumerated and generated vectors. The corpus's hand-derived verdicts. Within the model, the definition at the top of `due2-workflows.md` §6.4, every completion enumerated, beside the two-extreme computation: M is the theorem that they agree. The model shares with clingo-i only the prose and its reading (§3).
- **Properties.** The claims, as theorems. Faithfulness: each definition in the model, and each rule block in clingo-i's `lp/`, names the spec section it encodes, and a test checks that each name resolves. clingo-i's section citations are prose in `DESIGN.md` and in comments, and the faithfulness test is a sub-issue of #70.
- **Golden vectors.** The corpus scenarios within the layers modelled; the two shapes of `decisions/0019`; the empty-basis case of #77.
- **Generators.** The bounded-exhaustive enumerator and the generators of §1.1 and §5 (#42, #44). Each claim's hard shape is reached in a stated share of draws, and a test asserts the share (#77).
- **`check_completion.py`.** Its abstract model is the common mode of the evidence for M and F until the formal model exists. It keeps running until the model's differential covers its five phases, and then it retires.
- **Done.** M is proved in the chosen prover over the finding and resolution layers, and the spike's result is recorded as an amendment to `decisions/0021`. K, F, and W are each proved, or refuted with the spec edited (§6). P is settled by a spec edit or a decision record. The model runs under the spike harness and agrees with clingo-i on every corpus scenario within the layers it models and on the enumerated vectors at stated bounds. The proofs and the differential run in the slow tier (§7).

---

## 5. Generators **[O]** (coverage check **[D]**, 2026-10-11)

The Hypothesis strategies for policies, requests, and SOTWs are shared by every component in §4. They are a first-class artefact and get reviewed like spec text, because a blind spot in them (R9) silently weakens every property at once.

Requirements:

- **Biased towards unknowns.** Draw fact status uniformly over all five statuses rather than mostly `resolved`. A generator that rarely produces `U` cannot find R2 or R3.
- **Correlated by construction.** Reuse operands deliberately: identical parts, complement pairs, and one fact read both ways across rules. Mixed variables appear only when a generator aims for them.
- **Structurally complete.** Nested `and`, `or`, `xone`, and `dprod:not`; shared duties; guarded duties; deadlines and recurrences; all three conflict strategies; `violations = deny`.
- **Valid and invalid.** Each generator has a twin that produces near-miss invalid inputs — one rule left unnamed, an operand unbound, a cycle, a limit exceeded by one — with the expected rejection.
- **Shared with the enumerator.** The bounded-exhaustive enumerator of §1.1 and the Hypothesis generators draw from one description of the input space, so the two cannot drift apart. Over clingo-i, that description is the space programs in `spikes/clingo-i/tests/space/` (`spikes/clingo-i/DESIGN.md` § Tests), and the spike's own Hypothesis generators are written separately; both run against one oracle and one list of shapes, so a shape that the generators, or the spaces at their slow bounds, stop reaching fails a test. The production evaluator's Hypothesis strategies must draw from the space programs.
- **ASP-generated [D]** (`decisions/0009`). Coverage targets as choice rules plus constraints over the same facts the program consumes; `#minimize` yields the smallest witness — stronger than generate-and-filter. Generated vectors test other implementations, never the generator (§4.1).
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
| Every commit | The commands in `README.md` § Verify: four checkers, plus type checking and lint |
| PR | The above, plus: the corpus through every backend, including `I`; the status matrix and Kleene tables; bounded-exhaustive enumeration at small bounds; Hypothesis `fast` for L1–L10 and the stage-1 invariants; the L1 determinism matrix |
| Slow | Bounded-exhaustive enumeration at full bounds; Hypothesis `nightly`; the brute-force W3 differential at larger sizes; mutation testing on W2, W3, and the builder; the formal model's proofs and its differential (§4.8). Results feed the ratchet, not the gate |

---

## 8. Sequence

1. The open items of §9. Row 10 is set by measurement at step 5, and row 11 by the prover spike at step 6.
2. The case-format extension for negative cases (`expected_rejection`, §4.2).
3. The status matrix and Kleene truth tables, as data (ASP facts, `decisions/0009`). They are spec as much as tests, and `I` uses them first.
4. Slow `I`, the clingo semantics program (issue #9, `decisions/0009`): the driver and its syntactic flatten, the one-value integrity constraint, then every runnable corpus scenario, triage per §6. Fast mode (`due2-workflows.md` §6.4's computation) follows, differentially against enumeration.
5. The input-space description, the bounded-exhaustive enumerator, and the generators (§1.1, §5), with the coverage histogram, first over clingo-i (#42, #44).
6. The formal model (§4.8, `decisions/0021`): an Alloy model per claim and the bounded-exhaustive search over clingo-i, then the prover spike on M.
7. The W2/W3 backend bakeoff (`decisions/0006`): relation-level vectors (#36, #37), the brute-force W3 (#38), then Clingo (#41) and Elixir (#40), each gated as in §4.4 and §4.5 as far as the vectors reach. The Python backend (#39) is deferred, not withdrawn: it may enter when the production evaluator is written (`decisions/0009`).
8. W1 stage 1 with the Python `Den` oracle; the formal model's `Den` follows (issue #8).
9. W1 stage 2, gated by L9 against `I`.
10. The surviving W2/W3 backends on the full corpus through W1, completing the §4.4 and §4.5 gates.
11. The ledger (data model in §4.7), gated by the stateful machine.

---

## 9. Open decisions register

Rows keep their numbers, because issues and other documents cite them. Each open row has an issue; a resolved row leaves the table and is stated below it.

| # | Decision | Section | Issue | Blocked on |
|---|---|---|---|---|
| 11 | The prover for the formal model | §4.8 | #70 | A spike: Lean 4 first, Isabelle/HOL optional (`decisions/0021` #4); the result is an amendment to that record |

Rows 1–10 are resolved, each where its section states it:

- **1.** Strategy before code is a standing rule (§1; `CLAUDE.md`).
- **2.** Oracles implement definitions, and `I` completes unknowns by enumeration under a cap (§3). Slow `I` comes first and fast `I` (`due2-workflows.md` §6.4's computation) later, the two differentially tested. The vehicle is the clingo program, whose slow mode is answer-set enumeration under the variable cap (`decisions/0009`).
- **3.** `I` and W1 share only the Turtle reading (§4.1, `decisions/0009`). The driver's flatten is syntactic, the lifting is the program's, and the driver is tested on its own.
- **4.** Negative cases are `expected_rejection` with codes from the diagnostic registry (§4.2, `due2-diagnostics.md`).
- **5.** `check_completion.py` covers `violations = deny` and `frontier_complete` (§4.5). Multi-policy conflict under `invalid` is left to the brute-force W3 differential, and nested constraints to it and slow `I`.
- **6.** The generator coverage histogram is a failing check (§5).
- **7.** The disagreement protocol is §6.
- **8.** The critical features are atomization, evaluation, and case history, tested bounded-exhaustively, by generation, and differentially (§1.1).
- **9.** The ledger data model is `due2-workflows.md` §7.1 (§4.7, `decisions/0008`).
- **10.** The enumeration bounds are measured per input space and tier, not guessed (§1.1): the PR bound keeps README § Verify near a minute on ten cores, and the slow bound finishes in about ten minutes there. clingo-i's bounds, for evaluation, are in `spikes/clingo-i/DESIGN.md` § Tests (#42). W1's and the case history's follow the same rule.
