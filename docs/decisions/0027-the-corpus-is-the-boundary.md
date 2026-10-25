# 0027 — W1 stays Python; the corpus is the boundary; the bakeoff ends; the W2/W3 language is open

**Status:** Decided, 2026-10-24 (the owner), except item 1, which is open (#104); amended 2026-10-25: clingo-i's relation-level face is the gate's oracle
**Context documents:** `decisions/0002` #1, #5, #8 · `decisions/0004`, `0006`, `0007`, `0009`, `0021` #7 · `ways-of-working.md` §7.4, §10 · `due2-architecture.md` §9 · `due2-platform.md` §2.1, §2.3, §2.8 · `due2-workflows.md` §3.1, §5.5, §6.4 · `docs/archive/implementation-alternatives.md` §7 · issues #36–#41, #104, #105

## Question

How are W1, W2, and W3 built for production, and is the bakeoff of `decisions/0006` still how the W2/W3 implementation is chosen?

`decisions/0006` planned three W2/W3 backends, in Python, Elixir, and Clingo, under one gate. It scored them on trace fidelity first and on performance last. Kotlin was set aside (`decisions/0002` #8). `docs/archive/implementation-alternatives.md` §7 gives the reasons: it is not a verification language and has the same defect classes as disciplined Python, it costs a second language, a second RDF stack, and a duplicated term model, and it answers the W2/W3 hot-path question rather than W1's risk question. Two things have changed since:

- **clingo-i is the oracle.** It is the L9 oracle (`decisions/0009`), and the bounded-exhaustive search over it is part of the evidence for the formal claims (`correctness-strategy.md` §4.8). If Clingo were also the production evaluator, the oracle and the implementation would share their rules.
- **Agents will call the evaluator,** not only people through a user interface, the owner states. That raises the request volume and the number of requests in flight. The platform has to be resilient and to scale, and in time it has to be fast. Before this record, `due2-architecture.md` §9 called an in-memory interpreter adequate for governance-scale volumes.

The owner also states two facts about the organisation that will run due2. It runs many JVM services, in Java, Scala, Kotlin, and Clojure, and it does not run the BEAM. Its team knows Python well, and the predecessor system (`due2-platform.md` §4) is written in Python.

## Decision

1. **The language of W2 and W3, and of the evaluator of `due2-platform.md` §2.1 that hosts them, is open (#104).** The evaluator plans reads and decides, and owns no state. Kotlin is the owner's leading candidate, for the reasons under Why, and Python is the other. #104 may also weigh the other JVM languages the organisation runs. The owner settles it as an amendment to this record. The other components of `due2-platform.md` §2, such as fact fetching and the ledger, are not decided here.
2. **W1 stays Python** (`decisions/0002` #1, narrowed to W1). It runs as a batch job, once per policy version and normaliser version: it validates the policy and normalises it (`due2-platform.md` §2.8). Its output is the corpus of `due2-workflows.md` §3.1, a JCS JSON collection named by its digest (`decisions/0007`). Its oracles, `Den` among them (`correctness-strategy.md` §4.2), stay Python.
3. **The corpus is the only thing that crosses from W1 to W2 and W3.** It is the language-neutral normal form of `ways-of-working.md` §10.2 #2. Nothing after W1 stage 2 reads RDF (`due2-workflows.md` §4), and evaluation needs no RDF store or SPARQL endpoint. The owner states that authored policies may be kept as Turtle in git or in a triple store, and that nothing downstream depends on which. The policy store keeps each corpus immutable and named by its digest (`due2-platform.md` §2.3). The evaluator may cache corpora by digest, which is safe because a corpus is immutable. It selects the atoms for a request from a cached corpus's index (`due2-workflows.md` §5.5), never by running W1. Selection must over-select (`due2-platform.md` §2.3): it may drop a root only when its action, target, or parties certainly do not match the request. #105 states that rule per atomic policy, with the property test that checks it.
4. **Clingo is not a production backend.** clingo-i stays the L9 oracle (`decisions/0009`). The carve-out of `decisions/0002` #5 for a clingo backend closes.
5. **The bakeoff ends without being run.** The Elixir backend (#40) is withdrawn, the Python backend (#39) waits on #104, and the scoring of `decisions/0006` #5 lapses. The rest of `decisions/0006` now serves the W2/W3 evaluator: its relation-level input (item 3), its gate (item 4), and the work items for the vector format (#36), the vectors (#37), and the brute-force W3 (#38). The evaluator runs as a spike under the shared suite (`ways-of-working.md` §7.4) on the relation-level vectors, and on the full corpus once W1 exists. With one implementation, the gate's trace equality across backends (L1) becomes equality with the expected traces the vectors carry. clingo-i may gain a relation-level face for the same vectors (#41; `decisions/0009` #2 and #6 (d)). It is a second oracle independent of the evaluator, but not of `I`, whose rules it reuses (`decisions/0009` #8).
6. **Measure before optimising.** Before any performance work, record the measurables of `ways-of-working.md` §10.4 for the agent workload: p99 with the resolver excluded (the SOTW services that answer operands, `due2-platform.md` §2.4), records evaluated per request, corpus size, and whether every decision carries an explanation. `due2-architecture.md` §9's order still holds: index the corpus first.

## Why

- **W1 is the offline stage.** Its risk is semantic, and its budget is effectively unbounded (`ways-of-working.md` §10.1). Its checkers and oracles are already in Python, and the team knows Python.
- **A neutral boundary keeps the W2/W3 choice free.** Because only the corpus crosses, the W2/W3 language changes nothing upstream, and W1 never has to run on the request path.
- **The oracle and the implementation must differ.** The evaluator shares neither code nor language with clingo-i, and none with the brute-force W3 unless it is written in Python, the language `decisions/0006` #2 keeps the oracles in. Only the specification and the vectors are common.
- **The bakeoff no longer tests what decides the choice.** Clingo is out (item 4), and Elixir is out because the organisation does not run the BEAM. What remains is a choice between Kotlin and Python on the concurrency model and on organisational fit, which `decisions/0006` did not score.

**Why Kotlin leads (item 1).** The argument rests on the concurrency model and on what the organisation runs, not on measured performance, which item 6 has still to collect.

- **W2 and W3 are the hot stage** of `ways-of-working.md` §10.1, the only stage where a language argument from performance is allowed. They are a pure function over immutable inputs (`ways-of-working.md` §10.2 #1), so any language scales them by adding processes. What differs is the cost per process. One JVM process serves many concurrent requests on threads, virtual threads, or coroutines, against one in-memory copy of the indexed corpus. CPython runs Python code on one thread at a time per process unless its free-threaded build is used (PEP 703), so it serves concurrent requests on several processes, each with its own copy of the corpus. What that costs depends on the corpus size that item 6 records.
- **The exact computations are exponential, and their bounds are budgets.** `due2-workflows.md` §6.4 enumerates the mixed variables, up to `max_mixed`, and the listed frontier's relevant unknowns, up to `max_frontier_vars` (`decisions/0004`). Past either bound, W3 falls back to an answer that is not exact. The bounds are configurable, with a default of 8. If item 6's measurements show W3 faster on the JVM, higher bounds give exact answers in more cases within the same latency budget; until then this is an expectation, not a finding.
- **Most of `decisions/0002` #8's objection does not arise.** A Kotlin evaluator reads only the corpus relations, in JSON, so it needs no RDF stack, and its term model is the relation schema of `due2-workflows.md` §3. Kotlin is still no verification language, which matters for W1 and not for W2 and W3, whose oracles are elsewhere.
- **Against it:** the team knows Python, the predecessor is Python, and the value semantics would be written twice (see Consequences). Python's escape hatch from `ways-of-working.md` §10.3, Rust in process through PyO3, would add a second language later and under pressure.

## Alternatives

- **Kotlin for W1 too,** with Apache Jena, giving one runtime. Rejected: W1 is a batch job, its risk is semantic, and its checkers and oracles are Python. A second W1 stack would duplicate them.
- **Clingo in production.** Rejected (item 4): the oracle and the implementation would be one program.
- **Run the bakeoff as planned.** Rejected (Why).
- **Elixir.** The BEAM suits many concurrent callers, and `decisions/0006` expected it to suit the impure shell. Rejected: the organisation does not run it.

## Consequences

- `decisions/0002` #1 is narrowed to W1, #5's carve-out closes, and #8 no longer sets Kotlin aside for W2 and W3. `decisions/0006` is superseded except as item 5 lists. `decisions/0009` #6 (d), clingo-i as a bakeoff entrant, lapses with the bakeoff, and so do its statements that the production evaluator waits for the bakeoff. `decisions/0021` #7 is answered for W1 and left to #104 for W2 and W3.
- **If W2 and W3 are not Python, the value semantics are written twice.** The evaluator compares operand values under XSD datatypes, as clingo-i's Python driver does, and the driver's value table is where clingo-i's real bugs have appeared (`decisions/0021`, Consequences). The relation-level vectors must cover those comparisons, and a disagreement with clingo-i on one is triaged under `correctness-strategy.md` §6.
- `due2-architecture.md` §9, `correctness-strategy.md` §8, `ways-of-working.md` §7.4 and §10.3, and `spikes/README.md` name the W2/W3 evaluator in place of the bakeoff.
- In the issues: #40 is withdrawn, #39 waits on #104, #41 is re-scoped as in item 5, and the milestone "W2/W3 bakeoff" becomes "W2/W3 evaluator".

## Revisit when

- The `ways-of-working.md` §10.4 measurements show that W2 and W3 are not a clear majority of the latency at agent volume. The language was then not the constraint, and performance work goes to caching and SOTW freshness (`due2-architecture.md` §9).
- The evaluator cannot meet a vector without changing semantics. That is a finding under `decisions/0006` #4, not a spec change.
- W1 has to run per request, for example because agents submit policies of their own. W1 is then partly a hot stage.

## Amendment (2026-10-25, the gate's oracle)

The owner decided on 2026-10-25 that clingo-i, read through its relation-level face (#41), a second input face of its rules that reads the relation-level vectors (`decisions/0009` #2), is the oracle of the W2/W3 evaluator's gate, in place of the brute-force W3 (#38). The third item of `decisions/0006` #4's gate now reads: the relation-level cases, against clingo-i's slow mode through its relation-level face. #41 is required, and #38 is parked.

- **The reason for a separate Python oracle has gone.** `decisions/0006` #2 kept the oracles in Python, and the brute-force W3 was planned for a bakeoff in which Clingo (#41) was one of the backends under the gate. A backend cannot be its own oracle. Item 4 takes Clingo out of production, so clingo-i is an oracle only, and the evaluator shares no code or language with it (Why, "The oracle and the implementation must differ").
- **clingo-i already computes the definition.** Its slow mode enumerates every assignment of the literal variables, with no uniform/mixed split and no two-extreme computation, and declines above 64 variables rather than fall back (`correctness-strategy.md` §3). From the completions it derives the verdict, `verdict_basis`, the `unknown` atoms, `verdict_range`, and `eliminated` (`spikes/clingo-i/DESIGN.md` § Data flow), which are the relations a brute-force W3 was to compute. It also reads what `correctness-strategy.md` §9 row 5 left to the brute-force W3: multi-policy conflict under `invalid`, and nested constraints.
- **A second enumerator would add little independence.** A brute-force W3 would share with clingo-i what clingo-i shares with the evaluator: the prose of `due2-workflows.md` §5–§6, the completion key, and the author's reading of both. The checks that share none of these are the vectors' hand-derived traces and the Alloy model of the completion key (#84).
- **Recurrence does not argue for it.** clingo-i declines recurring duties (#80), but recurrence is parked with the rest of an agreement's operational life (#119), and #80 is parked with it.

The amendment has four costs:

- The relation-level face reuses `I`'s rules, so on the vectors the evaluator's one executable oracle is not independent of `I` (item 5). The vectors' hand-derived traces stay the independent one.
- clingo-i lists the frontier of `decisions/0026` only after #103, so the comparison of frontiers waits for it.
- clingo-i has no `max_mixed` or `max_frontier_vars` fallback. Where the evaluator falls back, the comparison checks soundness, not equality (`correctness-strategy.md` §4.5).
- A feature that clingo-i declines has no executable oracle on the vectors, only the hand-derived traces.

`correctness-strategy.md` v0.16 names clingo-i's relation-level face wherever it named the brute-force W3. `decisions/0021`'s amendment of 2026-10-24, which compares the evaluator with the brute-force W3, and the mentions of #38 in `decisions/0009` and `decisions/0011`, are read through this amendment.

Revisit when the evaluator's gate needs a feature that clingo-i declines and cannot be taught to read, and that is not parked. The brute-force W3 (#38) is then the alternative.
