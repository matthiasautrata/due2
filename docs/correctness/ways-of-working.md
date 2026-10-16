# Ways of Working — Correctness Discipline for Python

**Status:** Draft v0.3
**Scope:** Python services and libraries, with particular attention to decision/evaluation kernels where semantics are load-bearing.

**Changes, 2026-10-16:** §13's tracking narrowed to the picks still open (#4, #8); the register-tracking convention is stated once in `due2-architecture.md` §11. New §7.4: one shared suite for every spike (`spikes/README.md`); §11's basedpyright scope extended to `tests/`.

**Changes in v0.3:** new §2.4 — RDF at the boundary: parse and emit at the edges, plain frozen structures everywhere between.

**Coherence updates, 2026-10-10:** §9's blocker resolved — Dafny is installable here, and `decisions/0002` records the track (register #9, #12); §7.1's preservation property restated as the refinement of `due2-workflows.md` §8 L9, whose L9 oracle is a direct interpreter over the lifted (authored) form.

**Changes in v0.2:** §2.3 (where exhaustiveness actually pays), new §5.1 (absent / unknown / false), §7.1 (semantic-preservation property), §9 (verification retargeted at the normaliser), §10 (rewritten around the two-stage split; Rego/OPA added), §11 (generated-code rule generalised), §13 (register extended). Companion document: `due2-architecture.md`.

Each item is marked:

- **[D]** Decided — normative, applies now
- **[O]** Open — alternatives listed, decision pending
- **[F]** Future — depends on an external unknown

---

## 1. Premise

Python's type annotations are erased at runtime, no checker is sound, and `Any` is contagious. We therefore do not pretend to have verification. We build **layered defence**: several independent mechanisms, each cheap, each catching a different defect class.

The corollary is honesty about the ceiling. This discipline makes defects *rare*. It does not make classes of defect *impossible*. Where a guarantee is genuinely required, see §9.

Two rules govern everything below:

1. **Structural mechanisms are unconditional.** Types, immutability, boundary validation cost nothing at review time and are always on.
2. **Analyses that consume wall-clock are tiered.** See §8. A gate nobody waits for is a gate nobody runs.

---

## 2. Style: functional core, imperative shell **[D]**

The single highest-leverage convention. Effects live at the edges; the middle is pure.

**Core (pure):**

- Total functions over immutable data. No I/O, no clock, no randomness, no global state.
- Return values, don't mutate arguments. A function that takes a list and returns `None` is a smell.
- `@dataclass(frozen=True, slots=True)` by default. Mutable dataclasses require justification.
- Prefer transformation over accumulation: build a new value rather than mutating one in a loop. Comprehensions and `itertools` over `for` + `append` where it doesn't hurt readability.
- Pass dependencies (clock, ID generator, config) as arguments. This is what makes the core testable without mocks — and mock-heavy tests are a symptom that the shell has leaked into the core.

**Shell (effectful):**

- I/O, persistence, network, logging, process boundaries.
- Thin. It parses input, calls the core once, and writes the result. If there is branching logic in the shell, it belongs in the core.

**Why this matters beyond taste:** every tool in §6 and §7 works dramatically better on pure functions. Property tests need no fixtures. CrossHair *only* works on side-effect-free code. Contracts are meaningful. Concurrency questions disappear. This convention is the precondition for the rest of the document.

### 2.1 Immutability details **[D]**

- `Final` for module-level constants; `Sequence`/`Mapping`/`AbstractSet` in signatures rather than `list`/`dict`/`set` where the callee does not own the value.
- Default arguments are never mutable containers.
- For genuinely shared structures where copying is too expensive, use a persistent-structure library rather than reintroducing mutation. **[O]** — candidates: `immutables` (HAMT, small, CPython-adjacent) vs `pyrsistent` (broader API, heavier). Decide when we hit the first real case; do not adopt speculatively.

### 2.2 Error handling **[D]** (2026-10-11, provisional, §13)

Failures come in three kinds, and each is handled one way only.

| Kind | Example | Handling |
|---|---|---|
| **An expected outcome** | Unknown data at request time | Not a failure. `Indeterminate` is a verdict, a value like any other (§5.1). |
| **An expected failure** | A policy W1 rejects; a malformed request at the boundary | `Result[T, E] = Success[T] \| Failure[E]`, hand-rolled frozen dataclasses, matched exhaustively (§2.3). The cause is data, e.g. W1's diagnostics (`due2-diagnostics.md`). |
| **Can't happen** | A contract violation, a broken invariant, `assert_never` reached, an I/O fault | Let it crash. The exception propagates, and the core has no handler for it. |

