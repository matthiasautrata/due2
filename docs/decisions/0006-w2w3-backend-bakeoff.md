# 0006 — W2 and W3 are built as a bakeoff: Python, Elixir, Clingo, under one conformance suite

**Status:** Decided, 2026-10-16; superseded by `decisions/0027` (the bakeoff ends unrun; the W2/W3 language is #104), except for the relation-level input (item 3), the gate (item 4), and the vectors, which gate the W2/W3 evaluator
**Context documents:** `decisions/0002` (#1, #5, #8) · `ways-of-working.md` §10 · `due2-architecture.md` §10 · `correctness-strategy.md` §3, §4.4, §4.5, §8 · `due2-workflows.md` §3, §5, §6 · issues #3, #16

## Question

`decisions/0002` chose the implementation of W1 by risk. W2 and W3 inherited Python by default. `ways-of-working.md` §10 keeps a second backend as an option, and the conformance suite is backend-parameterised from day one so that the option stays cheap. Which implementation should build W2 and W3? Decide on evidence, not by default.

## Decision

1. **Three implementations of W2 and W3 are built and compared.** Each tests a hypothesis the others do not:

   | Backend | Hypothesis |
   |---|---|
   | **Python** | The documented path. A direct implementation of workflows §5–§6 is sufficient. It is also the differential partner of the others. |
   | **Elixir** | Pattern matching over tagged tuples is a direct, reviewable rendering of findings, statuses, and verdicts. The BEAM is the natural home of the impure shell around them (plan, fetch, record, re-evaluate: workflows §1, §3.3); that is measured later, with the shell. |
   | **Clingo** | The carve-out of `decisions/0002` #5, exercised. Can a declarative encoding keep `U` distinct from `F` (the 2026-10-10 audit found negation-as-failure collapsing them) and compute §6.4's completion? The cost of the encoding is itself a result. |

   Kotlin stays set aside (`decisions/0002` #8): its hypothesis, typed exhaustive matching, overlaps Python under strict typing and Elixir's matching.

2. **Scope.** W2 and W3 only: pure functions over the relations of workflows §3.1–§3.4, producing the trace of §3.5. W1 and the oracles stay Python (`decisions/0002`). No backend enters the runtime by this decision; adoption needs its own record.

3. **Input.** Relation-level vectors: corpus, request, SOTW, and config written directly as relations, with the expected trace. The bakeoff therefore runs before W1 exists. The vectors need a concrete encoding of collections (workflows §2, issue #3); the bakeoff is that decision's first consumer, and it is settled before any vector is written.

4. **Gate.** Correctness first, identical for every backend:
   - the status matrix and the Kleene tables (`correctness-strategy.md` §4.4);
   - the explicit `Indeterminate` vectors (`due2-architecture.md` §10);
   - the relation-level cases, against the brute-force W3 as oracle (`correctness-strategy.md` §3);
   - L1–L8 wherever a property can be checked against the backend;
   - trace equality across backends: the same evaluation gives the same canonical trace bytes (L1), checked in differential mode.

   A backend that fails a vector fails the gate. A vector it cannot express without changing semantics is a finding, recorded with the vector; it is never a spec change.

5. **Scoring**, among the backends that pass the gate, in this order:
   1. trace and basis fidelity: `basis`, `read`, `eliminated`, `verdict_basis` complete and exact;
   2. how `U`, fact statuses, and the five verdicts are represented: native, or encoded;
   3. size and reviewability of the core;
   4. cost of §6.4: the two extremes, mixed-variable enumeration, and `frontier_complete`;
   5. performance at realistic volume, measured as `ways-of-working.md` §10.4 prescribes, last.

6. **Sequence.** `correctness-strategy.md` §8 gains the bakeoff as a step after the status matrix and slow `I`, before W1. W1 then follows unchanged, and the surviving backends run the full corpus through it.

## Why

- **The hot stage is where language is cheapest to choose.** `ways-of-working.md` §10.1: language performance and choice matter only there, and correctness is least at risk there. The comparison costs little beyond what the backend-parameterised suite (§10.2 #3) already demands.
- **A bakeoff turns priors into results.** The clingo audit is a prior about one encoding. Elixir has never been examined. Under one gate, each hypothesis is either confirmed or refuted by vectors, not argued.
- **Relation-level vectors decouple evaluation from normalisation.** W2 and W3 can be built and judged while W1, the riskiest step, is still being specified and verified, and a W1 defect cannot be mistaken for an evaluator defect.

## Consequences

- `decisions/0002` #1 holds until an adoption record: the bakeoff's backends live outside the runtime.
- `ways-of-working.md` §10.3's ordering rule is unaffected: the bakeoff measures and adopts nothing.
- Issue #3 (canonical encoding) becomes a prerequisite; issue #16 (execution target) gains evidence.
- Work items, to be filed as issues: the encoding (#3), the relation-level vector format in `conformance/README.md` (#36), the first vector suite (#37), the brute-force W3 (#38), and one item per backend: Python (#39), Elixir (#40), Clingo (#41).

**Note (2026-10-16):** since `decisions/0009` the L9 oracle is a clingo program, so #2's "the oracles stay Python" no longer covers it; the brute-force W3 (#38) remains this bakeoff's oracle. Clingo (#41) and Elixir (#40) run first; the Python backend (#39) is deferred until the production evaluator is written. The gate and scoring are unchanged.

## Revisit when

- Only Python passes the gate: close the bakeoff, and record why.
- A backend passes but its trace differs: that is a defect in a backend or an underspecification in workflows §3.5. Triage it per `correctness-strategy.md` §6 before scoring.
- The shell is specified: extend Elixir's evaluation to the shell, its stronger hypothesis.

**Note (2026-10-16, `decisions/0010`):** scoring criterion 1, trace and basis fidelity, is checked as law L10 (explicability, workflows §3.7, §8) over each backend's traces. Each backend also has to pass the corpus's authored-level `verdict_basis` and `eliminated` (#57).
