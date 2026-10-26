# 0041 — The evaluator returns the whole trace

**Status:** Decided, 2026-10-26 (the owner, on #138)
**Context documents:** `due2-workflows.md` §3.5, §7 · `due2-platform.md` §2.1, §2.6 · `decisions/0007` · `decisions/0010` · issue #138

## Question

`due2-workflows.md` v0.49 §3.5 said which part of due2 writes each relation of the trace. W2 and W3 wrote all of them except two, which the shell wrote:

- `evaluation`, the ids of the four input collections;
- `diagnostic`, the corpus diagnostics of every policy an evaluated atom belongs to.

`due2-platform.md` §2.1 has `decide(corpus, request, sotw, config)` return the trace by value. If the shell adds two relations afterwards, the trace `decide` returns is not the trace the ledger stores, and replay, which calls `decide` again and compares digests, compares something else. Who produces these two relations?

## Decision

1. **The evaluator returns the whole trace.** `decide` returns every relation of `due2-workflows.md` §3.5 as one value, `evaluation` and `diagnostic` included, and writes nothing. The orchestrator stores what it returns.
2. **The evaluator computes both relations from its inputs.** `evaluation` holds the four input ids, each the digest of its collection's canonical bytes (`decisions/0007`). `diagnostic` copies the corpus `diagnostic` tuples of every policy of an atom in `finding`.
3. **The column of `due2-workflows.md` §3.5 says which workflow computes each relation.** Its header becomes *Computed by*, and both rows name W2.

## Why this holds

- **A pure function returns its result.** The owner, on #138: the evaluator "returns" the trace, because "it cannot write it and remain pure".
- **Both relations depend on the inputs alone.** The input ids are digests of the collections `decide` receives. The diagnostics are tuples of the corpus it receives. The shell holds nothing more that either needs, so no part of the trace has to be added outside `decide`.
- **Replay compares like with like.** The stored trace is the returned trace, so replaying `decide` and comparing digests checks all of it (`due2-workflows.md` §7), and the explanation of `decisions/0010` comes from one place.

## Rejected

- **The orchestrator adds `evaluation` and `diagnostic`.** The stored trace would differ from the returned one, and every replay would have to repeat the orchestrator's additions before it could compare digests.

## Consequences

- `due2-workflows.md` v0.50 §3.5: the *Computed by* column, and W2 for `evaluation` and `diagnostic`.
- `due2-platform.md`: §2.2 and §2.6 say that the orchestrator stores the trace `decide` returns, and builds no part of it.

## Revisit when

- Computing collection digests inside the evaluator costs too much at agent volume (`ways-of-working.md` §10.4). The orchestrator could then pass the digests it already holds, and the evaluator would check none of them.