- **`Result` only where failure is expected.** A function that cannot fail in an expected way returns its plain value. Kleene `and` returns a truth value, not `Success` of one. Its signature then says that any failure is a crash, and the checker keeps the two kinds apart.
- **No library.** The two dataclasses and a type alias are the whole of it. A stage that must collect every error, such as W1's (diagnostics §1), runs its checks and folds the failures into one `Failure`. It does not chain calls that stop at the first error.
- **One handler, at the shell.** In the Erlang sense of "let it crash", the shell is the supervisor. It catches what escapes the core, logs it in full with the traceback, and answers with an error outcome, never a verdict (`due2-workflows.md` §7). Then it takes the next request. The core is pure, so there is no state to restart. Restarting means handling the next request. This is the one `except Exception:` allowed without a re-raise.
- **Loud, never hidden.** A crash is never turned into `Indeterminate`, a default verdict, or an empty result. Doing that would make a bug look like missing data in the trace.

Exceptions are never control flow in the core, and no other bare `except:` or `except Exception:` without a re-raise is allowed.

### 2.3 Closed unions and exhaustiveness **[D]**

Model domain alternatives as closed unions of frozen dataclasses, matched with `match` and terminated by `assert_never(x)` in the default arm. This is the nearest Python gets to a non-exhaustive-match error: adding a variant makes every incomplete match a *type error*, statically, before runtime.

This is mandatory for any union representing domain semantics. It is the cheapest real guarantee in the document.

**Where this actually pays.** A pipeline that normalises a rich input into a flat regular form has two very different halves. The stage *after* normalisation operates on uniform records and tends to be a filter and a fold — closed unions buy little there beyond the verdict type. The stage *before* it is a recursive transformation over an inductive type with many cases, and that is where an added variant must not be silently ignored. When choosing where to spend review attention and specification effort, follow the case analysis, not the line count. See `due2-architecture.md` §3–§4 for the worked instance.

### 2.4 RDF at the boundary **[D]**

RDF is a wire format, not a working representation. It appears in three places: parsing authored policies and profile modules at the input boundary; emitting the canonical N-Quads artifacts and digest terms (normalisation spec §4, §5.2) at the output boundary; and nowhere between. Every transformation and every evaluation runs on the plain frozen structures of §2 — the lifted tree inside W1 stage 1, relations of tuples whose fields are terms everywhere else (`due2-workflows.md` §2, §4) — not a graph API.

- **One adapter module owns the library.** A third-party RDF library may exist inside it; its types, its `Any`s, and every `# type: ignore` stay there (§3). Nothing RDF-shaped escapes. The acceptance test is a grep: no RDF import outside the adapter and the test tree.
- **The lift is immediate and lossless by construction.** The parsed graph becomes typed trees in the same call that reads it. The input profile is what makes that possible: anonymous structure is a forest hanging from named anchors, rule references are acyclic, IRIs are never dereferenced, there are no named graphs, and output has no blank nodes (normalisation spec §3–§5) — so no graph algorithm is needed after the door. The lift owns the term model — IRI, literal `(lexical, datatype[, language])`, list cells — which is the real, bounded cost of this rule.
- **Serialisation is a pure function from the internal structures** — term rendering and a sort, not a library graph re-serialised. Digests and canonical bytes come from these renderings, which is what keeps them deterministic by construction.
- **The library's remaining job is the slow tier.** Property tests round-trip the lift against the library's own parse — isomorphic inputs, equal canonical bytes (§7.3 ratchet). A discrepancy is a lift bug.

What this buys: exhaustiveness where it pays (§2.3) instead of `isinstance` chains against open graph APIs; a hot path free of graph indexes (§10.1); canonical-byte determinism for free; and a second backend that ports a parser, not an RDF stack.

---

## 3. Banning `Any` **[D]**

`Any` disables checking silently and spreads through inference. It is the primary way a "typed" codebase turns out not to be.

