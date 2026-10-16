# due2 — Implementation Alternatives II: The Host — Python vs the BEAM

**Status:** Record of the 2026-10-16 host comparison, prompted by the Pentad Labs "Gleam and Zig" post (§9) and a changed-assumptions hypothetical. Not normative: the standing path (`decisions/0002`) holds until a trigger in §8 fires. **Revised the same day** after review inputs: persistence decoupled from host (Postgres is a deployment consequence either host shares); Elixir's contract mechanisms (guards, Bond, typespecs) and RDF.ex corrected in; LLM codability split into fluency and structural-safety dimensions, then re-benched twice — AutoCodeBench (arXiv:2508.09101) carries the Elixir column whose numbers run Elixir's way (caveated, §3), and MultiPL-E's dataset carries an Elixir track (`humaneval-elixir`, `mbpp-elixir`) that the paper's original 18 did not include. Two claims made en route were wrong and are withdrawn: "no benchmarked Elixir column" and "MultiPL-E has no Elixir track" — the second was verified against the README's stale language count instead of the dataset's config list.

**Companions:** `implementation-alternatives.md` (the W1 and verification-track review; this is its sequel) · `due2-architecture.md` (§9, §10) · `ways-of-working.md` (§2.2, §10) · `decisions/0002`

The first review asked which *vehicle* verifies W1 (§1 there: four sub-problems, A–D). This one asks a different question: which *host* runs due2, comparing the standing proposition — Python everywhere, Dafny oracle, `decisions/0002` — against an Elixir/BEAM alternative with a rented Rust door. Elegance is excluded from the scoring on purpose; the question is which is better, under stated assumptions, and why.

---

## 1. The question, corrected

"Which is better" is ill-formed until the assumption set is named, because the two propositions were each optimal under different assumptions — and the assumptions differ on the three axes that do the deciding:

| Assumption | Standing (2026-10-10 review) | Changed (this review's hypothesis) |
|---|---|---|
| Who writes the code | LLM-primary; the repository's rules are written for agent authoring | A single human author |
| Deployment horizon | Single-user, governance scale; multi-user is speculation (architecture §1 "out of scope for now") | Multi-user deployment is a real eventual requirement |
| Tooling constraints | Bank register: no Rust toolchain, approved packages only | None |

Neither proposition is better unconditionally. What a review can honestly deliver is the decision rule — which assumptions flip the answer — and the cost of the flip. Those are §7 and §8.

---

## 2. What does not change in either host

The comparison is a host comparison, not a semantics comparison. Everything normative travels unchanged:

- the corpus (107 cases / 397 scenarios, 8 negative) and its hand-derived verdicts;
- the three workflows and the laws L1–L9 (`due2-workflows.md` §8);
- the `Den` oracle plan (`decisions/0002`);
- measurement before any compiled hot path (`due2-architecture.md` §9.1);
- the backend-parameterised conformance suite (`ways-of-working.md` §10.2);
- the `tools/` checkers — corpus admissibility, SHACL validation (`pyshacl`), the completion check — which are dev-time tooling, not runtime: RDF lives in the one boundary adapter `ways-of-working.md` §2.4 already quarantines, so a host flip ports the runtime's lift and never touches the checkers.

That is not luck; it is the payoff of the three commitments `ways-of-working.md` §10.2 records (pure hot function, language-neutral normal form, suite parameterised from day one). A host flip is a port of a parser and a shell — the "second backend that ports a parser, not a semantics" the first review §10 promised to keep cheap. The constitution travels; the host is replaceable.

---

## 3. The standing path restated — and what it costs when the assumptions flip

**What it buys under its own assumptions.**

- **The instrument base is the product's factory, and it is Python-native.** Hypothesis (primary instrument, ways §7.1); CrossHair — the only symbolic executor of the pure core in either stack; icontract with `icontract-hypothesis` compounding contracts into property tests (ways §6); mutmut on the kernel; basedpyright strict, already gating `tools/`; msgspec at the boundary. Rebuilding this tier in another language is not a port; it is a re-derivation. Some substitutes are real — StreamData is a wash, function-head guards are preconditions always on in production — but the compounding has no equivalent: `icontract-hypothesis` turns contracts into property strategies, CrossHair symbolically executes the pure core, mutmut measures whether the tests notice (§6).
- **The checkers exist and run in CI today** (`check_corpus.py`, `check_odrl22.py`, `check_completion.py` — README §Verify).
- **LLM codability**, decisive while authoring is LLM-primary — a dimension pair, and now a benchmarked one. *Function-completion fluency*: AutoCodeBench (Tencent Hunyuan, arXiv:2508.09101 — 3,920 problems over 20 languages, 30+ models) is the benchmark whose Elixir column carries the model-level numbers in circulation, and the result runs Elixir's way: Elixir tops the per-language upper bound (97.5% to Python's 63.3%), and Claude Opus 4 scores 80.3% on Elixir against 40.3% on Python. The caveats are as large as the gap: Elixir's problems were translated from Python — algorithmic Elixir, no OTP, no GenServers; the paper's own difficulty filter "struggles to filter out simple problems in low-resource language scenarios" (25.1% of Python problems were removed as too easy; Elixir's set filtered less); and no human verified the Elixir test cases. The honest reading is not "twice as well" but *Elixir is not niche-handicapped at function completion* — a real ceiling, a partly artifact ranking. MultiPL-E (arXiv:2208.08227) grew an Elixir track after the paper's original 18 (`humaneval-elixir`, `mbpp-elixir` in the dataset), but the Elixir results in circulation are AutoCodeBench's, and nothing SWE-bench-shaped tests Elixir at all — the evidence is two tracks, one caveated headline result, and no repo-scale Elixir evaluation. *What remains Python's*: repo-scale familiarity — the instrument stack itself is model-familiar — and library breadth. Python's own documented liability is churn: 70–90% deprecated-API usage on stale context, 9–18% even on current (ICSE 2025, arXiv:2406.09834), ~50% success on version-pinned generation (GitChameleon 2.0); Elixir's stable core and doctest-verified documentation — `@doc` examples execute as tests, so the examples in its training data were verified correct — cut that class. *Structural safety of what was generated* favours Elixir as before: explicit `do…end` enclosures turn a misplaced statement into a deterministic compile error where Python's indentation silently changes scope; immutability removes the mutation and re-binding class; function heads fail fast with the offending input (`FunctionClauseError`) instead of `NoneType` deep in a run; the millisecond compiler is a native feedback oracle in a generate-check loop. For repo authoring — agent-in-the-loop, CI as the oracle — instrument familiarity and library breadth dominate over function-completion rankings. Runtime codegen, where BEAM process isolation would matter, is not due2's case: the binding language is deliberately not a language (`due2-architecture.md` §5).
- One language, one term model, and Dafny's Python extraction keeps the oracle in-tree.

**What it costs when the assumptions flip.**

- The multi-user shell becomes seams: an HTTP framework, a job queue, a broker, a real database — assembled from parts younger than OTP, with the shell (now the risk center) the half where `ways-of-working.md` §2.2's "let it crash" has no runtime behind it, only a document.
- Persistence is deployment-driven, not host-driven. Multi-user volume selects Postgres under either host — the ledger is the shell's, and nothing in the core notices — so the single-user store (SQLite, files and digests) is a consequence of staying single-user, not of staying Python.
- Resolver fan-out rides asyncio; W2 throughput has a CPython ceiling — unmeasured, and per §9 probably moot at governance scale, but real at multi-user scale.

---

## 4. The BEAM alternative, stated precisely

**Elixir everywhere.** A LiveView console over the ledger — replay of a pinned case, the `Pending` frontier with its routes, verdict transitions in both directions — which makes `due2-architecture.md` §7's audit answers browsable and turns the §9.1 measurables into dashboards rather than log archaeology. An OTP shell in which `ways-of-working.md` §2.2 stops being convention and becomes the runtime: one supervised process per request, a resolver pool under a supervisor, an Oban sweep for the re-evaluation trigger (issue #14). And a pure Elixir core including W1: pattern matching over the lifted tree, an unbounded offline budget, native arbitrary-precision integers and binaries, digests already riding the `crypto` NIF.

**Persistence follows the deployment assumption, not the host.** Multi-user volume selects Postgres under either host — via Ecto here — with decision time and validity time as first-class columns (§7's two clocks), because concurrent ledger writes are a multi-user consequence, not an optimisation. The single-user store is files and digests in both worlds. What the host adds is not the database but the operability around it: the supervised request path, the sweep, the console.

**Rust enters through one rented door, in admission order.** First the `Den` oracle as a CI-side CLI — host-agnostic, no VM integration, zero production risk; Dafny has no Elixir backend, and the oracle's role is defined by the differential test, not by where it lives (register #10's backend-maturity caveat applies unchanged; Go/C# extraction is the fallback). Second, the measured W2 hot path via Rustler, only on §9.1 evidence, with the crate surface ≈ `rustler` and nothing else, NIFs pure, total, and bounded — which is the shape `decide` and the expansion functions already have. A hung NIF blocks a scheduler; the discipline is the price of the door.

**A note on types.** Elixir's set-theoretic type checker was not verified as a shipped compiler gate for this review; plan on dynamic Elixir plus Dialyzer — a success-typing, not sound, checker. That is the same honesty `ways-of-working.md` §4 applies to Python's checkers; no soundness is being bought either way.

---

## 5. Set aside, with reasons

- **Gleam.** One decisive win: compile-time exhaustiveness over W1's case analysis — the stage where a missed variant "evaluates cleanly and means something else" (architecture §4 item 5). A bounded loss: the corpus and exhaustive-constructor tests catch it at test time. Its losses are unbounded: property testing is `qcheck` at v0.0.x (single-author) against StreamData; RDF only through untyped interop with RDF.ex; no delivery ecosystem. **Parked, not rejected:** `mix_gleam` is official, the core stays Gleam-portable by construction (pure, no macros, explicit typespecs), and the carve-out along the W1 line remains a trigger (§8).
- **Zig.** The Pentad criterion for its native half is bit-level exactness — SIMD over aligned structures, io_uring, reproducible numeric kernels. due2's exactness is algorithmic: canonical bytes, digests, pinned inputs, decimal discipline — all BEAM-native. The one credible native need is entitlement-scale W2, which measurement gates and Rust serves. Rejected.
- **OCaml+Why3, Lean, clingo.** Unchanged from the first review (§4–§6 there). One note: under a BEAM host the OCaml route gets strictly harder — no Elixir in Why3's extraction set, so the oracle goes host-agnostic anyway — and clingo's exclusion (the `U`-collapse) is untouched by host choice.

---

## 6. Axis by axis, elegance aside

| Axis | Standing: Python | Alternative: Elixir/BEAM |
|---|---|---|
| Property testing | Hypothesis, mature | StreamData, mature — even |
| Symbolic execution of the core | CrossHair, unique in either stack | none |
| Contracts | icontract + `icontract-hypothesis`: contracts compound into property strategies | guards (always-on preconditions), Bond (`@pre`/`@post`, invariants), typespecs — the mechanisms exist; the contract→property bridge does not |
| Mutation testing | mutmut, kernel-scoped | immature |
| Static checking | basedpyright strict (unsound, strong) | Dialyzer (unsound, weaker inference) |
| Exhaustiveness | `assert_never` convention | `case` convention; nil-truthiness hazard (§5.1), corpus vectors the backstop |
| LLM function-completion fluency | densest training data; instrument stack model-familiar; churn a documented liability (deprecated APIs 70–90% stale-context) | ahead of Python on AutoCodeBench's Elixir column (caveated, §3); MultiPL-E carries an Elixir track with thin model coverage; stable core, doctest-verified docs; niche Hex functions hallucinate |
| Generated-code safety | indentation changes scope silently; mutation class | structural errors are compile errors; immutability; `FunctionClauseError` fail-fast |
| RDF intake | rdflib behind one adapter; `pyshacl` for SHACL | RDF.ex behind the same adapter; SHACL stays `pyshacl` — dev-time tooling is host-independent (§2) |
| Multi-user serving | seams (queue, broker, framework) | OTP native |
| Delivery surface / GUI | none | LiveView console |
| Hot-path latency | unmeasured CPython ceiling | BEAM headroom; Rust door on §9.1 evidence only |
| Oracle integration | Dafny Python extraction in-tree | host-agnostic CLI or Rust door |
| Solo-author risk | incumbent; checkers already run | new language, bus factor 1 |

One axis is deliberately absent from the table: **persistence**. It follows deployment volume, not host — SQLite or files single-user, Postgres multi-user — and the ledger is the shell's in every column, so the choice never reaches the core (§4).

Read under the standing assumptions, Python wins the axes that are the product — instruments, codability, incumbency — and loses axes priced near zero (GUI, concurrent serving, hot-path headroom). Read under the changed assumptions, Elixir wins the axes that have become the product — operability, delivery, latency headroom — while the semantics travel free, and Python's remaining wins shrink to authoring convenience. Neither reading dominates; that is the finding, and it is why the verdict is a rule, not a winner.

---

## 7. The verdict, as a decision rule

- **Under the standing assumptions (LLM-primary authoring, single-user governance scale, bank register): the Python path is better, and the margin is structural.** The correctness strategy is the product; its factory is Python; three instruments already gate commits. Codability, initially scored for Python on fluency, is now the weaker half of that case: the benchmarked function-completion evidence runs Elixir's way, caveated (§3), and what remains Python's — repo-scale familiarity with the instrument stack, library breadth — is what incumbency already provides. Every hour spent re-deriving the test tier is an hour not spent on #9, #25, #30.
- **Under the changed assumptions (human-primary author, multi-user a real requirement, no tooling limits): the BEAM host is better.** `ways-of-working.md` §2.2 is OTP's thesis with a runtime to enforce it; the shell stops being the risk center. Postgres arrives with the multi-user requirement under either host; what the BEAM adds is the operability around it — supervision, delivery, the console, latency headroom. The flip costs a parser-and-shell port, not a rewrite, because `ways-of-working.md` §10.2 held.
- **What never flips with it:** corpus, laws, workflows, the `Den` oracle plan, measurement-first, backend parameterisation. The constitution travels.

---

## 8. Triggers

1. **First real multi-user requirement** (concurrent serving beyond one operator) → open the host issue; port order: corpus runner, adapter and lift, shell, console last.
2. **Sustained human-primary authoring** → de-weight codability, the single largest standing-path win.
3. **§9.1 measurement: kernel time a clear majority at realistic volume** → the Rust door opens under either host; under BEAM, via Rustler.
4. **Dafny Rust backend negative** (register #10) → oracle to a host-agnostic CLI (Go/C# extraction); no host change either way.
5. **A missed W1 variant escapes an Elixir corpus run** → the Gleam carve-out via `mix_gleam` re-opens; it is parked, not rejected.
6. **The W2/W3 bakeoff reports** (`decisions/0006`) → its evidence feeds #16; a backend that passes the gate but loses on the scoring order re-weighs the host choice here.

---

## 9. Relation to the Pentad post

The credited prompt (Kendall Clark, Pentad Labs, 2026-10-06): WunderOS splits coordination — sessions, tool calls, retries, supervision, the steady arrival of failure — onto the BEAM with Gleam, and computation — inference kernels, vector algebra, storage I/O — into Zig, with a *generated* BEAM–Zig boundary because hand-written boundaries fail, plus microVM venues for tenant code and hot reload across two runtimes.

Their split criterion — *if it's expected to fail, it runs on the BEAM; if it's got to be fast and exact, it runs in Zig* — maps onto due2 cleanly, and the mapping is the whole comparison:

- **The coordination half is due2's shell, and it is genuinely BEAM-shaped:** the request path, resolver fan-out, evidence ingestion, the re-evaluation sweep — long-lived, stateful, subject to failure from things they do not control, which is the post's own description of what the BEAM is for.
- **The computation half is due2's core, and it is not Zig-shaped.** due2's exactness is algorithmic, not bit-level; nothing needs memory layout or SIMD. Where the post's stack carries three seams — the generated boundary (a homegrown compiler), tenant venues, two-runtime reload — this alternative carries one, and rents it: Rustler is the maintained, off-the-shelf version of the boundary compiler they had to build. Mainstream-ness is not the compromise it resembles; it is the difference between owning that compiler and renting one.
- **Read under the standing assumptions, the same post is evidence for Python.** Its anti-Python case is an operability case — preemptive scheduling, per-process heaps, supervision as a runtime property — and operability is exactly what those assumptions price near zero. The post argues against Python as an *operating system for agents*; due2 under the standing assumptions is a *conformance corpus with an evaluator*, and the argument does not apply.

---

## References

- Pentad Labs, *Why our agent OS runs on Gleam and Zig, not Python or Rust* — `pentad.ai/blog/why-our-agent-os-runs-on-gleam-and-zig/` (2026-10-06).
- `implementation-alternatives.md` — the first review (W1 vehicle; Lean, clingo, OCaml+Why3, Flix, Soufflé); `decisions/0002` — the standing decision it backs.
- `ways-of-working.md` §2.2 (the let-it-crash discipline the BEAM embodies), §10.2 (the three commitments that keep a host flip cheap).
- `due2-architecture.md` §9–§9.1 (measurement before argument), §10 (conformance suite), §7 (the two clocks).
- MultiPL-E: *A Scalable and Extensible Approach to Benchmarking NL2Code for 18 Programming Languages* — arXiv:2208.08227 (language-resource tiers in LLM code generation). The paper evaluates 18 languages; the dataset has since grown to 24, Elixir among them (`humaneval-elixir`, `mbpp-elixir`) — verified against the dataset's config list; the README's "18" is stale as a track inventory.
- Code Llama: *Open Foundation Models for Code* — arXiv:2308.12950 (Rozière et al., Meta AI): MultiPL-E's principal consumer, and the multi-language record documenting Python-specialist versus multi-language accuracy variance.
- StreamData (elixir-lang.org, 2017–); `qcheck` (hex.pm, v0.0.x); `mix_gleam` (github.com/gleam-lang/mix_gleam, official).
- Bond — design by contract for Elixir: `@pre`, `@post`, invariants, runtime-checked (hex.pm/packages/bond, v1.19.0).
- RDF.ex (`rdf`, hex.pm, v3.0.1) — RDF 1.1 with Turtle, N-Triples/N-Quads; SPARQL.ex, JSON-LD.ex and ShEx.ex in the same family (Marcel Otto, since 2015). No SHACL engine on the BEAM — ShEx yes, SHACL no — which is why the checker side stays `pyshacl` under any host.
- AutoCodeBench — *Large Language Models are Automatic Code Benchmark Generators*, Tencent Hunyuan, arXiv:2508.09101 (Aug 2025): 3,920 problems, 20 languages, 30+ models; Elixir tops the per-language upper bound (97.5 to Python's 63.3) on translated low-resource problems whose tests were never human-verified. The critical write-up of that result (lukabreitig.com/blog/llms-write-elixir) — translated-from-Python problems, the low-resource difficulty-filter failure, the unverified tests; José Valim's "local reasoning" analysis of the same numbers (dashbit.co/blog/why-elixir-best-language-for-ai).
- Deprecated-API study — ICSE 2025, arXiv:2406.09834: seven LLMs, 70–90% deprecated Python API usage on outdated context, 9–18% on current; GitChameleon 2.0 (OpenReview, wtqdcVfJUN): ~50% success on version-specific Python generation.
- Review inputs, 2026-10-16 (repo owner), three rounds: persistence belongs on both sides; guards/Bond/typespecs as the Elixir contract mechanisms; RDF.ex; a Python-vs-Elixir codability analysis (fluency vs structural safety vs validation-loop efficiency), absorbed into §3 and §6; the Tencent benchmark pointer, which corrected "no benchmarked Elixir column"; and the MultiPL-E and Code Llama citations, which overturned that correction's companion claim — "MultiPL-E has no Elixir track" had been verified against the README's headline count rather than the dataset's config list, and was wrong. One claim remains unsourced and is not adopted: "2× fewer iterations in Elixir" — no self-repair-loop benchmark reports it; the figure resembles Opus 4's 80.3-vs-40.3 accuracy gap on AutoCodeBench.
