# Ways of Working — Correctness Discipline for Python

**Status:** Draft v0.9 (2026-10-26)
**Scope:** Python services and libraries, with particular attention to decision/evaluation kernels where semantics are load-bearing.

**Changes in v0.9** (2026-10-26, `decisions/0038`, #107): §2.4 drops the canonical N-Quads term form, which no id is computed from any more, and says that a digest is a collection id. Earlier changes are in `docs/archive/changes.md`.

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

### 2.2 Error handling **[D]** (provisional, §13)

Failures come in three kinds, and each is handled one way only.

| Kind | Example | Handling |
|---|---|---|
| **An expected outcome** | Unknown data at request time | Not a failure. `Indeterminate` is a verdict, a value like any other (§5.1). |
| **An expected failure** | A policy W1 rejects; a malformed request at the boundary | `Result[T, E] = Success[T] \| Failure[E]`, hand-rolled frozen dataclasses, matched exhaustively (§2.3). The cause is data, e.g. W1's diagnostics (`due2-diagnostics.md`). |
| **Can't happen** | A contract violation, a broken invariant, `assert_never` reached, an I/O fault | Let it crash. The exception propagates, and the core has no handler for it. |

- **`Result` only where failure is expected.** A function that cannot fail in an expected way returns its plain value. Kleene `and` returns a truth value, not `Success` of one. Its signature then says that any failure is a crash, and the checker keeps the two kinds apart.
- **No library.** The two dataclasses and a type alias are the whole of it. A stage that must collect every error, such as W1's (`due2-diagnostics.md` §1), runs its checks and folds the failures into one `Failure`. It does not chain calls that stop at the first error.
- **One handler, at the shell.** In the Erlang sense of "let it crash", the shell is the supervisor. It catches what escapes the core, logs it in full with the traceback, and answers with an error outcome, never a verdict (`due2-workflows.md` §7). Then it takes the next request. The core is pure, so there is no state to restart. Restarting means handling the next request. This is the one `except Exception:` allowed without a re-raise.
- **Loud, never hidden.** A crash is never turned into `Indeterminate`, a default verdict, or an empty result. Doing that would make a bug look like missing data in the trace.

Exceptions are never control flow in the core, and no other bare `except:` or `except Exception:` without a re-raise is allowed.

### 2.3 Closed unions and exhaustiveness **[D]**

Model domain alternatives as closed unions of frozen dataclasses, matched with `match` and terminated by `assert_never(x)` in the default arm. This is the nearest Python gets to a non-exhaustive-match error: adding a variant makes every incomplete match a *type error*, statically, before runtime.

This is mandatory for any union representing domain semantics. It is the cheapest real guarantee in the document.

**Where this actually pays.** A pipeline that normalises a rich input into a flat regular form has two very different halves. The stage *after* normalisation operates on uniform records and tends to be a filter and a fold — closed unions buy little there beyond the verdict type. The stage *before* it is a recursive transformation over an inductive type with many cases, and that is where an added variant must not be silently ignored. When choosing where to spend review attention and specification effort, follow the case analysis, not the line count. See `due2-architecture.md` §3–§4 for the worked instance.

### 2.4 RDF at the boundary **[D]**

RDF is a wire format, not a working representation. It appears at one boundary: parsing authored policies and profile modules. W1 emits none (`decisions/0037`). Every transformation and every evaluation runs on the plain frozen structures of §2 — the lifted tree inside W1 stage 1, relations of tuples whose fields are terms everywhere else (`due2-workflows.md` §2, §4) — not a graph API.

- **One adapter module owns the library.** A third-party RDF library may exist inside it; its types, its `Any`s, and every `# type: ignore` stay there (§3). Nothing RDF-shaped escapes. The acceptance test is a grep: no RDF import outside the adapter and the test tree.
- **The lift is immediate and lossless by construction.** The parsed graph becomes typed trees in the same call that reads it. The input profile is what makes that possible: anonymous structure is a forest hanging from named anchors, rule references are acyclic, IRIs are never dereferenced, there are no named graphs, and skolemisation leaves no blank nodes (`odrl-compound-to-atomic-normalization.md` §3–§5) — so no graph algorithm is needed after the door. The lift owns the term model — IRI, literal `(lexical, datatype[, language])`, list cells — which is the real, bounded cost of this rule.
- **Digests come from the plain structures**, not from a library graph re-serialised. A collection id is the SHA-256 of the collection's canonical JSON (`decisions/0007`), which keeps it deterministic by construction. W1 computes no id from content: it mints them (`odrl-compound-to-atomic-normalization.md` §5.2).
- **The library's remaining job is the slow tier.** Property tests round-trip the lift against the library's own parse: isomorphic inputs give lifted trees equal up to the renaming of minted ids (`odrl-compound-to-atomic-normalization.md` §5.2; §7.3 ratchet). A discrepancy is a lift bug.

What this buys: exhaustiveness where it pays (§2.3) instead of `isinstance` chains against open graph APIs; a hot path free of graph indexes (§10.1); canonical bytes for every collection without a graph canonicaliser; and an evaluator in another language that reads the corpus, not an RDF stack (`decisions/0027`).

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

Strict mode is non-negotiable. The candidates compare as follows, and the pick is stated after the table.

| Tool | Conformance | Speed | Note |
|---|---|---|---|
| Pyright / basedpyright | ~98% | fast | Best narrowing and inference; strongest correctness signal |
| Pyrefly (Meta) | ~88% | very fast | 1.0 May 2026; auto-converts existing mypy/pyright config |
| mypy | ~58% | slow | Mature plugin ecosystem; 2.0 added parallel checking |
| ty (Astral) | ~53% | fastest | Alpha. Unimplemented and clean look identical in CI — unsafe as a gate |

**[D]** (provisional) **basedpyright in strict mode**, in the editor and as the gate. One tool means the editor and CI never disagree. Pyrefly can join the editor later if speed matters. Revisit if the code moves to an environment that approves a different checker (§13).

Adoption on code written before strict checking: enable one strict flag per sprint rather than a big-bang migration. New modules start strict.

---

## 5. Boundaries: parse, don't validate **[D]**

All external input — HTTP, files, queues, database rows, config — is parsed into a typed domain object at the boundary. Past that point, types are trusted and **not re-validated**. Defensive re-checking inside the core is redundancy, and redundancy hides which layer owns the invariant.

**[D]** (provisional) **msgspec**, for the JSON boundary: requests, state of the world, case files. It decodes straight into the frozen dataclasses of §2, so the domain model does not depend on it. RDF has its own adapter (§2.4). The alternatives considered:

- **msgspec** — fastest, strict by default. Best fit for wire formats and high-volume paths.
- **pydantic v2** — richest constraint vocabulary. `Annotated[int, Field(ge=0)]` gives crude refinement types at the edge. Heavier; couples domain models to the library.
- **attrs + cattrs** — most composable, least magic, cleanest separation of domain model from serialisation.

Selection criterion: if the domain model should stay library-agnostic, attrs+cattrs. If throughput dominates, msgspec. If constraint expressiveness dominates, pydantic.

**Runtime enforcement:** `beartype` via import hook enforces existing annotations at near-constant cost. **[D]** (provisional) Test environments only: on in unit, integration, and system tests, optional in UAT, never in production.

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

**Tool:** **[D]** (provisional) `icontract` — `@require`, `@ensure` (with old-value capture), `@invariant`. The first module to use it is the Kleene truth tables, as the trial. `deal` was the alternative; it bundles a linter and a Z3-backed solver for simple functions, but `icontract` has the stronger ecosystem (`icontract-hypothesis`, CrossHair integration, `pyicontract-lint`).

**What to contract:**

- Every public function of a kernel/evaluator module.
- Class invariants on any type with a non-trivial well-formedness condition.
- Not trivial type restatements — the checker already does that. Contract the things types *cannot* express: ordering, non-emptiness under conditions, relationships between arguments, idempotence, monotonicity.

**Why contracts earn their place here:** they are the connective tissue between layers. `icontract-hypothesis` derives property-test strategies directly from preconditions, so a contract generates tests for free. CrossHair reads the same contracts and attempts to refute them symbolically. One artefact, three consumers: the runtime check, the test generator, and the symbolic refuter.

**Runtime cost:** contracts are enabled in dev and test unconditionally. **[D]** (provisional) In production, preconditions stay on and postconditions and invariants are off. A wrong policy decision costs more than the check.

---

## 7. Testing

This section lists the instruments. Which instrument guards which risk in due2, what each oracle is independent of, and what must exist before each component is coded: `correctness-strategy.md`.

### 7.1 Layers **[D]**

- **Unit tests** — pytest. Example-based, fast, deterministic. Cover the specific and the regression-worthy.
- **Property tests** — Hypothesis. The primary correctness instrument for the core. Test algebraic laws: idempotence, commutativity where claimed, round-tripping (parse ∘ render = id), invariant preservation, monotonicity.
- **Semantic preservation** — where a pipeline rewrites a rich input into a normal form before acting on it, the load-bearing property is that the rewrite changes nothing observable: for all inputs `p` and requests `r`, `interpret(normalise(p), r)` equals `interpret_directly(p, r)`, provided unknowns are completed over literals rather than over the normal form's findings — otherwise the rewrite's own correlations (a split guard and its negation) are lost and only refinement holds (`due2-workflows.md` §6.4, §8 L9). This is worth more than any number of tests against the normal form itself, because it is the only check that the rewrite has not quietly changed meaning. It requires maintaining a direct interpreter as a specification artefact, which is a real cost and a justified one.
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

### 7.4 One suite, many spikes **[D]**

Candidate implementations (the oracle `I`, and the W2/W3 evaluator of `decisions/0027` until W1 exists) are tested by one Python suite, written before them and shared by all. The vectors and expected results are the corpus (`conformance/`), pinned in git. Each candidate is a separate spike under `spikes/` that runs as a subprocess and speaks a JSON-lines protocol: text in, text out, so a spike in any language faces the same tests. The harness measures latency identically for every spike. Each spike commits a scorecard (its last full run) and an append-only journal: effort, attempts, rewrites, bugs, and checker diagnostic counts over time. The contract is in `spikes/README.md`, and the harness in `tools/harness/`. `uv run pytest` alone runs only the harness's self-tests, which pin both ends: a backend that echoes the expected results passes every vector, and one that returns nothing fails every vector.

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

## 9. Verification track **[D]** (`decisions/0021`)

Everything above reduces the probability of a defect. None of it produces a proof. Where a claim needs one, due2 follows Cedar's verification-guided development (`decisions/0021`). It has three parts: a small, executable model of the semantics, written in a prover; proofs of the claims about that model; and differential testing of every implementation against it. No production code is extracted from the model. `correctness-strategy.md` §4.8 states the claims, the oracles, and the gate.

**What to point it at.** Verification effort follows the case analysis. Once a policy has been rewritten into a flat normal form, the decision function is a filter and a fold, small enough to review by eye and cheap to test exhaustively. The case analysis lives in two other places, and those are the targets:

- **The completion algebra** (`due2-workflows.md` §6.4). Its claims make W3's two-extreme computation equal to the definition over every completion. A flaw in one makes a definite verdict wrong (`correctness-strategy.md` R3).
- **Semantic preservation in W1** (§7.1; `odrl-compound-to-atomic-normalization.md` §8.1). A mis-normalised policy still evaluates cleanly and simply means something else (R1). The `Den` oracle becomes part of the model (issue #8).

**Counterexamples first.** Each claim gets a small Alloy 6 model, and M and W also a bounded-exhaustive search over clingo-i, before anyone tries to prove it (`decisions/0021` #3 and its amendment). A small-scope search finds a false claim in minutes, and a failed proof finds it slowly.

**Operational cautions:**

- The cost is in the proofs, not in the model: Cedar's proofs are about 3.4 times the size of its models (`references.md` §7). The prover spike measures it (`decisions/0021` #4) before anything depends on it.
- Pin the prover and its libraries in the repository, and use the prover's deterministic limits (Lean's heartbeats, for one) rather than wall-clock timeouts. Otherwise a proof checks on one machine and fails on another, and CI goes flaky.
- Pin each proof to the spec version it states. A proof that outlives its spec version proves the previous one.

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

We do not choose a second backend before a measurement calls for one (§10.4). We keep the choice cheap. Three commitments do that, and each is justified on its own merits:

1. **The hot function stays pure** over its explicit inputs — no I/O, no ambient state, no resolver calls inside it. This is §2 anyway.
2. **A language-neutral normal form** for the artefact the offline stage emits and the hot stage consumes. Flat arrays of ground records with an explicit edge relation; no recursion to marshal, no host-language types in the contract.
3. **The conformance suite is backend-parameterised from day one**, even while exactly one backend exists. This is the only commitment that costs anything while one backend exists, and the only one that is expensive to retrofit.

With these, a later port is a contained piece of work. Without them it is a rewrite, whatever the target language.

### 10.3 Candidate targets, if the option is ever exercised **[O]**

| Target | Buys | Costs | Approval difficulty |
|---|---|---|---|
| Indexed in memory, in the evaluator's language (`decisions/0027`, #104) | Most of the available speedup, since the win is in not evaluating irrelevant records. Same language, same tests, no new toolchain. | Ceiling is real but unmeasured | None |
| Rego / OPA | A Go binary from a CNCF project; generation from flat ground records is near-trivial. Partial evaluation returns a residual condition, which is the right shape for entitlement-scale queries. | A third semantics to keep in sync; `undefined` collapses per §5.1; policy-plus-data-in-memory model does not suit a large event corpus | Low |
| Rust, in process | Best latency | Toolchain in the build image, and a native-library boundary: the JVM's foreign function API, or PyO3 for a Python host, with `abi3` from the start or the ABI matrix explodes | Medium — framed as a library with Rust inside (pydantic-core, polars, ruff, uv as precedent) |
| Compiled to SQL | Pushes the scan to the store | Relocates the trusted computing base into the query generator and the engine's three-valued logic; explanation becomes hard | Low technically, high semantically |

**Ordering rule:** exhaust indexing and measurement before adopting a second semantics. Adding a target adds a synchronisation obligation that never goes away.

### 10.4 The measurable that decides **[O]**

Record the numbers before the argument, not after: p99 with the resolver excluded, records evaluated per request, candidate corpus size, and whether every decision must carry an explanation. If the hot stage is not a clear majority of the latency budget at realistic volume, a faster hot stage buys nothing, and the first real optimisation is caching or a materialised projection.

If a backend is ever adopted for the **verified** property rather than for speed, note that only extracted backends carry it. The hand-written one is then not an equivalent implementation but a deliberately weaker one, and that asymmetry must be explicit in the interface documentation, or someone will run the fallback in production believing they have the guarantee.

---

## 11. Tooling and environment **[D]**

- **ruff** — linting and formatting. Rule sets: `ANN` (annotations required), `B` (bugbear), `S` (security), `RUF`, `C4`, `SIM`, on top of ruff's defaults. Configured once at repo root (`pyproject.toml`), line length 100.
- **basedpyright** (§4) — strict mode over `tools/` and `tests/`, configured in `pyproject.toml`; spikes (§7.4) declare their own checkers. `tools/import_force.py` is exempt from strict typing and `ANN`: it is a run-once importer, and its output is maintained by hand.
- **rumdl** — Markdown lint. Every Markdown file outside the vendored suites (`conformance/external/`, `profiles/vendor/`) is lint-clean. `MD013` (line length) is off, because a paragraph is one line. rumdl rather than markdownlint-cli2 keeps the toolchain uv-only; the two differ slightly (markdownlint's `MD060` table style and `MD029` list numbering), and rumdl is the gate.
- **uv** — dependency management with hashed lockfiles. Reproducibility and supply-chain provenance are not optional in this environment.
- **pip-audit** — dependency vulnerability scan in the slow tier.
- **Generated artefacts are vendored, never hand-edited, and regenerated by a documented command recorded in the repo.** This applies to every generation target without exception — generated Rego, generated SQL, and any compiled wheel. A generated policy artefact that someone patches in place destroys the traceability from source to decision, which is the property the whole discipline exists to defend. Where the artefact is a build output rather than source, it is separately versioned and its CI runs the conformance suite against the built artefact, not against the generator.

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
9. Tiering formalised in CI (§8; the PR tier is §14.3)
10. CrossHair on pure predicates; mutation gate on the kernel
11. The formal model: counterexamples first, then proofs, then the differential (§9)

Steps 1–5 deliver most of the value. Step 8 is cheap before a second backend exists and expensive after. Steps 10–11 are for the parts where being wrong is expensive.

---

## 13. Open decisions register

**Provisional picks.** #1, #2, #3, #5, #6, #7, and #14 were settled for a single-author repository. If due2 moves into a team or work environment, they are revisited against what that environment approves. They are not reopened before then without a reason.

**Tracking.** As `due2-architecture.md` §11: each open row has an issue, and the issue names this section. Rows keep their numbers, because issues and other documents cite them; a resolved row leaves the table and is stated below it.

| # | Decision | Section | Blocked on | Issue |
|---|---|---|---|---|
| 4 | Persistent-structure library | §2.1 | First real use case | #23 |
| 8 | Slow tier: nightly vs merge-queue | §8 | Observed merge frequency | #23 |
| 10 | Rust toolchain in the build image | §10.3 | Platform team conversation | #16 |
| 11 | Backend selection criterion and thresholds | §10.4 | Measurement on realistic volume | #16 |
| 13 | OPA approval and version pinning, if the Rego path is taken | §10.3 | Only on exercising the option | #16 |

Rows 1–3, 5–7, and 14 are the provisional picks above, each stated in the section named: basedpyright strict as editor checker and gate (§4); msgspec at the JSON boundary (§5); `Result` for expected failure and a crash otherwise, with one handler at the shell (§2.2); beartype in test environments only, through system test, optional in UAT (§5); contracts in production checking preconditions only (§6); `icontract`, trialled on the Kleene tables (§6); and, as row 14, JSON Schema 2020-12 as the language of the port schema, from which the OpenAPI and MCP adapters are generated (`due2-platform.md` §1.2). Row 9, Dafny's availability, is moot: `decisions/0021` withdraws Dafny. Row 12, whether a direct interpreter is maintained as a specification artifact (§7.1), is answered yes: clingo-i renders the evaluation semantics as the L9 oracle and the generator, and is not a pipeline stage (`decisions/0009`); the Python `Den` oracle, and later the chosen prover's, render W1 stage 1 (`decisions/0021`, issue #8).

---

## 14. Development cycle and backlog **[D]**

### 14.1 The cycle

Every change to a component is an increment, and every increment takes five steps in order: design, docs, test, code, verify. Each step leaves something in the repository. A step with nothing to leave is skipped, and the commit says so.

1. **Design.** Name the spec sections the increment renders and the decisions it rests on. Anything the spec leaves open stops here and becomes an `open-decision` issue (spec before code). The increment's issue states its scope, the vectors it turns green, what it declines, and its done-gate. For a component without a `correctness-strategy.md` §4 entry, writing that entry is this step.
2. **Docs.** The design lands as text before code: a spec edit (with a decision record if it is load-bearing), or the component's own design notes. For a spike these are in `spikes/<name>/DESIGN.md`: its structure, its internal interfaces (for clingo-i, the fact schema), and what it declines and why. The text and the code's comments meet §15, and the skill's checklist is run before the commit.
3. **Test.** The tests exist, and fail or are declined, before the code. The corpus vectors are already written (§7.4). The increment adds what the corpus cannot see — unit tests, Hypothesis properties, tables checked exhaustively — to the component's own suite. The implementer never adds or changes a shared vector (`spikes/README.md`, Rules); a missing vector becomes a `corpus` issue.
4. **Code.** The smallest change that turns the targeted tests green. A vector the code cannot yet meet is declined by feature (`spikes/README.md`, Protocol), not left to fail.
5. **Verify.** README § Verify and the component's own checks pass: for a spike, its `backend.toml` checks and `uv run pytest --backend=<name>`. A disagreement with a hand-derived verdict is triaged under `correctness-strategy.md` §6 before the increment closes, and never edited to pass. A spike journals its session, attempts, and bugs, and runs `spike_journal.py check`. The commit cites the issue and is pushed, and the issue closes citing the commit.

**Increments are vertical.** The first increment is a walking skeleton: it runs end to end through every layer for the simplest vectors and declines everything else by feature. Each later increment widens one feature and turns its vectors from unsupported to pass. The scorecard's unsupported count only goes down. A commit that raises it says why.

### 14.2 The backlog

- **Issues** follow the convention of `due2-architecture.md` §11: one issue per open item, labelled, each naming its source-of-truth section. The issue templates in `.github/ISSUE_TEMPLATE/` ask for that section.
- **Sub-issues.** A work item too large for one increment is a parent issue with one GitHub sub-issue per increment. The parent holds the done-gate. Each sub-issue holds its increment's design summary (step 1) and closes on the commit that meets it.
- **Milestones** are deliverables with a done-gate, scheduled in the order of `CLAUDE.md` Next. An issue in no milestone is backlog, not scheduled.
- **`parked`** marks an item deferred until a named condition, which the issue states.
- **Scope.** A finding outside the increment's scope becomes an issue, not part of the increment.

### 14.3 Branches and CI

- **Trunk-based.** The owner commits to `main`, and every commit on `main` passes. Work that does not pass stays on a branch.
- **Other contributors use pull requests.** A change written by another model or agent (Hermes, Agy, a delegated worker) arrives as a pull request and is reviewed before it merges; it is never pushed to `main` directly. The pull-request template carries the checklist of §14.1.
- **CI is the PR tier of §8** (§12 step 9). `.github/workflows/verify.yml` runs README § Verify on every push and pull request, against the locked environment. It is deterministic, and each job has a twenty-minute timeout. A spike's checks and its corpus run are a job of their own, as clingo-i's are. The slow tier's trigger is open (§13 #8).
- **Supply chain.** Actions are pinned by commit SHA. Dependabot proposes updates to the actions and the uv lock monthly, grouped, and each update passes CI like any other change.

---

## 15. Documentation **[D]**

Text written as a reminder, by a writer who holds the whole context, leaves a later reader to piece the story together from scattered fragments. This section sets the standard that prevents it. The procedure and the review checklist are the project skill `.claude/skills/technical-writing/SKILL.md`. The sources behind each rule are in `references.md` §5.

### 15.1 The reader

Write for a cold reader: a person, or a model, with the repository and nothing else. They have not seen the conversation, the issue thread, or the session that produced the text. A passage is done when that reader can re-derive every claim in it from the text and the sections it cites. It is not done when the writer can recognise it.

### 15.2 Kinds of text

Each passage does one job (Diátaxis): **reference** (what is: interfaces, schemas, rules), **explanation** (why: arguments, alternatives rejected), **how-to** (the steps of a task, such as README § Verify), or a **worked example** (one input followed through the mechanism). A document may hold several kinds, each in its own section.

**Status** (what is done, what is next, what an increment changed) is a fifth kind. It lives only in README § Status, `CLAUDE.md` § Next, the issues, a spike's `journal.jsonl` and `scorecard.json`, and a document's **Changes** lines. Reference text describes what the code or spec is now, in the present tense. A limit is stated as a decline or an open item ("constraints are declined, #47"), not as a history ("increment 2 added …").

### 15.3 Vocabulary

- **One word, one sense.** Where the domain gives a word two senses, one of them is always qualified. In clingo-i, "RDF literal" is `lit(Lex, Datatype)` and "literal" is a completion literal.
- **Define what you coin.** Any term the spec does not define is defined at first use or in the document's vocabulary, and every coined term the document uses appears there. A name that explains itself (`may_apply`) is better than a short one that needs a definition (`live`).
- **One letter, one kind.** In a program, a variable letter keeps one kind throughout: `W` is always a world, never a truth value. Each program states its letters in a table.

### 15.4 Interfaces

Every file, module, and public function states what it consumes, what it provides, and why it exists. That includes the invariants and sentinels a caller has to know, such as "`none` when the rule has no assignee". The interface can be read without the implementation. It lives in the file itself, beside the code, as in literate programming: an ASP file's header and doc blocks, a Python module's docstring. The semantics of what the file defines, and the arguments for them, live there too. The generated reference renders them (§15.10), so a reader can find a relation by name without grepping. A design note cites them and does not restate them, because two copies drift apart.

### 15.5 Worked examples

A document that describes a mechanism follows one real input through it, step by step: what each stage reads and what it derives. The example comes from a run, not from memory. A test pins it (its input and its result), so it cannot silently go stale.

### 15.6 Arguments

A claim that something is sound, exact, complete, or impossible ("no vector reaches it") carries its steps: the premises, the inference, and the conclusion. If a step needs the spec, cite the section. A test or check states the risk it guards and the counterfactual: what got through without it. The model is clingo-i's brute-force bullet, "Without them, deleting the flip constraint … survived most runs".

### 15.7 Cross-references

A `§` reference names its document, unless it points into the document it appears in: write `due2-workflows.md §6.4`, not `§6.4`. Where the number alone would send the reader off to look, add the subject: "`due2-workflows.md` §6.4, the literal key".

### 15.8 Code comments

- **Interface comments** state what goes in, what comes out, and why: a file header, a module docstring, a function docstring, and, in ASP, a block for each predicate. They do not describe the implementation.
- **Implementation comments** mark only what a fluent reader would miss: an idiom, a trick, a sentinel, an ordering constraint, or why the obvious approach was not taken. They never paraphrase the line below them.
- **Python.** Docstrings follow PEP 257: a one-line summary, a blank line, then the detail. The summary names what the function returns, as a noun phrase ("The facts of the vector's request"), or what it does, when it returns nothing. A module docstring says what goes in and what comes out. Add Google-style `Args:`, `Returns:`, `Raises:`, and `Attributes:` sections only when the signature and the summary do not already say it; every exception a caller should expect is under `Raises:`. Types live in annotations, not in prose (§3).
- **ASP.** A file header (`%#` title line, which clindocs renders as the page heading) names the purpose and the spec sections, then lists, as Markdown bullets, `% - **Consumes:**` and `% - **Provides:**` each relation as `` `name/arity` ``. `%##` lines make sections. Each predicate the file defines has one doc block in clindocs' format, `%*! name(Args)`, a blank line, the text, and `*%`, which clingo reads as a block comment. Its first sentence is the summary clindocs shows in its predicate table, cut at the first full stop, so it holds no dotted name (a file name, "e.g."). A comment marks each idiom whose behaviour is not local: an aggregate used as a function, the case where an empty set makes a rule inapplicable, a sentinel term.

### 15.9 Where compression is right

Tables, enumerations of codes, and lists of declines stay compact, because they are looked up, not read through. Spend the extra words on arguments and on mechanisms.

### 15.10 Checks

What can be measured is checked, so that the rules hold without a reviewer.

**The generated reference.** The docstrings and doc blocks are built into reference pages by MkDocs: mkdocstrings (Google style) for Python, and clindocs for ASP, one page per relation with its block, a predicate table, and a dependency graph. The pick is provisional: it is made for clingo-i, where both run under one MkDocs build, and is revisited when the production evaluator is written. The build, `uv run --group docs mkdocs build --strict`, is in README § Verify and CI, so a broken reference, or a docstring mkdocstrings cannot parse, fails the commit. The pages are not committed. clindocs reads ASP through tree-sitter-clingo, and tree-sitter 0.26 crashes it, so the docs group pins `tree-sitter<0.26`.

**The doc tests.** clingo-i's `tests/test_docs.py` reads the program with `clingo.ast` and checks:

- every relation the program defines has exactly one doc block, in the file that defines it;
- each block's summary sentence is whole (§15.8);
- each file header's **Consumes** and **Provides** lists match its rules;
- every relation the program reads but does not define is an input fact named in the module docstring of `clingo_i/flatten.py`;
- the docs entry point includes the program files in the order the interpreter loads them;
- `DESIGN.md`, the docs pages, and every Python and ASP file carry no bare `§` references.

The rest is the skill's review checklist (`.claude/skills/technical-writing/`).