- `Any` is prohibited in signatures of first-party code. Enforced via `disallow_any_explicit` and `warn_return_any`.
- Where a value is genuinely unknown, use `object` and narrow explicitly. This forces a check instead of skipping one.
- Untyped third-party libraries: wrap in a first-party typed adapter module. `Any` may exist *inside* that module; it never escapes it. The adapter is the only place `# type: ignore` is acceptable, and every one carries a specific error code and a comment.
- `cast()` is an assertion without evidence. Allowed only in adapters, adjacent to a runtime check that establishes the claim.

Replacements that carry meaning: `NewType` (zero runtime cost, nominal — use for IDs and units so `PolicyId` and `SubjectId` cannot be swapped), `Protocol` (structural interfaces, no inheritance coupling), `Literal`, `TypedDict`, PEP 695 generics, `@final`.

---

## 4. Static type checking **[D]** (provisional, §13)

Strict mode is non-negotiable; the tool is not yet decided.

| Tool | Conformance | Speed | Note |
|---|---|---|---|
| Pyright / basedpyright | ~98% | fast | Best narrowing and inference; strongest correctness signal |
| Pyrefly (Meta) | ~88% | very fast | 1.0 May 2026; auto-converts existing mypy/pyright config |
| mypy | ~58% | slow | Mature plugin ecosystem; 2.0 added parallel checking |
| ty (Astral) | ~53% | fastest | Alpha. Unimplemented and clean look identical in CI — unsafe as a gate |

**Recommendation:** a fast checker in the editor, a high-conformance checker as the CI gate. They need not be the same tool.

**[D]** (2026-10-11, provisional) **basedpyright in strict mode**, in the editor and as the gate. One tool means the editor and CI never disagree. Pyrefly can join the editor later if speed matters. Revisit if the code moves to an environment that approves a different checker (§13).

Adoption on existing code: enable one strict flag per sprint rather than a big-bang migration. New modules start strict.

---

## 5. Boundaries: parse, don't validate **[D]**

All external input — HTTP, files, queues, database rows, config — is parsed into a typed domain object at the boundary. Past that point, types are trusted and **not re-validated**. Defensive re-checking inside the core is redundancy, and redundancy hides which layer owns the invariant.

**[D]** (2026-10-11, provisional) **msgspec**, for the JSON boundary: requests, state of the world, case files. It decodes straight into the frozen dataclasses of §2, so the domain model does not depend on it. RDF has its own adapter (§2.4). The alternatives considered:

- **msgspec** — fastest, strict by default. Best fit for wire formats and high-volume paths.
- **pydantic v2** — richest constraint vocabulary. `Annotated[int, Field(ge=0)]` gives crude refinement types at the edge. Heavier; couples domain models to the library.
- **attrs + cattrs** — most composable, least magic, cleanest separation of domain model from serialisation.

Selection criterion: if the domain model should stay library-agnostic, attrs+cattrs. If throughput dominates, msgspec. If constraint expressiveness dominates, pydantic.

**Runtime enforcement:** `beartype` via import hook enforces existing annotations at near-constant cost. **[D]** (2026-10-11, provisional) Test environments only: on in unit, integration, and system tests, optional in UAT, never in production.

### 5.1 Absent, unknown, and false **[D]**

Three states are routinely conflated by host languages and query engines, and the conflation is silent:

- **Absent** — the field is legitimately not specified, and absence has a meaning (an unconstrained target, no named assignee).
- **Unknown** — the value could not be resolved. A lookup failed, a source was unavailable, a type was incomparable.
- **False** — the value was resolved and the predicate does not hold.

Every runtime we might generate into collapses unknown into false by default: SQL drops `UNKNOWN` rows in `WHERE`, Rego treats an unresolved reference as `undefined` so the rule simply does not fire, and SPARQL filter semantics make evaluation errors behave as false. Three independent targets making the same choice is not a coincidence; it is the default we must override every time.

**Rule:** in any system where a decision has consequences, unknown is modelled as a distinct value and surfaces as a distinct outcome. It is never inherited from the host language's null handling, and it is encoded explicitly in any generated artefact. A denial produced by an unresolvable operand and a denial produced by a rule must be distinguishable in the record after the fact.

**Test obligation:** the conformance suite (§10) carries cases where an operand is unresolvable, and asserts the distinct outcome on every backend. This is the property most likely to be silently lost in a port.

---

## 6. Contracts **[D]**

Design-by-contract is a first-class part of this discipline, not an optional extra. Contracts are the specification; tests are samples of it.

**Tool:** **[D]** (2026-10-11, provisional) `icontract` — `@require`, `@ensure` (with old-value capture), `@invariant`. The first module to use it is the Kleene truth tables, as the trial. `deal` was the alternative; it bundles a linter and a Z3-backed solver for simple functions, but `icontract` has the stronger ecosystem (`icontract-hypothesis`, CrossHair integration, `pyicontract-lint`).

**What to contract:**

- Every public function of a kernel/evaluator module.
- Class invariants on any type with a non-trivial well-formedness condition.
- Not trivial type restatements — the checker already does that. Contract the things types *cannot* express: ordering, non-emptiness under conditions, relationships between arguments, idempotence, monotonicity.

**Why contracts earn their place here:** they are the connective tissue between layers. `icontract-hypothesis` derives property-test strategies directly from preconditions, so a contract generates tests for free. CrossHair reads the same contracts and attempts to refute them symbolically. And if we ever get Dafny (§9), the contracts are already the specification, written down and reviewed. One artefact, four consumers.

**Runtime cost:** contracts are enabled in dev and test unconditionally. **[D]** (2026-10-11, provisional) In production, preconditions stay on and postconditions and invariants are off. A wrong policy decision costs more than the check.

---

## 7. Testing

This section lists the instruments. Which instrument guards which risk in due2, what each oracle is independent of, and what must exist before each component is coded: `correctness-strategy.md`.

### 7.1 Layers **[D]**

- **Unit tests** — pytest. Example-based, fast, deterministic. Cover the specific and the regression-worthy.
- **Property tests** — Hypothesis. The primary correctness instrument for the core. Test algebraic laws: idempotence, commutativity where claimed, round-tripping (parse ∘ render = id), invariant preservation, monotonicity.
- **Semantic preservation** — where a pipeline rewrites a rich input into a normal form before acting on it, the load-bearing property is that the rewrite changes nothing observable: for all inputs `p` and requests `r`, `interpret(normalise(p), r)` equals `interpret_directly(p, r)`, provided unknowns are completed over literals rather than over the normal form's findings — otherwise the rewrite's own correlations (a split guard and its negation) are lost and only refinement holds (`due2-workflows.md` §6.4, §8 L9: refinement on 2026-10-10, equality again in v0.6). This is worth more than any number of tests against the normal form itself, because it is the only check that the rewrite has not quietly changed meaning. It requires maintaining a direct interpreter as a specification artefact, which is a real cost and a justified one.
- **Model-based / stateful** — Hypothesis `RuleBasedStateMachine`, comparing an implementation against a simple reference model. For an evaluator, the declarative semantics *are* the model; this is worth more than any amount of example-based testing.
- **Differential** — where two implementations exist (reference vs optimised, Python vs extracted backend), cross-check them on generated inputs. See §10.
- **Mutation testing** — `mutmut`. Coverage measures execution; mutation measures whether the tests would *notice* a bug. Scoped to kernel modules only; unaffordable repo-wide.

### 7.2 Hypothesis profiles **[D]**

- `fast`: `max_examples=25`, `derandomize=True`. Deterministic — a gate that fails one PR in twenty on seed luck trains people to hit rerun, which destroys the signal.
- `nightly`: `max_examples=5000`, random seed, `deadline=None`.

### 7.3 The ratchet **[D]**

Slow tools are **finders, not gates**. When nightly Hypothesis, CrossHair, or mutation testing produces a counterexample, the output is a concrete failing input. That input is committed as an `@example(...)` case and becomes a millisecond-fast deterministic test in the PR tier permanently.

The fast suite therefore accumulates every hard case the slow tools have ever found. Hypothesis's own example database does part of this, but it is local and ephemeral — committing explicit examples is what makes it shared and durable.

A surviving mutant is not a build failure. It is a ticket that says "this line has no assertion behind it." The fix lands in the fast tier.

### 7.4 One suite, many spikes **[D]** (2026-10-16)

Candidate implementations (the oracle `I`, the bakeoff backends of `decisions/0006`) are tested by one Python suite, written before them and shared by all. The vectors and expected results are the corpus (`conformance/`), pinned in git. Each candidate is a separate spike under `spikes/` that runs as a subprocess and speaks a JSON-lines protocol: text in, text out, so a spike in any language faces the same tests. The harness measures latency identically for every spike. Each spike commits a scorecard (its last full run) and an append-only journal: effort, attempts, rewrites, bugs, and checker diagnostic counts over time. Code and scores are compared at the end. The contract is in `spikes/README.md`, and the harness in `tools/harness/`. `uv run pytest` alone runs only the harness's self-tests, which pin both ends: a backend that echoes the expected results passes every vector, and one that returns nothing fails every vector.

---

## 8. Tiering **[D]**

Placement is *tool × scope*. Scope is the cheaper lever: mutation testing is unaffordable repo-wide and comfortable on one module.

| Tier | Budget | Contents | Gate? |
|---|---|---|---|
| Editor | < 1s | ruff, fast type checker, LSP | No — feedback only |
| Pre-commit | < 10s | ruff `--fix`, format, type-check changed files | Yes |
| PR | < 5 min, deterministic | full strict type check, unit tests, Hypothesis `fast`, beartype active, contracts on | Yes |
| Slow | unbounded | Hypothesis `nightly`, CrossHair on pure predicates, mutation on kernel, dependency audit | No — feeds the ratchet |

**Pre-commit hard rule:** anything over ~10 seconds gets bypassed with `--no-verify` and buys nothing. No tests in pre-commit.

**PR tier hard rule:** same commit, same result, always. Non-determinism at this tier is worse than absence.

**[O] Slow-tier trigger:** nightly cron vs merge-queue entry. Merge-queue gives slower feedback on a busy repo and faster on a quiet one, and never leaves a bad commit on main overnight. Under a few merges a day, merge-queue wins. Decide by observed merge frequency.

---

## 9. Verification track **[D]** (Dafny confirmed installable 2026-10-10; see `decisions/0002`)

Everything above reduces defect probability. None of it produces a proof. Where a control function needs the word "verified", the route is a verification-aware language with extraction.

**Dafny** is the candidate. Specifications are written as pre/postconditions in the language itself, checked by Z3, then compiled to a target language.

**What to point it at.** The instinct is to verify the decision function. In a two-stage pipeline that instinct is wrong. Once inputs have been rewritten into a flat normal form, the decision function is a filter and a fold — small enough to review by eye and cheap to test exhaustively over a generated corpus. The transformation that produced the normal form is where the case analysis lives, where changes land, and where a defect is silent rather than loud, because a mis-normalised policy still evaluates cleanly and simply means something else. **Verification effort follows the case analysis.** The highest-value specification target is the semantic-preservation property of §7.1, not the evaluator.

Three usage modes, ranked by value/cost:

1. **Oracle only (recommended entry point).** Extract to Python, never deploy it. Use it as the reference implementation in differential Hypothesis tests against the production implementation. Machine-checked ground truth with zero interop, runtime, or performance cost; the generated code lives in the test tree. Reversible, and it reveals the true proof cost before any architectural commitment.
2. **Ship extracted Go.** Go is a well-supported backend and an admissible language here. Python becomes a client over a process boundary.
3. **Ship extracted Python.** Viable but the weakest backend (still officially "under development"). Generated code needs the Dafny Python runtime on `PYTHONPATH`; `seq`/`map`/`set` arrive as runtime wrapper types, not `list`/`dict`; names mangle without `{:extern}` pinning. Requires a hand-written typed adapter. Treat the generated package as a vendored binary artefact — never edited, regenerated only.

**Also to price:** the Rust backend. Extracted Rust + PyO3 gives far better in-process Python interop and performance than the Python backend. Relevant to our crate-approval constraint: we need the toolchain, and if serialisation stays on the Python side the dependency surface is roughly `dafny_runtime` + `pyo3`/`maturin` rather than a serde tree. **[O]** — confirm current Rust-backend maturity.

**What to extract:** pure total functions over inductive datatypes. Not parsing, not I/O, nothing effectful. Subset types (`type Nat = x: int | x >= 0`) are where we get the refinement types Python cannot express.

**Operational cautions:**

- Cost is in the proofs, not the codegen. Loop invariants and quantifier triggers dominate. Budget 3–10× on the verified portion, front-loaded.
- Pin Z3 and use resource limits (`--resource-limit`) rather than wall-clock timeouts, or verification becomes machine-dependent and CI goes flaky in a way that is very hard to defend to a control function.

**Resolved 2026-10-10** (`decisions/0002`, with the full alternatives review in `implementation-alternatives.md`): Dafny is installable here — Homebrew ships Apple-Silicon bottles (4.11.0, .NET 8 + Z3) — so the oracle mode below is unblocked. The recommendation stands: oracle only, scoped to the `Den` oracle and the stage-1 expansion functions, with OCaml+Why3 as the designated upgrade and Lean as the recorded fallback for the preservation metatheorem.

---

## 10. Execution stages and backends **[O]**

### 10.1 The two stages are not the same problem **[D]**

Systems of this shape divide into an offline transformation and a hot evaluation, and the two have different constraints. Conflating them produces a false performance argument.

| | Offline stage | Hot stage |
|---|---|---|
| Runs | Once per input version | Per request |
| Output | An auditable artefact, checked rather than trusted | A verdict |
| Dominant risk | Silent semantic change | Latency |
| Budget | Effectively unbounded | Tight |
| Implication | Contract-heavy, property-tested, specification-adjacent. Language performance is irrelevant. | Simple enough that language choice does not affect correctness |

The consequence is that **language performance arguments apply only to the hot stage, and the hot stage is the half where correctness is least at risk.** Any proposal to change implementation language must say which stage it addresses.

### 10.2 Preserving the option **[D]**

We do not choose a second backend now. We keep the choice cheap. Three commitments do that, and each is justified on its own merits today:

1. **The hot function stays pure** over its explicit inputs — no I/O, no ambient state, no resolver calls inside it. This is §2 anyway.
2. **A language-neutral normal form** for the artefact the offline stage emits and the hot stage consumes. Flat arrays of ground records with an explicit edge relation; no recursion to marshal, no host-language types in the contract.
3. **The conformance suite is backend-parameterised from day one**, even while exactly one backend exists. This is the only commitment that costs anything now, and the only one that is expensive to retrofit.

With these, a later port is a contained piece of work. Without them it is a rewrite, whatever the target language.

### 10.3 Candidate targets, if the option is ever exercised **[O]**

| Target | Buys | Costs | Approval difficulty |
|---|---|---|---|
| Indexed in-memory Python | Most of the available speedup, since the win is in not evaluating irrelevant records. Same language, same tests, available now. | Ceiling is real but unmeasured | None |
| Rego / OPA | A Go binary from a CNCF project; generation from flat ground records is near-trivial. Partial evaluation returns a residual condition, which is the right shape for entitlement-scale queries. | A third semantics to keep in sync; `undefined` collapses per §5.1; policy-plus-data-in-memory model does not suit a large event corpus | Low |
| Rust via PyO3 | In-process, best latency, keeps a Dafny extraction path open | Toolchain in the build image; `abi3` from the start or the ABI matrix explodes | Medium — framed as a Python library with Rust inside (pydantic-core, polars, ruff, uv as precedent) |
| Compiled to SQL | Pushes the scan to the store | Relocates the trusted computing base into the query generator and the engine's three-valued logic; explanation becomes hard | Low technically, high semantically |

**Ordering rule:** exhaust indexing and measurement before adopting a second semantics. Adding a target adds a synchronisation obligation that never goes away.

### 10.4 The measurable that decides **[O]**

Record the numbers before the argument, not after: p99 with the resolver excluded, records evaluated per request, candidate corpus size, and whether every decision must carry an explanation. If the hot stage is not a clear majority of the latency budget at realistic volume, a faster hot stage buys nothing, and the first real optimisation is caching or a materialised projection.

If a backend is ever adopted for the **verified** property rather than for speed, note that only extracted backends carry it. The hand-written one is then not an equivalent implementation but a deliberately weaker one, and that asymmetry must be explicit in the interface documentation, or someone will run the fallback in production believing they have the guarantee.

---

## 11. Tooling and environment **[D]**

- **ruff** — linting and formatting. Rule sets: `ANN` (annotations required), `B` (bugbear), `S` (security), `RUF`, `C4`, `SIM`, on top of ruff's defaults. Configured once at repo root (`pyproject.toml`), line length 100.
- **basedpyright** (§4) — strict mode over `tools/` and `tests/`, configured in `pyproject.toml`; spikes (§7.4) declare their own checkers. **[D]** (2026-10-12) The existing checkers were brought to strict, not ratcheted flag by flag. `tools/import_force.py` is exempt from strict typing and `ANN`: it is a run-once importer, and its output is now maintained by hand.
- **rumdl** — Markdown lint. **[D]** (2026-10-12) Every Markdown file outside the vendored suites (`conformance/external/`, `profiles/vendor/`) is lint-clean. `MD013` (line length) is off, because a paragraph is one line. rumdl rather than markdownlint-cli2 keeps the toolchain uv-only; the two differ slightly (markdownlint's `MD060` table style and `MD029` list numbering), and rumdl is the gate.
- **uv** — dependency management with hashed lockfiles. Reproducibility and supply-chain provenance are not optional in this environment.
- **pip-audit** — dependency vulnerability scan in the slow tier.
- **Generated artefacts are vendored, never hand-edited, and regenerated by a documented command recorded in the repo.** This applies to every generation target without exception — extracted Dafny (§9), generated Rego, generated SQL, and any compiled wheel. A generated policy artefact that someone patches in place destroys the traceability from source to decision, which is the property the whole discipline exists to defend. Where the artefact is a build output rather than source, it is separately versioned and its CI runs the conformance suite against the built artefact, not against the generator.

---

## 12. Adoption sequence

Each step is independently valuable. Stop wherever marginal cost exceeds the defect class caught.

1. ruff + uv + strict type checking on new modules
2. Functional core / imperative shell as a review criterion (§2)
3. Hypothesis on the core
4. Boundary parsing library selected and applied (§5)
5. Three-valued discipline applied at the boundary and in the verdict type (§5.1)
6. beartype in test environments
7. Contracts on kernel public functions (§6)
8. Backend-parameterised conformance suite, single backend (§10.2)
9. Tiering formalised in CI (§8)
10. CrossHair on pure predicates; mutation gate on the kernel
11. Dafny investigation — oracle mode only, targeting semantic preservation (§9)

Steps 1–5 deliver most of the value. Step 8 is cheap now and expensive later. Steps 10–11 are for the parts where being wrong is expensive.

---

## 13. Open decisions register

**Provisional picks.** #1, #2, #3, #5, #6, and #7 were settled on 2026-10-11 for a single-author repository. If due2 moves into a team or work environment, they are revisited against what that environment approves. They are not reopened before then without a reason.

**Tracking.** As `due2-architecture.md` §11, stated once there. Of the implementation-start checklist, #4 and #8 remain open (issue #23); #10/#11/#13 belong to the execution-target cluster (issue #16).

| # | Decision | Section | Blocked on |
|---|---|---|---|
| 1 | Static type checker (editor + gate) | §4 | Resolved 2026-10-11 (provisional): basedpyright strict, editor and gate |
| 2 | Boundary parsing library | §5 | Resolved 2026-10-11 (provisional): msgspec |
| 3 | Error handling: total core vs `Result` | §2.2 | Resolved 2026-10-11 (provisional): `Result` for expected failure, let it crash otherwise; one handler at the shell |
| 4 | Persistent-structure library | §2.1 | First real use case |
| 5 | beartype in production or test-only | §5 | Resolved 2026-10-11 (provisional): test environments only, through system test; optional in UAT |
| 6 | Contracts in production: preconditions-only or off | §6 | Resolved 2026-10-11 (provisional): preconditions only |
| 7 | `icontract` vs `deal` | §6 | Resolved 2026-10-11 (provisional): `icontract`; trial on the Kleene tables |
| 8 | Slow tier: nightly vs merge-queue | §8 | Observed merge frequency |
| 9 | Dafny availability | §9 | Resolved 2026-10-10 (`decisions/0002`): installable — Homebrew Apple-Silicon bottle 4.11.0, .NET 8 + Z3 |
| 10 | Rust toolchain in the build image | §10.3 | Platform team conversation |
| 11 | Backend selection criterion and thresholds | §10.4 | Measurement on realistic volume |
| 12 | Whether a direct interpreter is maintained as a specification artefact | §7.1 | Resolved by `decisions/0002`: Dafny-extracted `Den` oracle for stage 1, plus a Python reference evaluator for stage 2 and W2/W3 until a verified backend passes the corpus |
| 13 | OPA approval and version pinning, if the Rego path is taken | §10.3 | Only on exercising the option |
